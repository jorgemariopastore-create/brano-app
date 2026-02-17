
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 30px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: 'Courier New', Courier, monospace; font-size: 14px; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

# 2. CARGADOR DE ARCHIVOS
archivo = st.file_uploader("📂 Subir PDF del ecógrafo SonoScape E3", type=["pdf"])

def generar_word(texto_informe):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto_informe.split('\n'):
        if not linea.strip(): continue
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        try:
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE INTELIGENCIA
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    if "texto_mapeado" not in st.session_state or st.session_state.get("file_id") != archivo.name:
        with st.spinner("Realizando mapeo espacial del reporte..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            texto_mapeado = ""
            for pagina in pdf:
                # LA CLAVE: "layout=True" mantiene el orden visual de las tablas
                texto_mapeado += pagina.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) + "\n"
            
            st.session_state.texto_mapeado = texto_mapeado
            st.session_state.file_id = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ACTÚA COMO EL DR. PASTORE. USA EL SIGUIENTE TEXTO QUE MANTIENE EL FORMATO DE TABLAS ORIGINAL.
            
            MISION: Extraer los valores numéricos y redactar el informe.
            
            DATOS CLAVE QUE DEBES BUSCAR (ESTÁN AHÍ):
            - En la tabla de medidas: DDVI (61), DSVI (46), Septum (10), Pared (11), AI (42), FA (25), FEy (31%).
            - En el texto de motilidad: Busca 'Hipocinesia global severa'.
            - En el Doppler: Relación E/A (0.95), E/e' (5.9), Vena Cava (15mm).

            ESTRUCTURA:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Valores mm y Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (Doppler valvular)
            IV. CONCLUSIÓN: (Diagnóstico final)

            REGLA: NO digas 'No se encontraron datos'. Si el texto está desordenado, interprétalo profesionalmente.
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO ORIGINAL (PRESERVADO):
            {st.session_state.texto_mapeado}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            st.session_state.informe_ok = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{st.session_state.informe_ok}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error de sistema: {e}")

    if "informe_ok" in st.session_state:
        st.download_button(
            label="📥 Descargar Informe en Word",
            data=generar_word(st.session_state.informe_ok),
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
