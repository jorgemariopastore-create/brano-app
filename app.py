
import streamlit as st
from groq import Groq
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
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def crear_word(texto_final):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto_final.split('\n'):
        if not linea.strip(): continue
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    if os.path.exists("firma.jpg"):
        try:
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Usamos caché para que el PDF no se procese dos veces (evita el botón rojo)
    if "pdf_text" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        pdf = fitz.open(stream=archivo.read(), filetype="pdf")
        st.session_state.pdf_text = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
        st.session_state.last_file = archivo.name
        pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. PASTORE. EXTRAE LOS DATOS Y REDACTA EL INFORME MÉDICO.
            MANTÉN EL FORMATO: DATOS PACIENTE, I. ANATÓMICA, II. VENTRICULAR, III. HEMODINÁMICA, IV. CONCLUSIÓN.
            FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO:
            {st.session_state.pdf_text}
            """
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            st.session_state.informe_ok = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{st.session_state.informe_ok}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {e}")

    # LA DESCARGA AHORA ES SEGURA
    if "informe_ok" in st.session_state:
        st.download_button(
            label="📥 Descargar Word",
            data=crear_word(st.session_state.informe_ok),
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
