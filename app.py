
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Versión Estable")

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
                        # Corregido: Unimos la lista de bloques en un solo texto
                        bloques = pag.get_text("blocks")
                        for b in bloques:
                            texto_ext += str(b[4]) + " " # El texto está en la posición 4 del bloque
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Procesando datos del ecocardiograma..."):
                
                prompt = f"""
                Eres un cardiólogo experto. Analiza este texto extraído de un ecógrafo:
                ---
                {texto_ext}
                ---

                TAREA:
                1. Extrae: Nombre del paciente, Edad, FEy (EF o Fracción de Eyección), Diámetros (LVIDd o DDVI) y Aurícula (LA o AI).
                2. REGLA MÉDICA: 
                   - Si FEy > 55%: Conclusión = "Función sistólica conservada".
                   - Si FEy < 45%: Conclusión = "Deterioro de la función sistólica".
                3. NO INVENTES: Si un dato no está, pon 'No reportado'. Pero busca bien, el texto puede estar desordenado.

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad.
                I. EVALUACIÓN ANATÓMICA: Diámetros y Aurícula.
                II. FUNCIÓN VENTRICULAR: FEy y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Hallazgos del Doppler.
                CONCLUSIÓN: Diagnóstico técnico en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un cardiólogo que redacta informes precisos basados solo en los datos provistos."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("📥 Descargar Word", generar_docx(respuesta), "Informe_Cardio.docx")
