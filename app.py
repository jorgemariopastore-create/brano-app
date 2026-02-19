
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# --- 1. INTERFAZ INALTERABLE ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# --- 2. MOTOR DE EXTRACCIÓN (NIVEL SENIOR) ---
def extraer_datos(archivo_subido):
    # Leemos los bytes del archivo directamente
    bytes_pdf = archivo_subido.getvalue()
    doc = fitz.open(stream=bytes_pdf, filetype="pdf")
    texto_completo = ""
    for pagina in doc:
        texto_completo += pagina.get_text()
    
    # Limpiamos el texto para que la búsqueda sea infalible
    t = " ".join(texto_completo.split())
    
    # Diccionario de resultados
    d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
    
    # Regex mejoradas para evitar campos vacíos
    regex_map = {
        "pac": r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|$)",
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

# --- 3. LÓGICA DE CONTROL DE ESTADO ---
with st.sidebar:
    st.header("Panel de Control")
    archivo = st.file_uploader("Cargar estudio PDF", type=["pdf"])
    if st.button("🗑️ Resetear y Limpiar"):
        st.session_state.clear()
        st.rerun()

# --- 4. RENDERIZADO DE LA APLICACIÓN ---
if archivo:
    # Generamos un ID único por archivo para evitar que los datos se "peguen"
    id_actual = f"{archivo.name}_{archivo.size}"
    
    if st.session_state.get("id_archivo") != id_actual:
        # Extraemos datos y forzamos el guardado en la sesión
        st.session_state.datos_paciente = extraer_datos(archivo)
        st.session_state.id_archivo = id_actual
        st.rerun()

    # Si llegamos aquí, los datos DEBEN existir en session_state
    datos = st.session_state.datos_paciente

    with st.form("formulario_medico"):
        st.subheader(f"Validación: {datos['pac'] if datos['pac'] else 'Paciente sin nombre'}")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        nombre = col1.text_input("Paciente", value=datos["pac"])
        fecha = col2.text_input("Fecha", value=datos["fec"])
        edad = col3.text_input("Edad", value=datos.get("edad", ""))
        
        st.write("---")
        st.markdown("### Parámetros del Ecocardiograma")
        
        
        c1, c2, c3, c4, c5 = st.columns(5)
        ddvi = c1.text_input("DDVI", value=datos["ddvi"])
        dsvi = c2.text_input("DSVI", value=datos["dsvi"])
        siv = c3.text_input("SIV", value=datos["siv"])
        pp = c4.text_input("PP", value=datos["pp"])
        fey = c5.text_input("FEy %", value=datos["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME FINAL"):
            st.success("Procesando informe con IA...")

else:
    st.info("👋 Bienvenida/o. Por favor, suba un archivo PDF para visualizar los datos.")
