
import streamlit as st
from groq import Groq
import fitz # PyMuPDF
import re

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# Función Senior para limpiar TODO
def reset_completo():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- LÓGICA DE EXTRACCIÓN REFORZADA ---
def extraer_datos_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    texto = " ".join([pag.get_text() for pag in doc])
    t = re.sub(r'\s+', ' ', texto) # Limpieza de espacios
    
    # Buscamos datos con patrones más agresivos
    d = {"pac": "", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
    
    # Nombre: Busca después de "Paciente:" hasta encontrar una fecha o salto
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?=\s*(Fecha|Edad|DNI|$))", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    # Métricas Técnicas
    patrones = {
        "ddvi": r"DDVI\s*(\d+)", "dsvi": r"DSVI\s*(\d+)", 
        "siv": r"(?:SIV|DDSIV)\s*(\d+)", "pp": r"(?:PP|DDPP)\s*(\d+)",
        "fey": r"(?:FEy|FA|eyeccion)\s*(\d+)"
    }
    for k, v in patrones.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
    return d

# --- SIDEBAR ---
with st.sidebar:
    st.header("Control de Archivos")
    archivo = st.file_uploader("Subir PDF del Estudio", type=["pdf"])
    if st.button("🗑️ LIMPIAR MEMORIA (Reset)"):
        reset_completo()

# --- CUERPO PRINCIPAL ---
if archivo:
    # Creamos un ID único para el archivo
    file_id = f"{archivo.name}_{archivo.size}"
    
    # Si el archivo cambió o no hay datos, extraemos
    if st.session_state.get("last_id") != file_id:
        with st.spinner("Analizando nuevo paciente..."):
            st.session_state.datos = extraer_datos_pdf(archivo.read())
            st.session_state.last_id = file_id
            st.rerun()

    # Si tenemos datos, mostramos la validación
    if "datos" in st.session_state:
        d = st.session_state.datos
        with st.form("validador_senior"):
            st.subheader(f"Validación de Datos: {d['pac'] if d['pac'] else 'Nuevo Paciente'}")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            pac = c1.text_input("Paciente", value=d["pac"])
            fec = c2.text_input("Fecha", value=d["fec"])
            edad = c3.text_input("Edad", value=d["edad"])
            
            st.markdown("### Métricas Técnicas")
            c4, c5, c6, c7, c8 = st.columns(5)
            # Aquí el médico puede corregir si el PDF leyó mal
            ddvi = c4.text_input("DDVI", value=d["ddvi"])
            dsvi = c5.text_input("DSVI", value=d["dsvi"])
            siv = c6.text_input("SIV", value=d["siv"])
            pp = c7.text_input("PP", value=d["pp"])
            fey = c8.text_input("FEy %", value=d["fey"])
            
            if st.form_submit_button("🚀 GENERAR INFORME"):
                st.success("Informe en proceso...")
else:
    st.info("👋 Dr. Pastore: Por favor, cargue un archivo PDF para comenzar.")
