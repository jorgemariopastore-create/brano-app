
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt  # <--- Esta es la que causaba el error si no estaba en requirements.txt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

col1, col2 = st.columns(2)
with col1:
    archivo_datos = st.file_uploader("1. Reporte de Datos (TXT o DOCX)", type=["txt", "docx"])
with col2:
    archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            # Leer el archivo de datos
            if archivo_datos.name.endswith('.docx'):
                texto_crudo = docx2txt.process(archivo_datos)
            else:
                texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")
            
            client = Groq(api_key=api_key)
            
            # PROMPT MEJORADO PARA DATOS GENERALES
            prompt = f"""
            ERES EL DR. PASTORE. REDACTA UN INFORME MÉDICO.
            
            INSTRUCCIÓN CRÍTICA PARA DATOS GENERALES:
            Busca en la sección [PATINET INFO] o al inicio del texto:
            - PatientName (Nombre)
            - Weight (Peso)
            - Height (Altura)
            - Age (Edad)
            
            INSTRUCCIÓN PARA MEDICIONES:
            - Extrae DDVI, DSVI, Septum, Pared de las secciones de medición.
            - Extrae FEy (EF) y FA (FS).
            
            FORMATO DE SALIDA:
            DATOS DEL PACIENTE:
            (Escribe aquí Nombre, Edad, Peso, Altura y BSA detectados)
            
            I. EVALUACIÓN ANATÓMICA:
            II. FUNCIÓN VENTRICULAR:
            III. EVALUACIÓN HEMODINÁMICA:
            IV. CONCLUSIÓN:
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO PARA ANALIZAR:
            {texto_crudo[:15000]}
            """
            
            # ... (resto del código de envío a Groq y generación de Word)
