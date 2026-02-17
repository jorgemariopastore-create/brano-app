
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
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo SonoScape E3", type=["pdf"])

def crear_word_seguro(texto_informe):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
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
    # PASO 1: LECTURA BLINDADA (Solo ocurre al subir el archivo)
    if "datos_pdf" not in st.session_state or st.session_state.get("nombre_archivo") != archivo.name:
        with st.spinner("Mapeando coordenadas del reporte..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Usamos el modo de preservación de espacios que rescató los datos de Manuel antes
            st.session_state.datos_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
            st.session_state.nombre_archivo = archivo.name
            pdf.close()

    # PASO 2: GENERACIÓN DE INFORME
    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            # Prompt reforzado para que NO ignore los números que ya vimos que existen
            prompt = f"""
            ACTÚA COMO EL DR. PASTORE. EL SIGUIENTE TEXTO CONTIENE LOS DATOS DE UN SONOSCAPE E3.
            
            BUSCA ESPECÍFICAMENTE:
            - DDVI (61), DSVI (46), Septum (10), Pared (11), AI (42), FA (25), FEy (31%).
            - Hipocinesia global severa.
            - E/A (0.95), E/e' (5.9), Vena Cava (15mm).

            FORMATO:
            DATOS DEL PACIENTE: [Nombre, Peso, Altura, BSA]
            I. EVALUACIÓN ANATÓMICA: [Valores mm]
            II. FUNCIÓN VENTRICULAR: [FEy, FA, Motilidad]
            III. EVALUACIÓN HEMODINÁMICA: [Doppler, Vena Cava]
            IV. CONCLUSIÓN: [Diagnóstico final médico]
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO EXTRAÍDO:
            {st.session_state.datos_pdf}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            st.session_state.informe_memo = resp.choices[0].message.content
            
        except Exception as e:
            st.error(f"Error de comunicación: {e}")

    # PASO 3: VISUALIZACIÓN Y DESCARGA (Independientes para evitar botón rojo)
    if "informe_memo" in st.session_state:
        st.markdown(f'<div class="report-container">{st.session_state.informe_memo}</div>', unsafe_allow_html=True)
        
        # El Word se prepara solo cuando el usuario hace clic, ahorrando RAM
        word_data = crear_word_seguro(st.session_state.informe_memo)
        st.download_button(
            label="📥 Descargar Informe en Word",
            data=word_data,
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
