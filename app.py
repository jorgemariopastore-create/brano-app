
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# 1. Función de extracción robusta
def extraer_dato(texto, clave):
    # Soporta: "LVIDd: 50", "LVIDd=50", "LVIDd  50", "LVIDd : 50.5"
    patron = rf"{clave}\s*[:=\s]\s*([\d.,]+)"
    match = re.search(patron, texto, re.IGNORECASE)
    if match:
        return match.group(1).replace(',', '.') # Normaliza decimales
    return ""

st.set_page_config(page_title="CardioReport", layout="wide")
st.title("🏥 Asistente de Ecocardiogramas")

# Inicializar session_state para que los datos no se borren
if "datos" not in st.session_state:
    st.session_state.datos = None

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_txt = st.file_uploader("Archivo TXT del Equipo", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF (Imágenes/Nombre)", type=["pdf"])
    api_key = st.text_input("Groq API Key", type="password")
    
    if st.button("Limpiar Sesión / Nuevo Paciente"):
        st.session_state.datos = None
        st.rerun()

# 2. Lógica de Procesamiento (Solo ocurre una vez al cargar archivos)
if arc_txt and arc_pdf and api_key:
    if st.session_state.datos is None:
        with st.spinner("Extrayendo datos..."):
            t_raw = arc_txt.read().decode("latin-1", errors="ignore")
            p_bytes = arc_pdf.read()
            
            # Valores por defecto
            d = {"pac": "DESCONOCIDO", "fy": "", "dv": "", "si": ""}
            
            # Extraer Nombre del PDF
            try:
                with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                    texto_pdf = "".join([pag.get_text() for pag in doc])
                    n_m = re.search(r"(?:Nombre|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
                    if n_m: d["pac"] = n_m.group(1).strip().upper()
            except Exception as e:
                st.error(f"Error en PDF: {e}")

            # Extraer valores numéricos del TXT
            d["dv"] = extraer_dato(t_raw, "LVIDd")
            d["si"] = extraer_dato(t_raw, "IVSd")
            d["fy"] = extraer_dato(t_raw, "EF")
            
            st.session_state.datos = d

    # 3. Formulario de Edición (Usa los datos de session_state)
    if st.session_state.datos:
        with st.form("editor_medico"):
            st.subheader("🔍 Validar y Editar Datos")
            col1, col2 = st.columns(2)
            
            # Los inputs cargan el valor inicial del session_state
            paciente = col1.text_input("Nombre del Paciente", st.session_state.datos["pac"])
            fey = col1.text_input("FEy % (Función Sistólica)", st.session_state.datos["fy"])
            ddvi = col2.text_input("DDVI mm (Diámetro)", st.session_state.datos["dv"])
            siv = col2.text_input("SIV mm (Septum)", st.session_state.datos["si"])
            
            btn_confirmar = st.form_submit_button("🚀 GENERAR INFORME IA")

        if btn_confirmar:
            # Actualizamos el estado con lo que el usuario editó
            st.session_state.datos.update({"pac": paciente, "fy": fey, "dv": ddvi, "si": siv})
            
            try:
                client = Groq(api_key=api_key)
                prompt = (f"Actúa como cardiólogo. Redacta un informe profesional basado en: "
                         f"Paciente {paciente}. DDVI: {ddvi}mm, SIV: {siv}mm, FEy: {fey}%. "
                         f"Indica si los valores son normales o hay alteraciones.")
                
                with st.spinner("La IA está redactando..."):
                    res = client.chat.completions.create(
                        model='llama-3.3-70b-versatile', 
                        messages=[{'role':'user','content':prompt}]
                    )
                
                st.success("✅ Informe Generado")
                st.markdown("---")
                st.write(res.choices[0].message.content)
            except Exception as e:
                st.error(f"Error con Groq: {e}")
else:
    st.info("👋 Por favor, carga ambos archivos y la API Key en la barra lateral para comenzar.")
