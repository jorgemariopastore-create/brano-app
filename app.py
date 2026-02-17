
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de Interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_final(texto_informe, pdf_stream):
    doc = Document()
    
    # Estilo base: Arial 11
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # Título centrado
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Agregar el texto del informe JUSTIFICADO
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # <--- TEXTO JUSTIFICADO
        p.add_run(linea)

    # Procesar imágenes directamente
    doc.add_page_break()
    anexo = doc.add_paragraph()
    anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anexo.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
    imagenes = []
    for pagina in pdf_document:
        for img in pagina.get_images(full=True):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            imagenes.append(base_image["image"])
    
    # GRILLA DE IMÁGENES DE A 2 (Como pediste: 4 filas de 2 o las que correspondan)
    num_cols = 2 # <--- CAMBIADO A 2 COLUMNAS
    num_rows = (len(imagenes) + num_cols - 1) // num_cols
    tabla = doc.add_table(rows=num_rows, cols=num_cols)
    
    for idx, img_data in enumerate(imagenes):
        row = idx // num_cols
