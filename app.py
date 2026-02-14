
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Extractor Robusto")

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx(texto_ia):
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
                        # Extraemos texto con un método más simple para no romper tablas
                        texto_ext += pag.get_text("text") + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Analizando datos biométricos..."):
                
                # PROMPT DE EXTRACCIÓN ULTRA-FLEXIBLE
                prompt = f"""
                Eres un cardiólogo experto. Analiza este texto de un ecocardiograma:
                ---
                {texto_ext}
                ---
                
                TU OBJETIVO: Extraer los números a toda costa. 
                Busca específicamente:
                1. Fracción de Eyección: Puede decir 'EF', 'EF(Teich)', 'FEy', o estar cerca de un porcentaje (%). En este texto hay un valor de 73.14%. búscalo.
                2. Diámetros: LVIDd es DDVI. LVIDs es DSVI. Busca valores como 4.20cm o 42mm.
                3. Aurícula (LA o AI): Busca valores como 4.24cm o 42mm.

                REGLAS:
                - NO digas que no hay datos. Los datos ESTÁN en el texto, búscalos bien.
                - Si la FEy es >55%, concluye: "Función sistólica conservada".
                - Si la FEy es <40%, concluye: "Deterioro severo".

                FORMATO:
                DATOS DEL PACIENTE: Nombre, Edad.
                I. EVALUACIÓN ANATÓMICA: Diámetros (DDVI, DSVI) y AI.
                II. FUNCIÓN VENTRICULAR: FEy (%) y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Doppler.
                CONCLUSIÓN: Diagnóstico final técnico en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1 # Subimos un poquito para que sea más astuto buscando
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("Descargar Informe", generar_docx(respuesta), "Informe.docx")
