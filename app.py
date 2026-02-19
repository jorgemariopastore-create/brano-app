
import streamlit as st
from groq import Groq
import fitz
import re

# 1. API Key
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def extraccion_quirurgica(texto_sucio):
    """
    Limpia el texto de comillas, saltos de línea y basura de tablas.
    Luego extrae los datos basándose en el formato del SonoScape E3.
    """
    # Limpieza total: convertimos todo a una tira separada por comas
    t = texto_sucio.replace('"', '').replace('\n', ',').replace('\r', ',').replace(' ', '')
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # 1. Extraer Paciente (Busca después de PatientName o Paciente)
    m_pac = re.search(r"(?:PatientName|Paciente|Nombre),?([^,]+)", t, re.I)
    if m_pac:
        datos["pac"] = m_pac.group(1).replace('^', ' ').strip().upper()

    # 2. Extraer Valores por Etiquetas (Formato PDF/CSV)
    # Buscamos DDVI, luego una coma, y luego el número
    m_dv = re.search(r"DDVI,?([\d.]+)", t, re.I)
    m_si = re.search(r"(?:DDSIV|SIV),?([\d.]+)", t, re.I)
    m_fa = re.search(r"(?:FA|FE|EF),?([\d.]+)", t, re.I)

    if m_dv: datos["dv"] = m_dv.group(1)
    if m_si: datos["si"] = m_si.group(1)
    
    # Lógica de FEy: Si es FA (como el 38 de Alicia), calculamos FEy (~67)
    if m_fa:
        val_fa = float(m_fa.group(1))
        datos["fy"] = str(round(val_fa * 1.76)) if val_fa < 50 else str(val_fa)

    # 3. Respaldo Estructural (Si lo anterior falló, buscamos por rangos médicos)
    if not datos["dv"] or not datos["si"]:
        numeros = re.findall(r"([\d.]+)", t)
        for n in numeros:
            val = float(n)
            # Si el valor está en cm (ej 4.0), lo pasamos a mm (40.0)
            if 3.5 <= val <= 7.5: # Rango DDVI en cm
                datos["dv"] = str(val * 10)
            elif 0.6 <= val <= 1.6: # Rango SIV en cm
                datos["si"] = str(val * 10)
            elif 35 <= val <= 75: # Rango DDVI en mm
                datos["dv"] = str(val)
            elif 7 <= val <= 16: # Rango SIV en mm
                datos["si"] = str(val)

    return datos

st.set_page_config(page_title="CardioReport SonoScape", layout="wide")
st.title("🏥 Asistente Cardio SonoScape E3")

if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("Carga de Estudios")
    arc_txt = st.file_uploader("Subir TXT", type=["txt"])
    arc_pdf = st.file_uploader("Subir PDF", type=["pdf"])
    if st.button("🔄 Limpiar Todo"):
        st.session_state.datos = None
        st.rerun()

# Procesamiento
if (arc_txt or arc_pdf) and GROQ_KEY:
    if st.session_state.datos is None:
        with st.spinner("Procesando estructura de datos..."):
            texto_acumulado = ""
            if arc_txt:
                texto_acumulado += arc_txt.read().decode("latin-1", errors="ignore")
            if arc_pdf:
                with fitz.open(stream=arc_pdf.read(), filetype="pdf") as doc:
                    texto_acumulado += "\n".join([p.get_text() for p in doc])
            
            st.session_state.datos = extraccion_quirurgica(texto_acumulado)

# Formulario
if st.session_state.datos:
    with st.form("editor"):
        st.subheader("🔍 Confirmación de Datos")
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", st.session_state.datos["pac"])
        fey = c2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi = c3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv = c4.text_input("SIV mm", st.session_state.datos["si"])
        if st.form_submit_button("🚀 GENERAR INFORME"):
            st.session_state.datos.update({"pac": pac, "fy": fey, "dv": ddvi, "si": siv})
            client = Groq(api_key=GROQ_KEY)
            prompt = f"Informe médico Dr. Pastore. Paciente: {pac}. DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%."
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.markdown("---")
            st.info(res.choices[0].message.content)
            st.markdown("**Dr. Francisco A. Pastore**")
