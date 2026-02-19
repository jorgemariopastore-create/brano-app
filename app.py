
import streamlit as st
from groq import Groq
import fitz
import re
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")

# 1. GESTIÓN DE MEMORIA (Limpieza automática al cambiar de PDF)
if "archivo_actual" not in st.session_state:
    st.session_state.archivo_actual = None
if "datos_paciente" not in st.session_state:
    st.session_state.datos_paciente = {}

def limpiar_sesion():
    st.session_state.informe_ia = ""
    st.session_state.word_doc = None
    st.session_state.datos_paciente = {}

# 2. MOTOR DE EXTRACCIÓN (Ahora sin valores "fijos" de Alicia)
def extraer_datos_fieles(doc_pdf):
    texto = ""
    for pag in doc_pdf: texto += pag.get_text()
    t = re.sub(r'[\"\'\r\t]', '', texto)
    t = re.sub(r'\n+', ' ', t)
    
    # Buscamos datos reales del PDF actual
    d = {"pac": "NO DETECTADO", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": "", "ai": ""}
    
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|DNI|$)", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    m_fec = re.search(r"Fecha(?:\s*de\s*estudio)?:\s*(\d{2}/\d{2}/\d{4})", t, re.I)
    if m_fec: d["fec"] = m_fec.group(1)

    reg = {"ddvi": r"DDVI\s+(\d+)", "dsvi": r"DSVI\s+(\d+)", "siv": r"SIV\s+(\d+)", 
           "pp": r"PP\s+(\d+)", "fey": r"eyección\s+del\s+VI\s+(\d+)", "ai": r"AI\s+(\d+)"}
    
    for k, v in reg.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
    return d

# --- INTERFAZ ---
st.title("🏥 Sistema de Informes Multivista")

with st.sidebar:
    archivo = st.file_uploader("Subir PDF del Paciente", type=["pdf"])
    # Si el archivo cambió, reseteamos la memoria
    if archivo:
        if st.session_state.archivo_actual != archivo.name:
            st.session_state.archivo_actual = archivo.name
            limpiar_sesion() # Borra a Alicia para dejar pasar al nuevo
            st.rerun()

if archivo:
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    
    # Solo extraemos si la memoria está vacía
    if not st.session_state.datos_paciente:
        st.session_state.datos_paciente = extraer_datos_fieles(pdf)
    
    d = st.session_state.datos_paciente

    with st.form("validador_dinamico"):
        st.subheader(f"Validación: {d['pac']}")
        c1, c2, c3 = st.columns([2,1,1])
        pac = c1.text_input("Nombre del Paciente", d["pac"])
        fec = c2.text_input("Fecha", d["fec"])
        edad = c3.text_input("Edad", d["edad"])
        
        c4, c5 = st.columns(2)
        peso = c4.text_input("Peso (kg)", "")
        alt = c5.text_input("Altura (cm)", "")
        
        st.markdown("**Valores Ecocardiográficos**")
        c6, c7, c8, c9, c10 = st.columns(5)
        ddvi = c6.text_input("DDVI", d["ddvi"])
        dsvi = c7.text_input("DSVI", d["dsvi"])
        siv = c8.text_input("SIV", d["siv"])
        pp = c9.text_input("PP", d["pp"])
        fey = c10.text_input("FEy %", d["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME"):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            prompt = f"""Actúa como el Dr. Pastore. Redacta el cuerpo de un informe detallado.
            DATOS: DDVI {ddvi}mm, DSVI {dsvi}mm, SIV {siv}mm, PP {pp}mm, FEy {fey}%.
            REGLAS: Justificado, sin repetir nombre, 3 secciones (HALLAZGOS, VALVULAS, CONCLUSION)."""
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.informe_ia = res.choices[0].message.content
            # Aquí va la función crear_word_profesional (igual a la anterior con Justificado)
            # [Omitida por brevedad, pero debe estar en tu código]
