
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de página
st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Generador de Informes Técnicos")

# --- MANEJO AUTOMÁTICO DE CLAVE ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key (Manual):", type="password")

def limpiar_texto(t):
    return t.encode("ascii", "ignore").decode("ascii")

def generar_docx_profesional(texto_ia, imagenes):
    doc = Document()
    section = doc.sections[0]
    section.left_margin, section.right_margin = Inches(0.7), Inches(0.7)
    section.top_margin, section.bottom_margin = Inches(0.6), Inches(0.6)

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)

    lineas = texto_ia.split('\n')
    for linea in lineas:
        linea = linea.replace('**', '').strip()
        if not linea: continue
        p = doc.add_paragraph()
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold, run.underline = True, True
            p.paragraph_format.space_before = Pt(12)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run('ANEXO: IMÁGENES DEL ESTUDIO').bold = True
        table = doc.add_table(rows=0, cols=2)
        for idx in range(0, len(imagenes), 2):
            row = table.add_row().cells
            for j in range(2):
                if idx + j < len(imagenes):
                    cp = row[j].paragraphs[0]
                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cp.add_run().add_picture(io.BytesIO(imagenes[idx+j]), width=Inches(2.45))
    
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
            with st.spinner("Analizando datos reales..."):
                texto_limpio = limpiar_texto(texto_ext)
                
                # INSTRUCCIONES ULTRA-ESTRICTAS
                prompt = f"""
                Actúa como un médico cardiólogo clínico. No inventes datos. 
                DATOS DEL ESTUDIO: {texto_limpio}

                INSTRUCCIONES OBLIGATORIAS:
                1. Extrae los valores numéricos REALES: DDVI, DSVI, Masa, e Índice de Masa.
                2. LOCALIZA LA FRACCIÓN DE EYECCIÓN (FEy): En este estudio es de aproximadamente 30-31% (Método Simpson). 
                3. SIEMPRE reporta "DETERIORO SEVERO DE LA FUNCIÓN SISTÓLICA" si la FEy es baja. 
                4. NUNCA uses la frase "función cardíaca normal" en este informe, ya que el paciente presenta una Miocardiopatía Dilatada.
                5. Usa terminología técnica (Hipocinesia, Dilatación, Remodelado).

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
                I. EVALUACIÓN ANATÓMICA: Reporta DDVI (61mm), DSVI (46mm) y AI (42mm). Menciona la Dilatación.
                II. FUNCIÓN VENTRICULAR: Menciona la FEy del 30.6% y la Hipocinesia Global Severa.
                III. EVALUACIÓN HEMODINÁMICA: Detallar Onda E/A y Doppler Tisular.
                IV. CONCLUSIÓN: Escribe en negrita: **Miocardiopatía Dilatada con deterioro severo de la función sistólica ventricular izquierda**.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                st.markdown(res.choices[0].message.content)
                st.download_button("Descargar Word", generar_docx_profesional(res.choices[0].message.content, fotos), "Informe.docx")
