
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI - SonoScape E3 Edition", layout="wide")
st.title("❤️ CardioReport AI - Optimizado para SonoScape E3")

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
    archivos = st.file_uploader("Subir archivos del SonoScape E3", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        # Método de extracción optimizado para tablas de SonoScape
                        texto_ext += pag.get_text("words") 
                        texto_ext = str(texto_ext) + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Analizando reporte de SonoScape E3..."):
                
                prompt = f"""
                Eres un cardiólogo experto procesando datos de un ecógrafo SonoScape E3.
                Analiza el siguiente texto crudo y extrae los valores numéricos:
                ---
                {texto_ext}
                ---

                DICCIONARIO DE TRADUCCIÓN SONOSCAPE E3:
                - LVIDd = Diámetro Diastólico Ventrículo Izquierdo (Ej: 4.20 cm o 42 mm).
                - LVIDs = Diámetro Sistólico Ventrículo Izquierdo (Ej: 2.42 cm).
                - EF(Teich) o EF = Fracción de Eyección (Ej: 73.14%).
                - LA Diam o LA = Aurícula Izquierda (Ej: 4.24 cm).
                - IVSd = Tabique Interventricular.
                - LVPWd = Pared Posterior.

                INSTRUCCIONES:
                1. Extrae Nombre, Edad e ID del paciente.
                2. Si EF > 55% concluye "Función sistólica conservada".
                3. Si EF < 45% concluye "Deterioro de la función sistólica".
                4. Usa un tono técnico y seco.

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad.
                I. EVALUACIÓN ANATÓMICA: Reportar DDVI (LVIDd), DSVI (LVIDs) y AI (LA).
                II. FUNCIÓN VENTRICULAR: Mencionar FEy (EF) y técnica.
                III. EVALUACIÓN HEMODINÁMICA: Doppler (Vmax, Gradientes).
                CONCLUSIÓN: Diagnóstico final en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un cardiólogo experto en equipos SonoScape."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("📥 Descargar Informe", generar_docx(respuesta), "Informe_Cardio.docx")
