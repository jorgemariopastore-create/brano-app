
import streamlit as st
from groq import Groq
import fitz # PyMuPDF
import re

# --- CONFIGURACIÓN DE INTERFAZ (NUNCA DESAPARECE) ---
st.set_page_config(page_title="CardioReport Senior", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# 1. MOTOR DE EXTRACCIÓN SEGURO
def motor_extraccion_senior(archivo):
    # Usamos .read() pero aseguramos que el puntero vuelva al inicio
    archivo.seek(0)
    bytes_pdf = archivo.read()
    doc = fitz.open(stream=bytes_pdf, filetype="pdf")
    texto = " ".join([pag.get_text() for pag in doc])
    t = " ".join(texto.split()) # Limpieza total
    
    d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
    
    # Mapeo de precisión
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
        if match: d[clave] = match.group(1).strip()
    return d

# --- 2. GESTIÓN DE MEMORIA INTELIGENTE ---
# Esto evita que los datos de un paciente se "peguen" al siguiente
if "id_archivo_activo" not in st.session_state:
    st.session_state.id_archivo_activo = None

with st.sidebar:
    st.header("Estudio Actual")
    nuevo_archivo = st.file_uploader("Cargar PDF", type=["pdf"])
    if st.button("🗑️ Limpiar Todo"):
        st.session_state.clear()
        st.rerun()

# --- 3. LÓGICA DE ACTUALIZACIÓN AUTOMÁTICA ---
if nuevo_archivo:
    id_detectado = f"{nuevo_archivo.name}_{nuevo_archivo.size}"
    
    # Si el ID cambia, actualizamos la memoria automáticamente SIN perder la app
    if st.session_state.id_archivo_activo != id_detectado:
        st.session_state.datos_paciente = motor_extraccion_senior(nuevo_archivo)
        st.session_state.id_archivo_activo = id_detectado
        st.session_state.informe_generado = "" # Limpia el informe viejo
        st.rerun()

    # Recuperamos datos de la sesión
    d = st.session_state.datos_paciente

    # --- 4. INTERFAZ DE VALIDACIÓN (SIEMPRE VISIBLE) ---
    with st.form("form_medico"):
        st.subheader(f"Validación: {d['pac'] if d['pac'] else 'Nuevo Paciente'}")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        pac = col1.text_input("Paciente", value=d["pac"])
        fec = col2.text_input("Fecha", value=d["fec"])
        edad = col3.text_input("Edad", value=d.get("edad", ""))
        
        st.write("---")
        st.markdown("### Parámetros Técnicos")
        
        

        c1, c2, c3, c4, c5 = st.columns(5)
        v_ddvi = c1.text_input("DDVI", value=d["ddvi"])
        v_dsvi = c2.text_input("DSVI", value=d["dsvi"])
        v_siv = c3.text_input("SIV", value=d["siv"])
        v_pp = c4.text_input("PP", value=d["pp"])
        v_fey = c5.text_input("FEy %", value=d["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME PASTORE"):
            # Aquí va el prompt que ya teníamos: Justificado, Arial 12, Seco y Profesional
            # (El código de Groq se mantiene igual para no perder el estilo)
            st.info("Generando informe con el estilo profesional del Dr. Pastore...")
            # ... lógica de IA ...

else:
    st.info("👋 Por favor, suba un estudio para comenzar.")
