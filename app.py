
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def limpiar_y_extraer_todo(texto_combinado):
    # Paso 1: Limpieza agresiva para eliminar ruido de tablas y saltos
    t = texto_combinado.replace('"', '').replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # Paso 2: Extraer Paciente (Busca en ambos formatos)
    m_pac = re.search(r"(?:Paciente|Nombre pac\.|PatientName)\s*[:\-,]?\s*([^,]+)", t, re.I)
    if m_pac:
        datos["pac"] = m_pac.group(1).replace('^', ' ').strip().upper()

    # Paso 3: Búsqueda por etiquetas específicas (prioridad PDF/TXT limpio)
    # Buscamos DDVI y el primer número que lo siga
    m_dv = re.search(r"DDVI\s*(\d+)", t, re.I)
    # Buscamos DDSIV o SIV
    m_si = re.search(r"(?:DDSIV|SIV)\s*(\d+)", t, re.I)
    # Buscamos FEy (en el PDF de Alicia está como 'Fracción de eyección del VI 67%')
    m_fe = re.search(r"(?:FE|EF|Fracción\s*de\s*eyección)\s*(?:del\s*VI)?\s*(\d+)", t, re.I)
    # Si no hay FE, buscamos FA (Fracción de acortamiento)
    m_fa = re.search(r"FA\s*(\d+)", t, re.I)

    if m_dv: datos["dv"] = m_dv.group(1)
    if m_si: datos["si"] = m_si.group(1)
    
    if m_fe:
        datos["fy"] = m_fe.group(1)
    elif m_fa:
        # Si solo tenemos FA (ej. 38), calculamos la FE aproximada (~67)
        datos["fy"] = str(round(float(m_fa.group(1)) * 1.76))

    return datos

st.set_page_config(page_title="SonoScape Elite Hybrid", layout="wide")
st.title("🏥 Asistente Cardio: Extracción TXT + PDF")

# Widget para subir MULTIPLES archivos
archivos = st.sidebar.file_uploader("Subir archivos (TXT y PDF de Alicia)", type=["txt", "pdf"], accept_multiple_files=True)

if st.sidebar.button("🗑️ Resetear Sistema"):
    st.session_state.datos_hibridos = None
    st.rerun()

if archivos and GROQ_KEY:
    texto_total = ""
    for arc in archivos:
        if arc.type == "application/pdf":
            doc = fitz.open(stream=arc.read(), filetype="pdf")
            texto_total += " ".join([pag.get_text() for pag in doc])
        else:
            texto_total += arc.read().decode("latin-1", errors="ignore")
    
    # Procesamos el texto combinado de todos los archivos subidos
    st.session_state.datos_hibridos = limpiar_y_extraer_todo(texto_total)

if "datos_hibridos" in st.session_state and st.session_state.datos_hibridos:
    with st.form("validador_final"):
        d = st.session_state.datos_hibridos
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", d["pac"])
        fey = c2.text_input("FEy %", d["fy"])
        ddvi = c3.text_input("DDVI mm", d["dv"])
        siv = c4.text_input("SIV mm", d["si"])
        
        if st.form_submit_button("🚀 GENERAR INFORME MÉDICO"):
            client = Groq(api_key=GROQ_KEY)
            prompt = f"Informe: Paciente {pac}, DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. Estilo Dr. Pastore."
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.info(res.choices[0].message.content)
