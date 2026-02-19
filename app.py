
import streamlit as st
from groq import Groq
import fitz
import re

# 1. Configuración de API Key
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def parser_sonoscape_senior(texto_txt):
    """
    Parser estructural que extrae mediciones en modo M y las asigna
    según rangos biológicos lógicos para evitar errores de orden.
    """
    datos = {"pac": "DESCONOCIDO", "dv": "", "si": "", "fy": ""}
    
    # --- 1. Extraer Bloque Demográfico ---
    # El SonoScape usa etiquetas claras en la cabecera
    match_nombre = re.search(r"PatientName\s*,\s*\"([^\"]+)\"", texto_txt)
    if match_nombre:
        datos["pac"] = match_nombre.group(1).replace('^', ' ').strip().upper()

    # --- 2. Extraer Mediciones Modo M (Estructural) ---
    # Buscamos valores que acompañen a "cm" y "M"
    # El regex captura el número en el primer grupo
    valores_cm = re.findall(r"\"([\d.]+)\"\s*,\s*\"cm\"\s*,\s*\"M\"", texto_txt)
    
    # Convertimos a floats y a milímetros para procesar
    mediciones = [float(v) * 10 for v in valores_cm]

    if mediciones:
        # Lógica de asignación por rangos (Ventana Biológica)
        for m in mediciones:
            # Si mide entre 32 y 70mm, es altamente probable que sea el DDVI
            if 32 <= m <= 75:
                datos["dv"] = str(round(m, 1))
            # Si mide entre 6 y 16mm, es altamente probable que sea el SIV (Septum)
            elif 6 <= m <= 18:
                datos["si"] = str(round(m, 1))

    # --- 3. Extraer Función Sistólica (FEy) ---
    # Buscamos el valor que tenga la unidad "%"
    match_fey = re.search(r"\"([\d.]+)\"\s*,\s*\"%\"", texto_txt)
    if match_fey:
        datos["fy"] = match_fey.group(1)
    else:
        # Si no hay %, buscamos FA (Fracción de Acortamiento) y estimamos
        match_fa = re.search(r"\"FA\".*?\"([\d.]+)\"", texto_txt, re.I)
        if match_fa:
            fa_val = float(match_fa.group(1))
            datos["fy"] = str(round(fa_val * 1.7)) # Estimación de Teichholz rápida

    return datos

# --- INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="CardioReport SonoScape", layout="wide")
st.title("🏥 Asistente de Informes SonoScape E3")

if "datos" not in st.session_state:
    st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}

with st.sidebar:
    st.header("Carga de Datos")
    arc_txt = st.file_uploader("Subir TXT (SonoScape)", type=["txt"])
    arc_pdf = st.file_uploader("Subir PDF (Nombre/Referencia)", type=["pdf"])
    if st.button("Limpiar Sesión"):
        st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}
        st.rerun()

# Procesamiento
if arc_txt and GROQ_KEY:
    if st.session_state.datos["pac"] == "":
        with st.spinner("Parseando estructura SonoScape..."):
            raw_txt = arc_txt.read().decode("latin-1", errors="ignore")
            extraidos = parser_sonoscape_senior(raw_txt)
            
            # Refuerzo de nombre con PDF
            if arc_pdf:
                try:
                    with fitz.open(stream=arc_pdf.read(), filetype="pdf") as doc:
                        text_pdf = "".join([p.get_text() for p in doc])
                        n_m = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\n]*)", text_pdf, re.I)
                        if n_m: extraidos["pac"] = n_m.group(1).strip().upper()
                except: pass
            
            st.session_state.datos = extraidos

# Formulario de Validación
if st.session_state.datos["pac"] != "":
    with st.form("editor"):
        st.subheader("🔍 Revisión de Datos Estructurales")
        col1, col2, col3, col4 = st.columns(4)
        
        pac = col1.text_input("Paciente", st.session_state.datos["pac"])
        fey = col2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi = col3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv = col4.text_input("SIV mm", st.session_state.datos["si"])
        
        generar = st.form_submit_button("🚀 GENERAR INFORME")

    if generar:
        st.session_state.datos.update({"pac": pac, "fy": fey, "dv": ddvi, "si": siv})
        client = Groq(api_key=GROQ_KEY)
        
        prompt = f"""
        Actúa como el Dr. Francisco Pastore. Redacta conclusiones de ecocardiograma.
        Paciente: {pac}. Datos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%.
        - Si SIV >= 11mm: 'Remodelado concéntrico'.
        - Si FEy > 55%: 'Función sistólica global conservada'.
        Sé breve y profesional.
        """
        
        with st.spinner("Redactando..."):
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.markdown("---")
            st.info(res.choices[0].message.content)
            st.markdown("**Dr. Francisco A. Pastore**")
