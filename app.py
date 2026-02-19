
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
import hashlib
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN DE NÚCLEO ---
st.set_page_config(page_title="CardioReport Senior", layout="wide")

def get_file_hash(file):
    """Genera una huella única para el archivo para detectar cambios reales."""
    if file is None: return None
    return hashlib.md5(file.getvalue()).hexdigest()

def extraer_datos_frescos(file):
    """Lógica de extracción sin valores persistentes."""
    doc = fitz.open(stream=file.getvalue(), filetype="pdf")
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    
    # Limpieza de ruido del ecógrafo (SonoScape/Mindray)
    t = re.sub(r'[\"\'\r\t]', '', texto)
    t = re.sub(r'\n+', ' ', t)
    
    # Diccionario base vacío (Garantiza que no traiga datos de Alicia si no existen)
    d = {
        "pac": "NO DETECTADO", "fec": "", "edad": "", 
        "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": "", "ai": ""
    }
    
    # Regex de precisión
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|DNI|$)", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    m_fec = re.search(r"Fecha(?:\s*de\s*estudio)?:\s*(\d{2}/\d{2}/\d{4})", t, re.I)
    if m_fec: d["fec"] = m_fec.group(1)

    patterns = {
        "ddvi": r"DDVI\s+(\d+)", "dsvi": r"DSVI\s+(\d+)", 
        "siv": r"(?:SIV|DDSIV)\s+(\d+)", "pp": r"(?:PP|DDPP)\s+(\d+)",
        "fey": r"(?:FEy|eyección|FA)\s+(\d+)", "ai": r"(?:AI|DDAI)\s+(\d+)"
    }
    
    for k, v in patterns.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
        
    return d

# --- 2. GESTIÓN DE SESIÓN (EL "RESET" SENIOR) ---
archivo_subido = st.sidebar.file_uploader("Subir PDF del Estudio", type=["pdf"])

if archivo_subido:
    current_hash = get_file_hash(archivo_subido)
    
    # Si el hash cambió, significa que es OTRO archivo: Borramos TODO
    if st.session_state.get("last_hash") != current_hash:
        st.session_state.last_hash = current_hash
        st.session_state.datos = extraer_datos_frescos(archivo_subido)
        st.session_state.informe_ia = ""
        st.session_state.word_ready = False
        st.rerun() # Forzamos recarga limpia

    d = st.session_state.datos

    # --- 3. INTERFAZ DE VALIDACIÓN ---
    # Usamos el hash en la clave del formulario para forzar refresco visual
    with st.form(key=f"form_{st.session_state.last_hash}"):
        st.subheader(f"Validación Médica: {d['pac']}")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        pac = c1.text_input("Paciente", value=d["pac"])
        fec = c2.text_input("Fecha", value=d["fec"])
        edad = c3.text_input("Edad", value=d["edad"])
        
        c4, c5 = st.columns(2)
        peso = c4.text_input("Peso (kg)", value="")
        alt = c5.text_input("Altura (cm)", value="")
        
        st.write("---")
        c6, c7, c8, c9, c10 = st.columns(5)
        ddvi = c6.text_input("DDVI", value=d["ddvi"])
        dsvi = c7.text_input("DSVI", value=d["dsvi"])
        siv = c8.text_input("SIV", value=d["siv"])
        pp = c9.text_input("PP", value=d["pp"])
        fey = c10.text_input("FEy %", value=d["fey"])
        
        submit = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

    if submit:
        # Aquí va la llamada a Groq y la creación del Word (Arial 12, Justificado)
        # Se asegura que no repita el nombre y sea conciso.
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        prompt = f"""Actúa como el Dr. Pastore. Redacta el cuerpo de un informe de ecocardiograma.
        DATOS: DDVI {ddvi}mm, DSVI {dsvi}mm, SIV {siv}mm, PP {pp}mm, FEy {fey}%.
        ESTILO: Técnico, seco, letra Arial 12, texto JUSTIFICADO. 
        ESTRUCTURA: HALLAZGOS (motilidad y diámetros), VALVULAS, CONCLUSIÓN técnica (una oración).
        REGLA: Prohibido repetir el nombre del paciente en el cuerpo."""
        
        with st.spinner("Redactando informe..."):
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.informe_ia = res.choices[0].message.content
            st.session_state.word_ready = True

    # --- 4. SALIDA ---
    if st.session_state.get("informe_ia"):
        st.markdown("---")
        st.markdown(f"### Informe del Dr. Pastore\n\n{st.session_state.informe_ia}")
        # Aquí el botón de descarga del Word...
