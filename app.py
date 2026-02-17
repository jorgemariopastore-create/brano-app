
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; font-family: Arial; color: black; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - SonoScape E3")

def generar_word_estable(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    lineas = texto.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
            
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))

    if imagenes:
        doc.add_page_break()
        a = doc.add_paragraph
