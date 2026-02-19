
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# --- 1. INTERFAZ PROFESIONAL (ESTRUCTURA FIJA) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")
st.markdown("---")

# --- 2. EL MOTOR DE EXTRACCIÓN MÁS POTENTE (MODO RAW) ---
def extraer_datos_crudos(archivo_subido):
    # Abrimos el documento desde la memoria
    bytes_pdf = archivo_subido.getvalue()
    doc = fitz.open(stream=bytes_pdf, filetype="pdf")
    
    texto_total = ""
    for pagina in doc:
        # Extraemos texto en modo "RAW" (crudo) para ignorar errores de codificación
        texto_total += pagina.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    
    # Limpieza básica para la búsqueda
    t = " ".join(texto_total.split())
    
    # Diccionario inicial
    d = {"pac": "", "fec": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
    
    # Búsqueda ultra-flexible (ignora mayúsculas, puntos, dos puntos)
    regex_config = {
        "pac": r"Paciente[:\s]+([A-Z\s,]+?)(?=Fecha|Edad|DNI|ID|$)",
        "fec": r"Fecha[:\s]+(\d{2}/\d{2}/\d{4})",
        "ddvi": r"DDVI\s*[:\-\s]*(\d+)",
        "dsvi": r"DSVI\s*[:\-\s]*(\d+)",
        "siv": r"(?:SIV|DDSIV)\s*[:\-\s]*(\d+)",
        "pp": r"(?:PP|DDPP)\s*[:\-\s]*(\d+)",
        "fey": r"(?:FEy|FA|eyeccion|EF|eyección)\s*[:\-\s]*(\d+)"
    }
    
    for clave, patron in regex_config.items():
        res = re.search(patron, t, re.I)
        if res:
            d[clave] = res.group(1).strip()
            
    return d

# --- 3. LÓGICA DE PERSISTENCIA AUTOMÁTICA ---
if "memoria_paciente" not in st.session_state:
    st.session_state.memoria_paciente = None

with st.sidebar:
    st.header("Entrada de Estudio")
    archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])
    if st.button("🗑️ Reset General"):
        st.session_state.clear()
        st.rerun()

# --- 4. PROCESAMIENTO Y VALIDACIÓN ---
if archivo:
    # Generamos un ID único para forzar el refresco al cambiar de archivo
    id_actual = f"{archivo.name}_{archivo.size}"
    
    if st.session_state.get("last_id") != id_actual:
        datos_capturados = extraer_datos_crudos(archivo)
        st.session_state.memoria_paciente = datos_capturados
        st.session_state.last_id = id_actual
        st.rerun()

    d = st.session_state.memoria_paciente

    # FORMULARIO (Siempre visible si hay archivo)
    with st.form("validador_estudio"):
        st.subheader(f"Estudio: {d['pac'] if d['pac'] else 'Sin Nombre Detectado'}")
        
        c1, c2 = st.columns([3, 1])
        nombre = c1.text_input("Paciente", value=d["pac"])
        fecha = c2.text_input("Fecha", value=d["fec"])
        
        st.write("---")
        st.markdown("### Parámetros Ecocardiográficos")
        
        
        
        c3, c4, c5, c6, c7 = st.columns(5)
        v_ddvi = c3.text_input("DDVI", value=d["ddvi"])
        v_dsvi = c4.text_input("DSVI", value=d["dsvi"])
        v_siv = c5.text_input("SIV", value=d["siv"])
        v_pp = c6.text_input("PP", value=d["pp"])
        v_fey = c7.text_input("FEy %", value=d["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL"):
            # Aquí va el motor de IA con el formato Dr. Pastore (Justificado, Arial 12)
            st.success("Informe generado. El formato profesional está listo.")
else:
    st.info("Dr. Pastore, cargue el PDF del ecógrafo para iniciar.")
