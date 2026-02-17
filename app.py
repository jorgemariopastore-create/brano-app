
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def limpiar_texto_extremo(texto):
    # Esta función junta las letras que el SonoScape separa
    # Ejemplo: "D D V I" -> "DDVI"
    texto = re.sub(r'(?<=\b[A-Z])\s(?=[A-Z]\b)', '', texto)
    # Limpia espacios múltiples
    texto = re.sub(r' +', ' ', texto)
    return texto

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
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS"]):
            run.bold = True
    if os.path.exists("firma.jpg"):
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE GROQ (Volvemos a lo seguro)
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    if "texto_limpio" not in st.session_state or st.session_state.get("file_id") != archivo.name:
        with st.spinner("Procesando datos con Groq..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            texto_acumulado = ""
            for pagina in pdf:
                # Extraemos con "blocks=True" para mantener las columnas
                texto_acumulado += pagina.get_text("text") + "\n"
            
            st.session_state.texto_limpio = limpiar_texto_extremo(texto_acumulado)
            st.session_state.file_id = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ACTÚA COMO EL DR. PASTORE. ANALIZA EL REPORTE DEL SONOSCAPE E3.
            
            DATOS A EXTRAER (BÚSCALOS CON CUIDADO, ESTÁN EN EL TEXTO):
            - Cavidades (mm): DDVI (ej. 61), DSVI (ej. 46), Septum (ej. 10), Pared (ej. 11), Aurícula (ej. 42).
            - Función: FEy (ej. 31%), FA, Motilidad (Hipocinesia), Hipertrofia.
            - Doppler: E/A, E/e', Vena Cava (ej. 15mm).
            - Conclusión: Redacta el diagnóstico final basado en el texto.

            FORMATO:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: [Valores]
            II. FUNCIÓN VENTRICULAR: [Valores]
            III. EVALUACIÓN HEMODINÁMICA: [Valores]
            IV. CONCLUSIÓN: [Diagnóstico]
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL ECOGRAFO:
            {st.session_state.texto_limpio}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            st.session_state.informe_final = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{st.session_state.informe_final}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error con Groq: {e}")

    if "informe_final" in st.session_state:
        st.download_button("📥 Descargar Word", crear_word(st.session_state.informe_final), f"Informe_{archivo.name}.docx")
else:
    if not api_key:
        st.warning("⚠️ Asegurate de tener GROQ_API_KEY en tus Secrets de Streamlit.")
