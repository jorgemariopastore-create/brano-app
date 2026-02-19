
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# --- 1. CONFIGURACIÓN ESTRUCTURAL (EL TÍTULO NUNCA DESAPARECE) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")
st.markdown("---")

# --- 2. MOTOR DE EXTRACCIÓN (CON REBOBINADO DE ARCHIVO) ---
def motor_extraccion_profesional(archivo_subido):
    # SENIOR FIX: Rebobinamos el archivo al inicio antes de leer
    archivo_subido.seek(0)
    bytes_pdf = archivo_subido.read()
    
    doc = fitz.open(stream=bytes_pdf, filetype="pdf")
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    
    # Limpieza total de espacios para que la Regex no falle
    t = " ".join(texto.split())
    
    # Diccionario con los datos reales del PDF
    d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
    
    # Patrones de búsqueda de alta precisión
    regex_map = {
        "pac": r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|DNI|$)",
        "fec": r"Fecha:\s*(\d{2}/\d{2}/\d{4})",
        "ddvi": r"DDVI\s*(\d+)",
        "dsvi": r"DSVI\s*(\d+)",
        "siv": r"(?:SIV|DDSIV)\s*(\d+)",
        "pp": r"(?:PP|DDPP)\s*(\d+)",
        "fey": r"(?:FEy|FA|eyeccion)\s*(\d+)"
    }
    
    for clave, patron in regex_map.items():
        match = re.search(patron, t, re.I)
        if match:
            d[clave] = match.group(1).strip()
    return d

# --- 3. GESTIÓN DE MEMORIA (DETECCIÓN DE CAMBIO DE PACIENTE) ---
if "datos_paciente" not in st.session_state:
    st.session_state.datos_paciente = None
if "archivo_id" not in st.session_state:
    st.session_state.archivo_id = None

with st.sidebar:
    st.header("Control de Estudio")
    archivo = st.file_uploader("Subir PDF del Estudio", type=["pdf"])
    # El botón de reset ahora solo se usa si usted quiere limpiar la pantalla manualmente
    if st.button("🗑️ Limpiar para nuevo paciente"):
        st.session_state.clear()
        st.rerun()

# --- 4. LÓGICA DE CARGA DINÁMICA ---
if archivo:
    # Creamos un ID único basado en el archivo
    id_actual = f"{archivo.name}_{archivo.size}"
    
    # Si sube un archivo nuevo (o cambió el que estaba), extraemos
    if st.session_state.archivo_id != id_actual:
        datos_nuevos = motor_extraccion_profesional(archivo)
        st.session_state.datos_paciente = datos_nuevos
        st.session_state.archivo_id = id_actual
        st.rerun() # Refrescamos para que los datos aparezcan en los cuadros

    # Mostramos los datos cargados en la sesión
    d = st.session_state.datos_paciente

    with st.form("validador_final"):
        st.subheader(f"Informe de: {d['pac'] if d['pac'] else 'Nuevo Estudio'}")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        pac = c1.text_input("Paciente", value=d["pac"])
        fec = c2.text_input("Fecha", value=d["fec"])
        # (Edad opcional según el PDF)
        
        st.markdown("### Métricas del Ecógrafo")
        
        

        c4, c5, c6, c7, c8 = st.columns(5)
        v_ddvi = c4.text_input("DDVI", value=d["ddvi"])
        v_dsvi = c5.text_input("DSVI", value=d["dsvi"])
        v_siv = c6.text_input("SIV", value=d["siv"])
        v_pp = c7.text_input("PP", value=d["pp"])
        v_fey = c8.text_input("FEy %", value=d["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL"):
            # Aquí se dispara el modelo de lenguaje con el formato "Pastore"
            st.success("Analizando datos y generando conclusión médica...")

else:
    st.info("👋 Dr. Pastore, cargue el PDF del estudio para visualizar los parámetros.")
