
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. LÓGICA DE EXTRACCIÓN ROBUSTA ---
def limpiar_texto(t):
    # Elimina caracteres nulos y normaliza espacios
    return " ".join(t.split())

def extraer_dato_seguro(texto, etiqueta):
    # Buscamos la etiqueta y capturamos el valor numérico en un rango cercano (200 caracteres)
    # Esto evita saltos accidentales a otros bloques [MEASUREMENT]
    patron = rf"{etiqueta}.{{0,200}}?value\s*=\s*([\d.]+)"
    match = re.search(patron, texto, re.S | re.I)
    if match:
        try:
            val = float(match.group(1))
            return str(int(val)) if val.is_integer() else str(val)
        except: return match.group(1)
    return "--"

# --- 2. GESTIÓN DE ESTADO (SESSION STATE) ---
def inicializar_estado():
    if 'datos' not in st.session_state:
        st.session_state.datos = {
            "pac": "", "ed": "", "fecha": "", 
            "dv": "--", "si": "--", "fy": "60", "dr": "--", "ai": "--"
        }
    if 'informe_generado' not in st.session_state:
        st.session_state.informe_generado = ""

# --- 3. PROCESAMIENTO ---
def procesar_archivos_a_estado(txt_bytes, pdf_bytes):
    txt_raw = txt_bytes.decode("latin-1", errors="ignore")
    # Extraer del PDF
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pdf_text = doc[0].get_text()
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", pdf_text)
            if f_m: st.session_state.datos["fecha"] = f_m.group(1)
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", pdf_text, re.I)
            if n_m: st.session_state.datos["pac"] = n_m.group(1).strip().upper()
    except: pass

    # Extraer del TXT (Mapeo técnico)
    st.session_state.datos["ed"] = re.search(r"Age\s*=\s*(\d+)", txt_raw, re.I).group(1) if re.search(r"Age\s*=\s*(\d+)", txt_raw, re.I) else "--"
    st.session_state.datos["dv"] = extraer_dato_seguro(txt_raw, "LVIDd")
    st.session_state.datos["si"] = extraer_dato_seguro(txt_raw, "IVSd")
    st.session_state.datos["dr"] = extraer_dato_seguro(txt_raw, "AORootDiam")
    st.session_state.datos["ai"] = extraer_dato_seguro(txt_raw, "LADiam")
    st.session_state.datos["fy"] = extraer_dato_seguro(txt_raw, "EF")

# --- INTERFAZ ---
st.set_page_config(page_title="CardioPro 43.0", layout="wide")
inicializar_estado()

st.title("🏥 CardioReport Pro v43.0 (Logic-First)")

with st.sidebar:
    st.header("1. Carga de Archivos")
    u_txt = st.file_uploader("Subir TXT", type=["txt"])
    u_pdf = st.file_uploader("Subir PDF", type=["pdf"])
    
    if st.button("🔄 Extraer Datos Nuevos") and u_txt and u_pdf:
        procesar_archivos_a_estado(u_txt.read(), u_pdf.getvalue())
        st.success("¡Datos extraídos! Ahora puedes editarlos.")

# --- 4. FORMULARIO DE EDICIÓN (Persistente) ---
st.subheader("🔍 Confirmación de Datos")
c1, c2, c3 = st.columns(3)

# Vinculamos los inputs directamente al session_state
st.session_state.datos["pac"] = c1.text_input("Paciente", st.session_state.datos["pac"])
st.session_state.datos["fy"] = c1.text_input("FEy (%)", st.session_state.datos["fy"])
st.session_state.datos["ed"] = c2.text_input("Edad", st.session_state.datos["ed"])
st.session_state.datos["dv"] = c2.text_input("DDVI (mm)", st.session_state.datos["dv"])
st.session_state.datos["fecha"] = c3.text_input("Fecha", st.session_state.datos["fecha"])
st.session_state.datos["si"] = c3.text_input("Septum (mm)", st.session_state.datos["si"])

# --- 5. GENERACIÓN CON PROMPT OPTIMIZADO ---
if st.button("🚀 Generar Informe Médico"):
    if not st.secrets.get("GROQ_API_KEY"):
        st.error("Falta API Key")
    else:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
        # PROMPT DE ALTA PRECISIÓN
        prompt_medico = f"""
        Actúa como un cardiólogo experto. Redacta un informe técnico basado estrictamente en:
        - DDVI: {st.session_state.datos['dv']} mm
        - Septum (SIV): {st.session_state.datos['si']} mm
        - FEy: {st.session_state.datos['fy']}%
        - Raíz Aórtica: {st.session_state.datos['dr']} mm
        - Aurícula Izquierda: {st.session_state.datos['ai']} mm

        Estructura: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VALVULAS Y DOPPLER, IV. CONCLUSIÓN.
        Reglas:
        1. Si un valor es '--', describe que no se visualizó correctamente.
        2. Mantén un tono profesional y conciso.
        3. No inventes datos de otros órganos.
        """
        
        try:
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_medico}],
                temperature=0.1 # Baja temperatura = Menos inventiva
            )
            st.session_state.informe_generado = res.choices[0].message.content
            st.info(st.session_state.informe_generado)
        except Exception as e:
            st.error(f"Error en Groq: {e}")

# (La función de generar_word se mantiene igual pero usando st.session_state.datos)
