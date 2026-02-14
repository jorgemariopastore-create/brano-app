
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

# --- MANEJO DE CLAVE (SECRETS) ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key (Manual):", type="password")

def limpiar_texto(t):
    return t.encode("ascii", "ignore").decode("ascii")

def generar_docx_profesional(texto_ia, imagenes):
    doc = Document()
    section = doc.sections[0]
    section.left_margin = section.right_margin = Inches(0.7)
    section.top_margin = section.bottom_margin = Inches(0.6)

    # Título Principal
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)

    # Procesar el texto de la IA
    for linea in texto_ia.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Detectar encabezados para darles formato
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold = True
            p.paragraph_format.space_before = Pt(12)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Anexo de imágenes (formato estable para evitar errores de Word)
    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run('ANEXO: IMÁGENES DEL ESTUDIO').bold = True
        for img_data in imagenes:
            try:
                # Insertar imagen con un tamaño estándar
                doc.add_picture(io.BytesIO(img_data), width=Inches(4.5))
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            except:
                continue
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir archivos (PDF o Imágenes)", type=["pdf", "jpg", "png"], accept_multiple_files=True)

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

        if st.button("Generar Informe Médico"):
            with st.spinner("Analizando datos del estudio actual..."):
                texto_limpio = limpiar_texto(texto_ext)
                
                # EL PROMPT DEFINITIVO: DINÁMICO Y TÉCNICO
                prompt = f"""
                Actúa como un cardiólogo experto. Tu tarea es redactar un informe basado ÚNICAMENTE en estos datos: {texto_limpio}

                INSTRUCCIONES CRÍTICAS:
                1. NO uses datos de pacientes anteriores (como Baleiron). Lee los valores de este texto actual.
                2. Extrae medidas reales: DDVI (o LVIDd), DSVI (o LVIDs), AI (o LA), Masa.
                3. Analiza la Fracción de Eyección (FEy o EF):
                   - Si es > 55%: Informa "Función sistólica conservada".
                   - Si es < 45%: Informa el grado de deterioro y busca anomalías de motilidad.
                4. Estilo: Técnico, breve, profesional. Usa terminología médica.

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad, Fecha.
                I. EVALUACIÓN ANATÓMICA: Medidas de cavidades y espesores.
                II. FUNCIÓN VENTRICULAR: FEy encontrada, técnica y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Hallazgos Doppler (E/A, gradientes).
                IV. CONCLUSIÓN: Diagnóstico técnico principal basado en los números hallados.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
