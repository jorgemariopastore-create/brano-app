
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Versión Final")

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
            with st.spinner("Escaneando datos biométricos..."):
                
                # PROMPT DE EXTRACCIÓN AVANZADA
                prompt = f"""
                Actúa como un cardiólogo experto. Debes extraer los datos de este estudio médico: {texto_ext}

                REGLAS CRÍTICAS:
                1. NO uses datos de pacientes anteriores (como el 30% o 61mm de Baleiron). 
                2. Busca valores numéricos usando estas etiquetas:
                   - FEy: busca 'EF(Teich)', 'FEy', 'EF', 'Simpson' o 'Fracción de Eyección'.
                   - Diámetros: busca 'LVIDd' o 'DDVI', 'LVIDs' o 'DSVI'.
                   - Aurícula: busca 'LA' o 'AI'.
                3. Si la FEy es mayor a 55%, indica "Función sistólica conservada".
                4. Si la FEy es menor a 40%, indica "Deterioro severo".

                ESTRUCTURA DEL INFORME:
                DATOS DEL PACIENTE: Nombre, Edad, ID.
                I. EVALUACIÓN ANATÓMICA: Reportar Diámetros (LVIDd/DDVI) y Aurícula (LA/AI).
                II. FUNCIÓN VENTRICULAR: Mencionar la FEy (%) y la motilidad parietal.
                III. EVALUACIÓN HEMODINÁMICA: Resumen del Doppler (válvulas y flujos).
                CONCLUSIÓN: Diagnóstico técnico FINAL en negrita basado en los números encontrados.

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
