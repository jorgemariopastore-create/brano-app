
import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Motor Gemini 1.5")

# 2. CARGADOR
archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def crear_word(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto.split('\n'):
        if not linea.strip(): continue
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS"]):
            run.bold = True

    if os.path.exists("firma.jpg"):
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA GEMINI
# Usa la misma clave que tenías, pero asegúrate de que sea una de Google AI Studio
api_key = st.secrets.get("GEMINI_API_KEY") 

if archivo and api_key:
    if "texto_pdf" not in st.session_state:
        with st.spinner("Analizando con Visión de Gemini..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Extraemos texto manteniendo el formato visual exacto
            st.session_state.texto_pdf = "\n".join([p.get_text("text") for p in pdf])
            pdf.close()

    if st.button("🚀 GENERAR INFORME"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Actúa como el Dr. Pastore. Del siguiente texto de un SonoScape E3, extrae:
            1. DDVI, DSVI, FA, DDSIV, DDPP, DDAI (están en mm).
            2. FEy (31%), Motilidad (Hipocinesia), Vena Cava (15mm).
            3. Relación E/A y E/e'.
            
            Formato:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Valores mm)
            II. FUNCIÓN VENTRICULAR: (FEy, Motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Doppler)
            IV. CONCLUSIÓN: (Diagnóstico)
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO:
            {st.session_state.texto_pdf}
            """
            
            response = model.generate_content(prompt)
            st.session_state.res_final = response.text
            st.markdown(f'<div class="report-container">{response.text}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error: {e}")

    if "res_final" in st.session_state:
        st.download_button("📥 Descargar Word", crear_word(st.session_state.res_final, []), "informe.docx")
        
