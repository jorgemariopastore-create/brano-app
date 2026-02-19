
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF para extraer imágenes
from docx import Document
from docx.shared import Inches
import io

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro + Imágenes", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# --- 2. MOTOR DE EXTRACCIÓN DE IMÁGENES ---
def extraer_imagenes_del_pdf(archivo_pdf):
    imagenes = []
    doc = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            imagenes.append(io.BytesIO(image_bytes))
    return imagenes

# --- 3. FORMULARIO MANUAL (ESTABLE) ---
with st.sidebar:
    st.header("Estudio Original")
    archivo_pdf = st.file_uploader("Subir el PDF del ecógrafo para extraer imágenes", type=["pdf"])

with st.form("generador_word"):
    st.subheader("Datos para el Informe")
    c1, c2 = st.columns([3, 1])
    pac = c1.text_input("Nombre del Paciente", value="ALBORNOZ ALICIA")
    fec = c2.text_input("Fecha", value="13/02/2026")
    
    st.markdown("---")
    c3, c4, c5, c6, c7 = st.columns(5)
    ddvi = c3.text_input("DDVI", value="40")
    dsvi = c4.text_input("DSVI", value="25")
    siv = c5.text_input("SIV", value="11")
    pp = c6.text_input("PP", value="10")
    fey = c7.text_input("FEy %", value="67")
    
    if st.form_submit_button("🚀 GENERAR WORD CON IMÁGENES"):
        if archivo_pdf:
            # 1. Redactamos el texto con IA (Groq)
            # ... (Lógica de prompt del Dr. Pastore que ya aprobamos) ...
            texto_ia = "HALLAZGOS: ... CONCLUSIÓN: ..." # Simulación del resultado
            
            # 2. Creamos el documento Word
            doc_word = Document()
            doc_word.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
            doc_word.add_paragraph(f"Paciente: {pac}   |   Fecha: {fec}")
            
            # Agregamos el texto profesional
            p = doc_word.add_paragraph(texto_ia)
            p.alignment = 3 # Justificado
            
            # 3. Insertamos las imágenes del ecógrafo
            st.info("Extrayendo imágenes del PDF original...")
            doc_word.add_page_break()
            doc_word.add_heading('ANEXO DE IMÁGENES', 1)
            
            imgs = extraer_imagenes_del_pdf(archivo_pdf)
            for img_data in imgs:
                doc_word.add_picture(img_data, width=Inches(3.0)) # Dos imágenes por fila aprox.
            
            # 4. Descarga
            bio = io.BytesIO()
            doc_word.save(bio)
            st.download_button(
                label="⬇️ DESCARGAR INFORME COMPLETO (WORD)",
                data=bio.getvalue(),
                file_name=f"Informe_{pac}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.error("Debe subir el PDF original para poder extraer las imágenes.")
