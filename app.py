
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# 1. Configuración de API Key desde Secrets
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None

def extraer_con_precision(texto, patrones):
    """
    Busca valores numéricos en tablas o texto.
    Ejemplo: Busca 'DDVI' seguido de comas, comillas o espacios y luego el número.
    """
    for p in patrones:
        # Esta regex es más agresiva: busca la palabra clave y salta caracteres
        # especiales (como los de las tablas CSV/PDF) hasta encontrar el número.
        regex = rf"{p}.*?[\" \t,:=]*\s*([\d.,]+)"
        match = re.search(regex, texto, re.IGNORECASE)
        if match:
            valor = match.group(1).replace(',', '.')
            # Limpieza de puntos finales si el regex capturó de más
            valor = re.sub(r'\.$', '', valor)
            return valor
    return ""

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

# Inicialización del estado de sesión
if "datos" not in st.session_state:
    st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_txt = st.file_uploader("Subir Archivo TXT", type=["txt"])
    arc_pdf = st.file_uploader("Subir Informe PDF", type=["pdf"])
    
    if st.button("🔄 Limpiar y Nuevo Paciente"):
        st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}
        st.rerun()

# 2. Procesamiento de extracción
# Solo procesamos si hay archivos nuevos y el estado está vacío
if (arc_txt or arc_pdf) and GROQ_KEY:
    # Verificamos si ya extrajimos datos para no sobreescribir lo que el usuario edite
    if st.session_state.datos["pac"] == "":
        with st.spinner("Analizando archivos..."):
            texto_acumulado = ""
            
            # Leer TXT si existe
            if arc_txt:
                texto_acumulado += arc_txt.read().decode("latin-1", errors="ignore") + "\n"
            
            # Leer PDF si existe
            if arc_pdf:
                try:
                    with fitz.open(stream=arc_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_acumulado += pagina.get_text()
                except: pass

            # EXTRACCIÓN MAESTRA (ajustada a los nombres del equipo de Alicia)
            nombre_match = re.search(r"(?:Paciente|Nombre pac\.|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto_acumulado, re.I)
            
            # Llenamos el session_state directamente
            st.session_state.datos["pac"] = nombre_match.group(1).strip().upper() if nombre_match else "DESCONOCIDO"
            st.session_state.datos["dv"] = extraer_con_precision(texto_acumulado, ["DDVI", "Diám. Diastólico", "LVIDd"])
            st.session_state.datos["si"] = extraer_con_precision(texto_acumulado, ["DDSIV", "SIV", "Septum", "IVSd"])
            
            # La FEy en el informe de Alicia puede ser FA (Fracción de Acortamiento) o EF(A4C)
            fey_detectada = extraer_con_precision(texto_acumulado, [r"EF\(A4C\)", "FEVI", "FA", "Fracción de eyección"])
            st.session_state.datos["fy"] = fey_detectada

# 3. Interfaz de Usuario (Siempre lee de st.session_state)
if st.session_state.datos["pac"] != "" or arc_pdf:
    with st.form("editor_final"):
        st.subheader("🔍 Validar y Corregir Datos")
        st.info("El sistema extrajo estos valores. Si falta alguno, complételo manualmente.")
        
        c1, c2, c3, c4 = st.columns(4)
        # Usamos 'value' para precargar lo extraído, pero el usuario puede cambiarlo
        pac_edit = c1.text_input("Paciente", st.session_state.datos["pac"])
        fey_edit = c2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi_edit = c3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv_edit = c4.text_input("SIV mm", st.session_state.datos["si"])
        
        btn_informe = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

    if btn_informe:
        # Actualizamos el estado con los valores finales del formulario
        st.session_state.datos.update({"pac": pac_edit, "fy": fey_edit, "dv": ddvi_edit, "si": siv_edit})
        
        if not fey_edit or not ddvi_edit:
            st.error("Error: La FEy y el DDVI son necesarios para un informe preciso.")
        else:
            client = Groq(api_key=GROQ_KEY)
            # Prompt optimizado para el estilo del Dr. Pastore
            prompt = f"""
            Redacta un informe médico profesional para {pac_edit}. 
            Valores: DDVI {ddvi_edit}mm, SIV {siv_edit}mm, FEy {fey_edit}%.
            
            REGLAS:
            1. Usa un tono técnico y formal (estilo Dr. Francisco Pastore).
            2. Si FEy > 55%, indica 'Función sistólica global conservada'.
            3. Si SIV >= 11mm y DDVI normal (aprox 40-50mm), indica 'Remodelado concéntrico'.
            4. No digas que faltan datos. Si los valores están arriba, úsalos.
            """
            
            with st.spinner("La IA está redactando..."):
                res = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[{'role':'user', 'content': prompt}]
                )
                
                st.markdown("---")
                st.markdown("### 📄 Informe Médico Generado")
                st.info(res.choices[0].message.content)
                st.markdown("**Dr. Francisco A. Pastore**")

elif not GROQ_KEY:
    st.error("Falta la GROQ_API_KEY en los Secrets.")
else:
    st.info("Esperando archivos para procesar...")
