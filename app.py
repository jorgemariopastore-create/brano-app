
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
    .report-container { background-color: white; padding: 30px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

# Función de Word optimizada (sin procesos pesados)
def crear_word_simple(texto_final):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto_final.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "PACIENTE", "FIRMA"]):
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
    # Mantenemos la lógica de extracción que SÍ funcionó
    if "pdf_text" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        with st.spinner("Leyendo reporte..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Esta es la línea que lograba leer los datos de Manuel:
            st.session_state.pdf_text = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
            st.session_state.last_file = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ACTÚA COMO EL DR. PASTORE. EXTRAE LOS DATOS DEL SONOSCAPE E3.
            USA ESTE FORMATO:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Valores mm)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (Doppler, Vena Cava)
            IV. CONCLUSIÓN: (Diagnóstico final)
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL PDF:
            {st.session_state.pdf_text}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            # Guardamos el resultado para que el botón de descarga no tenga que re-procesar nada
            st.session_state.informe_finalizado = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{st.session_state.informe_finalizado}</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {e}")

    # LA CLAVE PARA EVITAR EL BOTÓN ROJO: 
    # El botón de descarga solo aparece si el informe ya está en la memoria (session_state)
    if "informe_finalizado" in st.session_state:
        # Pre-preparamos los datos del Word para que la descarga sea instantánea
        word_data = crear_word_simple(st.session_state.informe_finalizado)
        st.download_button(
            label="📥 Descargar Informe en Word",
            data=word_data,
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="download_btn"
        )
