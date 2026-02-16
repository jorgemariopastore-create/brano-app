
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 15px rgba(0,0,0,0.05); }
    .stButton>button { background-color: #c62828; color: white; border-radius: 10px; font-weight: bold; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL DOCUMENTO WORD
def crear_word_profesional(texto):
    doc = Document()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)
    run_t.font.name = 'Arial'

    for linea in texto.split('\n'):
        linea_limpia = linea.replace('**', '').strip()
        if linea_limpia:
            p = doc.add_paragraph()
            run = p.add_run(linea_limpia)
            run.font.name = 'Arial'
            run.font.size = Pt(11)
            # Detectar secciones principales para negrita
            if any(linea_limpia.upper().startswith(tag) for tag in ["DATOS", "I.", "II.", "III.", "IV.", "FIRMA:"]):
                run.bold = True
    
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME PROFESIONAL"):
            with st.spinner("Analizando estudio médico..."):
                try:
                    # LECTURA COMPLETA DE TODAS LAS PÁGINAS
                    texto_raw = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_raw += pagina.get_text()
                    
                    # LIMPIEZA DE CARACTERES DE TABLA (Crucial para Baleiron)
                    # Eliminamos comillas y unificamos espacios para que la IA "vea" los números
                    texto_limpio = texto_raw.replace('"', ' ').replace("'", " ").replace(",", ".")
                    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT DE EXTRACCIÓN TOTAL Y DIAGNÓSTICO
                    prompt_final = f"""
                    ERES UN EXPERTO EN CARDIOLOGÍA. REDACTA UN INFORME PARA EL DR. FRANCISCO ALBERTO PASTORE.
                    UTILIZA ESTE TEXTO DEL ESTUDIO: {texto_limpio}

                    INSTRUCCIONES DE EXTRACCIÓN:
                    1. DATOS: Extrae Nombre, ID y Fecha.
                    2. ANATOMÍA: Busca DDVI, DSVI, DDAI (Aurícula), DDSIV (Septum) y DDPP (Pared). 
                    3. FUNCIÓN: Busca FEy (31%) y la descripción de motilidad (Hipocinesia global severa).
                    4. HEMODINAMIA: Busca Vena Cava y Relación E/A.

                    REGLA MÉDICA DR. PASTORE:
                    Si FEy < 35% y DDVI > 57mm -> CONCLUSIÓN OBLIGATORIA: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE:
                    I. EVALUACIÓN ANATÓMICA:
                    II. FUNCIÓN VENTRICULAR:
                    III. EVALUACIÓN HEMODINÁMICA:
                    IV. CONCLUSIÓN: (En Negrita)

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-vers
