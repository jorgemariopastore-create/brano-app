
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io

# --- 1. CONFIGURACIÓN DE NÚCLEO (SIEMPRE VISIBLE) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")
st.markdown("---")

# --- 2. MOTOR DE EXTRACCIÓN ULTRA-ROBUSTO ---
def extraer_datos_pdf(archivo_objeto):
    try:
        # Leemos el contenido sin bloquear el archivo
        archivo_bytes = archivo_objeto.getvalue()
        doc = fitz.open(stream=archivo_bytes, filetype="pdf")
        
        texto_acumulado = ""
        for pagina in doc:
            texto_acumulado += pagina.get_text("text")
        
        # Limpieza de caracteres extraños y normalización de espacios
        t = " ".join(texto_acumulado.split())
        
        # Valores iniciales vacíos
        d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
        
        # Patrones de búsqueda (Regex) con mayor flexibilidad
        patrones = {
            "pac": r"Paciente:\s*([A-Z\s,]+?)(?=\s*(Fecha|Edad|DNI|Motivo|$))",
            "fec": r"Fecha:\s*(\d{2}/\d{2}/\d{4})",
            "ddvi": r"DDVI\s*(\d+)",
            "dsvi": r"DSVI\s*(\d+)",
            "siv": r"(?:SIV|DDSIV)\s*(\d+)",
            "pp": r"(?:PP|DDPP)\s*(\d+)",
            "fey": r"(?:FEy|FA|eyección|eyeccion)\s*(\d+)"
        }
        
        for clave, reg in patrones.items():
            match = re.search(reg, t, re.IGNORECASE)
            if match:
                d[clave] = match.group(1).strip()
        
        return d
    except Exception as e:
        st.error(f"Error técnico en la lectura: {e}")
        return None

# --- 3. GESTIÓN DE MEMORIA (SESSION STATE) ---
if "datos" not in st.session_state:
    st.session_state.datos = None
if "file_id" not in st.session_state:
    st.session_state.file_id = None

# --- 4. CARGA DE ARCHIVO ---
with st.sidebar:
    st.header("Entrada de Datos")
    archivo_subido = st.file_uploader("Arrastre aquí el PDF del estudio", type=["pdf"])
    
    if st.button("🗑️ Limpiar Pantalla"):
        st.session_state.clear()
        st.rerun()

# --- 5. LÓGICA DE ACTUALIZACIÓN ---
if archivo_subido:
    # Identificador único para detectar el cambio de archivo
    current_id = f"{archivo_subido.name}_{archivo_subido.size}"
    
    if st.session_state.file_id != current_id:
        with st.spinner("Analizando PDF..."):
            extraido = extraer_datos_pdf(archivo_subido)
            if extraido:
                st.session_state.datos = extraido
                st.session_state.file_id = current_id
                st.rerun()

    # Si hay datos en memoria, mostramos el formulario
    if st.session_state.datos:
        d = st.session_state.datos
        
        with st.form("validador_datos"):
            st.subheader(f"Datos del Paciente: {d['pac']}")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            nombre_pac = c1.text_input("Paciente", value=d["pac"])
            fecha_est = c2.text_input("Fecha", value=d["fec"])
            edad_pac = c3.text_input("Edad", value=d["edad"])
            
            st.markdown("### Parámetros de Cámara y Función")
            
            
            c4, c5, c6, c7, c8 = st.columns(5)
            v_ddvi = c4.text_input("DDVI (mm)", value=d["ddvi"])
            v_dsvi = c5.text_input("DSVI (mm)", value=d["dsvi"])
            v_siv = c6.text_input("SIV (mm)", value=d["siv"])
            v_pp = c7.text_input("PP (mm)", value=d["pp"])
            v_fey = c8.text_input("FEy (%)", value=d["fey"])
            
            if st.form_submit_button("🚀 GENERAR INFORME"):
                # Aquí la lógica de Groq con formato JUSTIFICADO y Arial 12
                st.info("Generando informe con estilo profesional...")

else:
    st.info("👋 Dr. Pastore, cargue el PDF para comenzar la extracción de datos.")
