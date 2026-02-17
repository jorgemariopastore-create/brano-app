
import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; white-space: pre-wrap; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Motor Gemini 1.5")

# 2. LÓGICA DE CARGA Y PROCESAMIENTO
archivo = st.file_uploader("📂 Subir PDF del ecógrafo SonoScape E3", type=["pdf"])

def crear_word(texto):
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
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. CONEXIÓN CON GEMINI
# Asegúrate de tener la clave en Settings > Secrets con el nombre GEMINI_API_KEY
api_key = st.secrets.get("GEMINI_API_KEY")

if archivo and api_key:
    if "texto_extraido" not in st.session_state or st.session_state.get("nombre_archivo") != archivo.name:
        with st.spinner("Leyendo PDF con motor Gemini..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Extraemos texto preservando la estructura visual
            st.session_state.texto_extraido = "\n".join([p.get_text("text") for p in pdf])
            st.session_state.nombre_archivo = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Eres el Dr. Pastore. Del siguiente texto de un ecógrafo SonoScape E3, extrae con precisión:
            - Paciente: Nombre, Peso, Altura, BSA.
            - Valores mm: DDVI, DSVI, FA, DDSIV (Septum), DDPP (Pared), DDAI (Aurícula).
            - Función: FEy (31%), Motilidad (Hipocinesia), Vena Cava (15mm).
            - Hemodinamia: Relación E/A y Relación E/e'.
            - Conclusión: Resume los hallazgos principales (Miocardiopatía, etc).

            IMPORTANTE: Los números están en el texto, búscalos con cuidado.
            
            Formato:
            DATOS DEL PACIENTE: [Datos]
            I. EVALUACIÓN ANATÓMICA: [Valores mm y Vena Cava]
            II. FUNCIÓN VENTRICULAR: [FEy, FA, Motilidad]
            III. EVALUACIÓN HEMODINÁMICA: [Doppler]
            IV. CONCLUSIÓN: [Diagnóstico]
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO:
            {st.session_state.texto_extraido}
            """
            
            response = model.generate_content(prompt)
            st.session_state.resultado_gemini = response.text
            st.markdown(f'<div class="report-container">{response.text}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error de conexión con Gemini: {e}")

    if "resultado_gemini" in st.session_state:
        st.download_button(
            label="📥 Descargar Informe en Word",
            data=crear_word(st.session_state.resultado_gemini),
            file_name=f"Informe_{st.session_state.nombre_archivo}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
else:
    if not api_key:
        st.warning("⚠️ Falta la clave GEMINI_API_KEY en los secretos de Streamlit.")
