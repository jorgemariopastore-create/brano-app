
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# 1. Configuración de API Key
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = None

def extraer_dato_especifico(texto, clave):
    """
    Extrae datos de formatos tipo tabla CSV: "DDVI","40","mm"
    """
    # Esta regex busca la clave entre comillas, salta la coma, y captura el número entre comillas
    patron = rf"\"{clave}\"\s*,\s*\"([\d.,]+)\""
    match = re.search(patron, texto, re.IGNORECASE)
    if match:
        return match.group(1).replace(',', '.')
    
    # Si no lo encuentra con comillas, busca formato estándar
    patron_simple = rf"{clave}.*?[:=\s]\s*([\d.,]+)"
    match_s = re.search(patron_simple, texto, re.IGNORECASE)
    if match_s:
        return match_s.group(1).replace(',', '.')
    return ""

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

if "datos" not in st.session_state:
    st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_pdf = st.file_uploader("Subir Informe PDF", type=["pdf"])
    if st.button("🔄 Nuevo Paciente"):
        st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}
        st.rerun()

if arc_pdf and GROQ_KEY:
    if st.session_state.datos["pac"] == "":
        with st.spinner("Escaneando PDF..."):
            try:
                doc = fitz.open(stream=arc_pdf.read(), filetype="pdf")
                texto_total = "".join([pag.get_text() for pag in doc])
                
                # Extraer Paciente
                n_m = re.search(r"Paciente:\s*([^<\r\n]*)", texto_total, re.I)
                
                # Extraer Valores Críticos usando etiquetas exactas de tu equipo
                ddvi = extraer_dato_especifico(texto_total, "DDVI")
                siv = extraer_dato_especifico(texto_total, "DDSIV")
                
                # Lógica de FEy: Si no hay FE específica, usamos FA (Fracción de Acortamiento)
                # En el reporte de Alicia, FA es 38, lo que equivale a una FEy de ~67%
                fey = extraer_dato_especifico(texto_total, "FE") or extraer_dato_especifico(texto_total, "EF")
                fa = extraer_dato_especifico(texto_total, "FA")
                
                if not fey and fa:
                    # Estimación simple si solo hay Fracción de Acortamiento
                    fey = str(round(float(fa) * 1.7)) 

                st.session_state.datos = {
                    "pac": n_m.group(1).strip().upper() if n_m else "DESCONOCIDO",
                    "dv": ddvi,
                    "si": siv,
                    "fy": fey
                }
            except Exception as e:
                st.error(f"Error técnico: {e}")

    # FORMULARIO DE EDICIÓN
    with st.form("editor"):
        st.subheader("🔍 Datos Detectados")
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", st.session_state.datos["pac"])
        fey = c2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi = c3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv = c4.text_input("SIV mm", st.session_state.datos["si"])
        
        generar = st.form_submit_button("🚀 GENERAR INFORME")

    if generar:
        if not fey or not ddvi:
            st.error("⚠️ Error: El sistema no detectó automáticamente la FEy o el DDVI. Por favor, ingréselos manualmente antes de continuar.")
        else:
            client = Groq(api_key=GROQ_KEY)
            prompt = f"""
            Actúa como el Dr. Francisco Pastore. Redacta las conclusiones de un ecocardiograma.
            Paciente: {pac}. Datos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%.
            
            Instrucciones:
            - Si FEy > 55%: 'Función sistólica global conservada'.
            - Si SIV >= 11mm: 'Remodelado concéntrico del VI'.
            - Usa lenguaje médico formal y directo.
            """
            with st.spinner("Redactando..."):
                res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
                st.success("Informe Generado")
                st.info(res.choices[0].message.content)
                st.markdown("**Dr. Francisco A. Pastore**")
