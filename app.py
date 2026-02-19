
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# 1. Configuración de API Key
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None

def extraer_dato_txt(texto, clave):
    """
    Extracción robusta para el TXT del equipo.
    Soporta: 'LVIDd: 50', 'LVIDd=50', 'LVIDd  50', 'LVIDd....50'
    """
    # Busca la clave + cualquier caracter no numérico + el número
    patron = rf"{clave}.*?[:=\s]\s*([\d.]+)"
    match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    return ""

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

# Estado de sesión para persistencia
if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_txt = st.file_uploader("Archivo TXT (Datos del equipo)", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF (Referencia/Nombre)", type=["pdf"])
    
    if st.button("🔄 Nuevo Paciente"):
        st.session_state.datos = None
        st.rerun()

# 2. Lógica de Procesamiento Combinada
if arc_txt and arc_pdf and GROQ_KEY:
    if st.session_state.datos is None:
        with st.spinner("Procesando archivos..."):
            # Leer TXT (Datos técnicos)
            t_raw = arc_txt.read().decode("latin-1", errors="ignore")
            
            # Leer PDF (Datos personales y contexto)
            p_bytes = arc_pdf.read()
            nombre_paciente = "NO ENCONTRADO"
            try:
                with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                    texto_pdf = "".join([pag.get_text() for pag in doc])
                    n_m = re.search(r"(?:Paciente|Nombre pac\.)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
                    if n_m: nombre_paciente = n_m.group(1).strip().upper()
            except: pass

            # Extraer valores del TXT usando las etiquetas del equipo
            # Nota: Ajusté las etiquetas a las comunes de ecógrafos (LVIDd, IVSd, EF)
            d = {
                "pac": nombre_paciente,
                "dv": extraer_dato_txt(t_raw, "LVIDd") or extraer_dato_txt(t_raw, "DDVI"),
                "si": extraer_dato_txt(t_raw, "IVSd") or extraer_dato_txt(t_raw, "DDSIV"),
                "fy": extraer_dato_txt(t_raw, "EF") or extraer_dato_txt(t_raw, "FEVI")
            }
            st.session_state.datos = d

    # 3. Formulario de Edición
    if st.session_state.datos:
        with st.form("editor_medico"):
            st.subheader("🔍 Validar Datos Extraídos")
            col1, col2 = st.columns(2)
            
            paciente = col1.text_input("Paciente", st.session_state.datos["pac"])
            fey = col1.text_input("FEy %", st.session_state.datos["fy"])
            ddvi = col2.text_input("DDVI mm", st.session_state.datos["dv"])
            siv = col2.text_input("SIV mm", st.session_state.datos["si"])
            
            btn_generar = st.form_submit_button("🚀 GENERAR INFORME")

        if btn_generar:
            # Actualizar session_state con cambios manuales
            st.session_state.datos.update({"pac": paciente, "fy": fey, "dv": ddvi, "si": siv})
            
            client = Groq(api_key=GROQ_KEY)
            prompt = f"""
            Actúa como el Dr. Francisco Pastore. Redacta un informe médico basado en:
            Paciente: {paciente}
            DDVI: {ddvi}mm, SIV: {siv}mm, FEy: {fey}%.
            
            Usa términos como 'Función sistólica global conservada' si la FEy es normal.
            Si el DDVI es ~40 y SIV >= 11, menciona 'Remodelado concéntrico'.
            Sé breve y profesional.
            """
            
            with st.spinner("Redactando..."):
                res = client.chat.completions.create(
                    model='llama-3.3-70b-versatile', 
                    messages=[{'role':'user','content':prompt}]
                )
                st.markdown("---")
                st.info(res.choices[0].message.content)
                st.markdown("**Dr. Francisco A. Pastore**")

elif not GROQ_KEY:
    st.error("Falta la API Key en Secrets.")
