
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# 1. Configuración de API Key desde Secrets
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None

def extraer_dato_universal(texto, clave):
    """
    Busca datos tanto en formato tabla CSV ("DDVI","40") 
    como en formato texto estándar (DDVI: 40).
    """
    # Formato tabla (comillas y comas como en tu equipo)
    patron_tabla = rf"\"{clave}\"\s*,\s*\"([\d.,]+)\""
    match_t = re.search(patron_tabla, texto, re.IGNORECASE)
    if match_t:
        return match_t.group(1).replace(',', '.')
    
    # Formato texto estándar
    patron_txt = rf"{clave}.*?[:=\s]\s*([\d.,]+)"
    match_s = re.search(patron_txt, texto, re.IGNORECASE)
    if match_s:
        return match_s.group(1).replace(',', '.')
    return ""

st.set_page_config(page_title="CardioReport Master", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

# Inicializar sesión para persistencia
if "datos" not in st.session_state:
    st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}

with st.sidebar:
    st.header("1. Carga de Archivos")
    # Restauramos ambos cargadores
    arc_txt = st.file_uploader("Archivo TXT (Datos crudos)", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF (Nombre/Referencia)", type=["pdf"])
    
    if st.button("🔄 Nuevo Paciente / Limpiar"):
        st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}
        st.rerun()

# 2. Procesamiento Inteligente
if arc_txt and arc_pdf and GROQ_KEY:
    # Solo procesamos si el estado está vacío (evita borrar lo que el médico escribe)
    if st.session_state.datos["pac"] == "":
        with st.spinner("Fusionando datos de TXT y PDF..."):
            try:
                # Leer TXT
                t_raw = arc_txt.read().decode("latin-1", errors="ignore")
                
                # Leer PDF
                p_bytes = arc_pdf.read()
                texto_pdf = ""
                with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                    texto_pdf = "".join([pag.get_text() for pag in doc])
                
                # Unimos ambos textos para la búsqueda
                texto_total = t_raw + "\n" + texto_pdf

                # Extraer Paciente (del PDF preferentemente)
                n_m = re.search(r"(?:Paciente|Nombre pac\.|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
                
                # Extraer Valores Técnicos
                ddvi = extraer_dato_universal(texto_total, "DDVI")
                siv = extraer_dato_universal(texto_total, "DDSIV")
                
                # Lógica de FEy: Buscar FEy, si no está, buscar EF, si no buscar FA
                fey = extraer_dato_universal(texto_total, "FE") or extraer_dato_universal(texto_total, "EF")
                if not fey:
                    fa = extraer_dato_universal(texto_total, "FA")
                    if fa: # Si Alicia tiene FA 38%, calculamos FEy ~65-67%
                        fey = str(round(float(fa) * 1.73))

                # Guardar en session_state
                st.session_state.datos = {
                    "pac": n_m.group(1).strip().upper() if n_m else "DESCONOCIDO",
                    "dv": ddvi,
                    "si": siv,
                    "fy": fey
                }
            except Exception as e:
                st.error(f"Error al procesar: {e}")

# 3. Interfaz de Validación (Carga los datos del session_state)
if st.session_state.datos["pac"] != "":
    with st.form("validador_final"):
        st.subheader("🔍 Validar Datos Extraídos")
        c1, c2, c3, c4 = st.columns(4)
        
        pac_edit = c1.text_input("Paciente", st.session_state.datos["pac"])
        fey_edit = c2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi_edit = c3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv_edit = c4.text_input("SIV mm", st.session_state.datos["si"])
        
        submit = st.form_submit_button("🚀 GENERAR INFORME")

    if submit:
        # Actualizamos el estado con lo que el médico corrigió
        st.session_state.datos.update({"pac": pac_edit, "fy": fey_edit, "dv": ddvi_edit, "si": siv_edit})
        
        if not fey_edit or not ddvi_edit:
            st.warning("⚠️ Complete los datos manualmente si el sistema no los detectó.")
        else:
            client = Groq(api_key=GROQ_KEY)
            prompt = f"""
            Actúa como el Dr. Francisco Pastore. Redacta el informe:
            Paciente: {pac_edit}. 
            Datos: DDVI {ddvi_edit}mm, SIV {siv_edit}mm, FEy {fey_edit}%.
            
            ESTILO:
            - Técnico, conciso, formal.
            - Si FEy > 55%: 'Función sistólica global conservada'.
            - Si SIV >= 11mm: 'Remodelado concéntrico'.
            """
            with st.spinner("Redactando..."):
                res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
                st.markdown("---")
                st.info(res.choices[0].message.content)
                st.markdown("**Dr. Francisco A. Pastore**")

elif not GROQ_KEY:
    st.error("Configura la GROQ_API_KEY en Secrets.")
else:
    st.info("👋 Por favor, carga el TXT y el PDF para comenzar.")
