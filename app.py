
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Extractor de Datos Preciso")

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx(texto_ia, imagenes):
    doc = Document()
    for linea in texto_ia.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        p = doc.add_paragraph()
        if any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run = p.add_run(linea.upper())
            run.bold = True
        else:
            p.add_run(linea)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir archivos del paciente", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_ext += pag.get_text() + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Buscando datos numéricos en el estudio..."):
                # PROMPT MEJORADO PARA DETECTAR DATOS EN INGLÉS Y ESPAÑOL
                prompt = f"""
                Eres un cardiólogo experto. Tu misión es extraer datos de este texto desordenado: {texto_ext}

                INSTRUCCIONES DE EXTRACCIÓN:
                1. Busca la FEy (Fracción de Eyección). Puede aparecer como 'EF', 'EF(Teich)', 'FEy' o 'Simpson'. 
                2. Busca diámetros: LVIDd o DDVI (Diámetro Diastólico), LVIDs o DSVI (Sistólico).
                3. Busca Aurícula Izquierda (LA o AI).
                4. SI ENCUENTRAS EL DATO, ÚSALO. Si no lo encuentras, no inventes, pero busca bien en las tablas.

                ESTILO DEL INFORME:
                - DATOS DEL PACIENTE: Nombre, Edad, ID.
                - I. EVALUACIÓN ANATÓMICA: Reportar DDVI, DSVI y AI con sus mm.
                - II. FUNCIÓN VENTRICULAR: Mencionar la FEy (En Nilda es aprox 73%, en otros puede ser distinta).
                - III. EVALUACIÓN HEMODINÁMICA: Resumen del Doppler.
                - CONCLUSIÓN: Diagnóstico técnico basado en si la FEy es normal (>55%) o reducida.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("Descargar Informe", generar_docx(respuesta, []), "Informe.docx")
