
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE INTERFAZ
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del SonoScape E3", type=["pdf"])

def super_limpieza(texto):
    # Paso 1: Juntar letras separadas (D D V I -> DDVI)
    texto = re.sub(r'(?<= [A-Z])\s(?=[A-Z] )', '', texto)
    # Paso 2: Eliminar saltos de línea innecesarios que rompen números
    texto = texto.replace('\n', '  ')
    # Paso 3: Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def generar_word(texto):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS"]):
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
    if "texto_bruto" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        with st.spinner("Escaneando cada milímetro del PDF..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            texto_completo = ""
            for pagina in pdf:
                # Extraemos el texto crudo para que la IA vea las tablas
                texto_completo += pagina.get_text("text") + "\n"
            
            st.session_state.texto_bruto = super_limpieza(texto_completo)
            st.session_state.last_file = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. PASTORE. EL SIGUIENTE TEXTO ES UNA EXTRACCIÓN CRUDA DE UN SONOSCAPE E3. 
            LOS DATOS ESTÁN AHÍ, PERO DESORDENADOS. TU TRABAJO ES ENCONTRARLOS.

            INSTRUCCIONES DE BÚSQUEDA:
            - Busca números seguidos de 'mm' o que estén cerca de: DDVI, DSVI, DDSIV, DDPP, DDAI.
            - Busca el porcentaje de FEy (ej. 31%) y FA.
            - Busca en la sección Doppler: E/A, E/e' y Vena Cava.
            - Busca términos como 'Hipocinesia', 'Hipertrofia' o 'Dilatada'.

            ESTRUCTURA OBLIGATORIA:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, Septum, Pared, AI, Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (E/A, E/e')
            IV. CONCLUSIÓN: (Diagnóstico médico final)

            REGLA: No digas 'No disponible'. Si el valor parece ser 61 para DDVI, úsalo.
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO PARA ANALIZAR:
            {st.session_state.texto_bruto}
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
            label="📥 Descargar Word",
            data=generar_word(st.session_state.informe_ok),
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
