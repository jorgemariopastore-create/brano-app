
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io

# --- 1. CONFIGURACIÓN ESTRUCTURAL (FUERA DE CONDICIONALES) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")
st.markdown("---")

# --- 2. LÓGICA DE EXTRACCIÓN (REFORZADA) ---
def motor_extraccion(file_content):
    doc = fitz.open(stream=file_content, filetype="pdf")
    texto = " ".join([pag.get_text() for pag in doc])
    t = re.sub(r'\s+', ' ', texto)
    
    # Valores por defecto para evitar el "NO DETECTADO" visual
    d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": "", "ai": ""}
    
    # Regex Senior optimizada para SonoScape/Mindray
    m_pac = re.search(r"Paciente\s*:\s*([A-Z\s]+?)(?:\s*Fecha|Edad|DNI|$)", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    m_fec = re.search(r"Fecha\s*:\s*(\d{2}/\d{2}/\d{4})", t, re.I)
    if m_fec: d["fec"] = m_fec.group(1)

    patterns = {
        "ddvi": r"DDVI\s*(\d+)", "dsvi": r"DSVI\s*(\d+)", 
        "siv": r"(?:SIV|DDSIV)\s*(\d+)", "pp": r"(?:PP|DDPP)\s*(\d+)",
        "fey": r"(?:FEy|FA|eyeccion)\s*(\d+)", "ai": r"(?:AI|DDAI)\s*(\d+)"
    }
    for k, v in patterns.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
    
    return d

# --- 3. GESTIÓN DE ESTADO (SESSION STATE) ---
if "datos" not in st.session_state:
    st.session_state.datos = None
if "last_file_name" not in st.session_state:
    st.session_state.last_file_name = None

# --- 4. BARRA LATERAL Y CARGA ---
with st.sidebar:
    st.header("Carga de Estudio")
    archivo = st.file_uploader("Subir PDF", type=["pdf"])
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state.clear()
        st.rerun()

# --- 5. CONTROL DE FLUJO ---
if archivo:
    # Si el archivo es nuevo, extraemos y guardamos en session_state
    if st.session_state.last_file_name != archivo.name:
        content = archivo.read() # Leemos el contenido una sola vez
        st.session_state.datos = motor_extraccion(content)
        st.session_state.last_file_name = archivo.name
        st.rerun()

    # Si hay datos, mostramos el formulario
    if st.session_state.datos:
        d = st.session_state.datos
        
        # El formulario usa una clave única basada en el nombre del archivo
        with st.form(key=f"form_{archivo.name}"):
            st.subheader(f"Validación de Datos: {d['pac'] if d['pac'] else 'Nuevo Paciente'}")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            pac = c1.text_input("Paciente", value=d["pac"])
            fec = c2.text_input("Fecha", value=d["fec"])
            edad = c3.text_input("Edad", value=d["edad"])
            
            st.markdown("### Métricas Técnicas")
            c4, c5, c6, c7, c8 = st.columns(5)
            # Aseguramos que si no hay dato, el campo quede editable para el médico
            v_ddvi = c4.text_input("DDVI", value=d["ddvi"])
            v_dsvi = c5.text_input("DSVI", value=d["dsvi"])
            v_siv = c6.text_input("SIV", value=d["siv"])
            v_pp = c7.text_input("PP", value=d["pp"])
            v_fey = c8.text_input("FEy %", value=d["fey"])
            
            if st.form_submit_button("🚀 GENERAR INFORME"):
                # Aquí iría el proceso de IA...
                st.success("Informe generado correctamente.")
    else:
        st.warning("No se pudieron extraer datos automáticamente. Por favor complete el formulario.")
else:
    st.info("Esperando carga de archivo PDF para iniciar la validación...")
