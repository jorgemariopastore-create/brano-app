
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Generador de Informes Técnicos")

# --- MANEJO DE CLAVE ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key (Manual):", type="password")

def limpiar_texto(t):
    return t.encode("ascii", "ignore").decode("ascii")

def generar_docx_profesional(texto_ia, imagenes):
    doc = Document()
    # Ajuste de márgenes
    section = doc.sections[0]
    section.left_margin = section.right_margin = Inches(0.7)
    
    # Título
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)

    # Procesar texto línea por línea para evitar errores de Word
    for linea in texto_ia.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold = True
            p.paragraph_format.space_before = Pt(12)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Imágenes (simplificado para evitar errores de apertura)
    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run('ANEXO DE IMÁGENES').bold = True
        for img_data in imagenes:
            try:
                doc.add_picture(io.BytesIO(img_data), width=Inches(4))
                doc.add_paragraph()
            except:
                continue
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir archivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        fotos = []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_ext += pag.get_text() + "\n"
                        for img in pag.get_images(full=True):
                            fotos.append(d.extract_image(img[0])["image"])
            else:
                fotos.append(a.read())

        if st.button("Generar Informe"):
            with st.spinner("Analizando datos del paciente actual..."):
                texto_limpio = limpiar_texto(texto_ext)
                
                # PROMPT DINÁMICO (Sin números de Baleiron)
                prompt = f"""
                Actúa como un cardiólogo clínico. Extrae los datos ÚNICAMENTE del texto provisto.
                DATOS DEL ESTUDIO: {texto_limpio}

                REGLAS:
                1. Extrae Nombre, Edad y Fecha reales.
                2. Busca los valores: DDVI, DSVI, AI, FEy (Fracción de Eyección).
                3. Si la FEy es > 55%, reporta "Función sistólica conservada".
                4. Si la FEy es < 40%, reporta "Deterioro severo".
                5. Usa estilo técnico médico (abreviaturas como AI, VI, FEy).

                ESTRUCTURA:
                DATOS DEL PACIENTE
                I. EVALUACIÓN ANATÓMICA
                II. FUNCIÓN VENTRICULAR
                III. EVALUACIÓN HEMODINÁMICA
                IV. CONCLUSIÓN (En una oración técnica)

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = res.choices[0].message.content
                st.markdown(resultado)
                st.download_button("📥 DESCARGAR INFORME", generar_docx_profesional(resultado, fotos), "Informe_Cardiologico.docx")
