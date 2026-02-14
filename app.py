
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Extractor de Datos")

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
                        # Extraemos texto de manera más simple para no romper las tablas de datos
                        texto_ext += pag.get_text("text") + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Buscando datos técnicos..."):
                
                # PROMPT DE EXTRACCIÓN CON PISTAS ESPECÍFICAS
                prompt = f"""
                Actúa como un cardiólogo experto. Debes extraer datos de este texto:
                ---
                {texto_ext}
                ---

                GUÍA DE BÚSQUEDA PARA ESTE PACIENTE:
                1. Busca el número al lado de 'LVIDd' o 'DDVI'. (En Nilda es 4.20 o 4.2).
                2. Busca el número al lado de 'EF(Teich)', 'EF' o 'FEy'. (En Nilda es 73.14).
                3. Busca 'LA' o 'AI' (En Nilda es 4.24).
                
                INSTRUCCIONES:
                - Si FEy > 55%: Conclusión = "Función sistólica conservada".
                - Si FEy < 45%: Conclusión = "Deterioro de la función sistólica".
                - Redacta el informe de forma técnica y profesional.

                FORMATO:
                DATOS DEL PACIENTE: Nombre, Edad.
                I. EVALUACIÓN ANATÓMICA: Diámetros y Aurícula.
                II. FUNCIÓN VENTRICULAR: FEy y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Doppler.
                CONCLUSIÓN: Diagnóstico final en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un cardiólogo que encuentra datos numéricos incluso en textos desordenados."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("📥 Descargar Word", generar_docx(respuesta), "Informe_Cardio.docx")
