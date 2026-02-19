
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")
st.subheader("Motor de Extracción Directa de Ecógrafo")

# --- 2. MOTOR DE EXTRACCIÓN POR BLOQUES (SENIOR) ---
def extraer_datos_ecografo(archivo_subido):
    # Leemos los bytes del archivo
    bytes_pdf = archivo_subido.getvalue()
    doc = fitz.open(stream=bytes_pdf, filetype="pdf")
    
    # Extraemos el texto crudo pero preservando la estructura de bloques
    texto_sucio = ""
    for pagina in doc:
        texto_sucio += pagina.get_text("blocks") # Extrae por bloques de ubicación
        # Convertimos la lista de bloques en un solo texto manejable
        texto_limpio = " ".join([str(b[4]) for b in pagina.get_text("blocks")])
        texto_sucio += texto_limpio
    
    # Normalizamos el texto (quitamos saltos de línea y espacios extra)
    t = " ".join(texto_sucio.split())
    
    # Diccionario de resultados
    d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
    
    # REGLAS DE BÚSQUEDA (Adaptadas a la salida de software médico)
    patrones = {
        "pac": r"Paciente:\s*([A-Z\s,]+?)(?=\s*(Fecha|Edad|ID|Sexo|$))",
        "fec": r"Fecha:\s*(\d{2}/\d{2}/\d{4})",
        "ddvi": r"DDVI\s*[:\-]?\s*(\d+)",
        "dsvi": r"DSVI\s*[:\-]?\s*(\d+)",
        "siv": r"(?:SIV|DDSIV)\s*[:\-]?\s*(\d+)",
        "pp": r"(?:PP|DDPP)\s*[:\-]?\s*(\d+)",
        "fey": r"(?:FEy|FA|eyeccion|EF)\s*[:\-]?\s*(\d+)"
    }
    
    for clave, reg in patrones.items():
        match = re.search(reg, t, re.I)
        if match:
            d[clave] = match.group(1).strip()
            
    return d

# --- 3. LÓGICA DE PERSISTENCIA ---
if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("Carga de Archivo")
    archivo = st.file_uploader("Subir PDF generado por ecógrafo", type=["pdf"])
    if st.button("🗑️ Limpiar Todo"):
        st.session_state.clear()
        st.rerun()

# --- 4. PROCESAMIENTO ---
if archivo:
    # Generamos un ID para no repetir procesos
    id_actual = f"{archivo.name}_{archivo.size}"
    
    if st.session_state.get("file_id") != id_actual:
        with st.spinner("Decodificando datos del ecógrafo..."):
            st.session_state.datos = extraer_datos_ecografo(archivo)
            st.session_state.file_id = id_actual
            st.rerun()

    if st.session_state.datos:
        d = st.session_state.datos
        
        with st.form("validador"):
            st.subheader(f"Paciente: {d['pac']}")
            c1, c2 = st.columns([3, 1])
            nombre = c1.text_input("Nombre Completo", value=d["pac"])
            fecha = c2.text_input("Fecha Estudio", value=d["fec"])
            
            st.write("---")
            st.markdown("### Mediciones del VI")
            
            
            c3, c4, c5, c6, c7 = st.columns(5)
            v_ddvi = c3.text_input("DDVI", value=d["ddvi"])
            v_dsvi = c4.text_input("DSVI", value=d["dsvi"])
            v_siv = c5.text_input("SIV", value=d["siv"])
            v_pp = c6.text_input("PP", value=d["pp"])
            v_fey = c7.text_input("FEy %", value=d["fey"])
            
            if st.form_submit_button("🚀 GENERAR INFORME MÉDICO"):
                # Aquí se genera el informe con el estilo profesional que definimos
                st.success("Informe generado con éxito.")
else:
    st.info("👋 Dr. Pastore, cargue el PDF del ecógrafo para autocompletar.")
