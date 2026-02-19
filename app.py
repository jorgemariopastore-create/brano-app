
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# 1. Configuración de Secrets
# Asegúrate de tener en tu archivo .streamlit/secrets.toml:
# GROQ_API_KEY = "tu_clave_aqui"
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None
    st.error("⚠️ No se encontró 'GROQ_API_KEY' en los Secrets de Streamlit.")

def extraer_dato(texto, clave):
    # Soporta: "LVIDd: 50", "LVIDd=50", "LVIDd  50"
    patron = rf"{clave}\s*[:=\s]\s*([\d.,]+)"
    match = re.search(patron, texto, re.IGNORECASE)
    if match:
        return match.group(1).replace(',', '.')
    return ""

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

# Inicializar sesión
if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_txt = st.file_uploader("Archivo TXT del Equipo", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF (Nombre/Imágenes)", type=["pdf"])
    
    if st.button("🔄 Nuevo Paciente / Limpiar"):
        st.session_state.datos = None
        st.rerun()
    
    st.divider()
    st.caption("Configuración: API Key cargada desde Secrets ✅" if GROQ_KEY else "❌ API Key no configurada")

# 2. Procesamiento de archivos
if arc_txt and arc_pdf and GROQ_KEY:
    if st.session_state.datos is None:
        with st.spinner("Procesando archivos..."):
            t_raw = arc_txt.read().decode("latin-1", errors="ignore")
            p_bytes = arc_pdf.read()
            
            d = {"pac": "DESCONOCIDO", "fy": "", "dv": "", "si": ""}
            
            try:
                with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                    texto_pdf = "".join([pag.get_text() for pag in doc])
                    n_m = re.search(r"(?:Nombre|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
                    if n_m: d["pac"] = n_m.group(1).strip().upper()
            except: pass

            d["dv"] = extraer_dato(t_raw, "LVIDd")
            d["si"] = extraer_dato(t_raw, "IVSd")
            d["fy"] = extraer_dato(t_raw, "EF")
            
            st.session_state.datos = d

    # 3. Formulario persistente
    if st.session_state.datos:
        with st.form("editor_medico"):
            st.subheader("🔍 Revisión de Datos Extraídos")
            c1, c2 = st.columns(2)
            
            paciente = c1.text_input("Nombre completo", st.session_state.datos["pac"])
            fey = c1.text_input("FEy %", st.session_state.datos["fy"])
            ddvi = c2.text_input("DDVI mm", st.session_state.datos["dv"])
            siv = c2.text_input("SIV mm", st.session_state.datos["si"])
            
            submit = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

        if submit:
            # Actualizar estado antes de llamar a la IA
            st.session_state.datos.update({"pac": paciente, "fy": fey, "dv": ddvi, "si": siv})
            
            client = Groq(api_key=GROQ_KEY)
            prompt = (f"Genera un informe médico de ecocardiograma para {paciente}. "
                      f"Datos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. "
                      f"Usa lenguaje técnico y formal.")
            
            with st.spinner("Redactando informe..."):
                res = client.chat.completions.create(
                    model='llama-3.3-70b-versatile', 
                    messages=[{'role':'user','content':prompt}]
                )
                st.markdown("### 📄 Informe Sugerido")
                st.info(res.choices[0].message.content)

elif not GROQ_KEY:
    st.warning("Falta la configuración de la API Key en los Secrets del servidor.")
else:
    st.info("Cargue los archivos TXT y PDF para comenzar el análisis.")
