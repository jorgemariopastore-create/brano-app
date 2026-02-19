
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# Configuración de API Key
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None

def limpiar_valor(texto):
    """Extrae solo el número de una cadena sucia (ej: '40 mm' -> '40')"""
    match = re.search(r"([\d.,]+)", texto)
    if match:
        valor = match.group(1).replace(',', '.')
        return valor
    return ""

def extraer_dato_maestro(texto, etiquetas):
    """Busca en el texto usando múltiples variantes de etiquetas médicas."""
    for etiqueta in etiquetas:
        # Busca la etiqueta, ignora lo que haya en el medio hasta encontrar un número
        patron = rf"{etiqueta}.*?[:=\s]\s*([\d.,]+)"
        match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if match:
            return limpiar_valor(match.group(1))
    return ""

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_txt = st.file_uploader("Archivo TXT del Equipo", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF (Alicia Albornoz)", type=["pdf"])
    
    if st.button("🔄 Nuevo Paciente / Limpiar"):
        st.session_state.datos = None
        st.rerun()

# Procesamiento
if arc_txt and arc_pdf and GROQ_KEY:
    if st.session_state.datos is None:
        with st.spinner("Extrayendo información..."):
            t_raw = arc_txt.read().decode("latin-1", errors="ignore")
            
            # Procesar PDF para nombre
            p_bytes = arc_pdf.read()
            nombre = "DESCONOCIDO"
            texto_pdf = ""
            try:
                with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                    texto_pdf = "".join([pag.get_text() for pag in doc])
                    n_m = re.search(r"(?:Paciente|Nombre pac\.)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
                    if n_m: nombre = n_m.group(1).strip().upper()
            except: pass

            # Extraer datos técnicos combinando fuentes (Prioridad TXT, apoyo PDF)
            # Combinamos ambos textos para tener más probabilidad de éxito
            texto_total = t_raw + "\n" + texto_pdf

            d = {
                "pac": nombre,
                "dv": extraer_dato_maestro(texto_total, ["DDVI", "LVIDd", "Diám. Diastólico"]),
                "si": extraer_dato_maestro(texto_total, ["DDSIV", "IVSd", "SIV", "Septum"]),
                "fy": extraer_dato_maestro(texto_total, [r"EF\(A4C\)", "FEVI", "FA", "EF", "Fracción de eyección"])
            }
            st.session_state.datos = d

    # Formulario de validación
    if st.session_state.datos:
        with st.form("validador"):
            st.subheader("🔍 Verifique los datos antes de generar")
            c1, c2, c3, c4 = st.columns(4)
            
            paciente = c1.text_input("Paciente", st.session_state.datos["pac"])
            fey = c2.text_input("FEy %", st.session_state.datos["fy"])
            ddvi = c3.text_input("DDVI mm", st.session_state.datos["dv"])
            siv = c4.text_input("SIV mm", st.session_state.datos["si"])
            
            submit = st.form_submit_button("🚀 GENERAR INFORME")

        if submit:
            if not fey or not ddvi:
                st.warning("⚠️ Faltan datos críticos. Por favor complételos manualmente si no fueron detectados.")
            
            client = Groq(api_key=GROQ_KEY)
            prompt = f"""
            Genera un informe médico de ecocardiograma para el paciente {paciente}.
            Utiliza estrictamente estos valores: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%.
            
            Estilo: Dr. Francisco Pastore (Técnico, preciso).
            - Si FEy > 55%: 'Función sistólica global del VI conservada'.
            - Si SIV >= 11mm y DDVI normal: 'Remodelado concéntrico del VI'.
            - No menciones que faltan datos si los valores están presentes.
            """
            
            with st.spinner("Redactando..."):
                res = client.chat.completions.create(
                    model='llama-3.3-70b-versatile', 
                    messages=[{'role':'user','content':prompt}]
                )
                st.markdown("---")
                st.markdown(f"### Informe Médico: {paciente}")
                st.write(res.choices[0].message.content)
                st.markdown("**Dr. Francisco A. Pastore**")
