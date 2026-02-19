
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# Intentar cargar la API KEY desde Secrets
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None

def extraer_dato_robusto(texto, claves_posibles):
    """Busca entre varias etiquetas posibles para un mismo dato médico."""
    for clave in claves_posibles:
        # Busca la clave seguida de espacios/signos y captura el número (soporta 40, 40.5, 40,5)
        patron = rf"{clave}\s*[:=\s]*\s*([\d.,]+)"
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '.')
    return ""

st.set_page_config(page_title="CardioReport Elite", layout="wide")

# --- LÓGICA DE ESTILO MÉDICO ---
ESTILO_MEDICO = """
Actúa como un cardiólogo experto. Usa un tono formal, conciso y técnico. 
Sigue este estilo de redacción:
1. Diámetros y función sistólica (mencionar si está conservada).
2. Motilidad y Fracción de Eyección (FEy).
3. Descripción de aurículas y ventrículo derecho.
4. Hallazgos de Doppler (patrón de llenado, relación E/A).
"""

if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("📂 Carga de Estudios")
    arc_pdf = st.file_uploader("Subir informe PDF (Alicia Albornoz)", type=["pdf"])
    if st.button("🔄 Limpiar y Nuevo Paciente"):
        st.session_state.datos = None
        st.rerun()

if arc_pdf and GROQ_KEY:
    if st.session_state.datos is None:
        with st.spinner("Analizando documento médico..."):
            p_bytes = arc_pdf.read()
            d = {"pac": "NO ENCONTRADO", "fy": "", "dv": "", "si": ""}
            
            try:
                with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                    texto_completo = "".join([pag.get_text() for pag in doc])
                
                # 1. Extraer Paciente
                n_m = re.search(r"(?:Paciente|Nombre pac\.)\s*[:=-]?\s*([^<\r\n]*)", texto_completo, re.I)
                if n_m: d["pac"] = n_m.group(1).strip().upper()

                # 2. Extraer DDVI (Diámetro Diastólico VI)
                d["dv"] = extraer_dato_robusto(texto_completo, ["DDVI", "Diám. Diastólico"])
                
                # 3. Extraer SIV (Septum Interventricular)
                d["si"] = extraer_dato_robusto(texto_completo, ["DDSIV", "SIV", "Septum"])
                
                # 4. Extraer FEy (Fracción de Eyección)
                # En tu PDF aparece como "FE(A4C)" o "Fracción de eyección del VI"
                d["fy"] = extraer_dato_robusto(texto_completo, ["Fracción de eyección del VI", "EF\(A4C\)", "FEVI", "FA"])
                
                st.session_state.datos = d
            except Exception as e:
                st.error(f"Error al leer el PDF: {e}")

    # --- INTERFAZ DE EDICIÓN ---
    if st.session_state.datos:
        st.subheader(f"👤 Paciente: {st.session_state.datos['pac']}")
        
        with st.form("editor"):
            c1, c2, c3 = st.columns(3)
            paciente = c1.text_input("Nombre", st.session_state.datos["pac"])
            fey = c1.text_input("FEy (%)", st.session_state.datos["fy"])
            ddvi = c2.text_input("DDVI (mm)", st.session_state.datos["dv"])
            siv = c3.text_input("SIV (mm)", st.session_state.datos["si"])
            
            enviar = st.form_submit_button("📝 GENERAR INFORME CON ESTILO MÉDICO")

        if enviar:
            client = Groq(api_key=GROQ_KEY)
            # Prompt optimizado con el estilo del Dr. Pastore
            prompt = f"""
            {ESTILO_MEDICO}
            Genera un informe para el paciente {paciente} con estos datos:
            - DDVI: {ddvi} mm
            - SIV: {siv} mm
            - FEy: {fey} %
            
            Si el DDVI es ~40mm y SIV ~11mm, menciona 'remodelado concéntrico'. 
            Si la FEy es >55%, menciona 'función sistólica conservada'.
            """
            
            with st.spinner("Redactando..."):
                res = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[{'role':'user', 'content': prompt}]
                )
                st.markdown("---")
                st.markdown("### 📄 Borrador del Informe Médico")
                st.write(res.choices[0].message.content)

elif not GROQ_KEY:
    st.error("🔑 Error: No se encontró la GROQ_API_KEY en los Secrets.")
else:
    st.info("A la espera de un archivo PDF para procesar.")
