
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de la interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo (Alicia, Manuel, etc.)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Procesamiento de texto con limpieza de "basura de IA"
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or any(x in linea.lower() for x in ["lo siento", "no puedo", "falta de información", "espero que"]):
            continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Formato de negritas para secciones
        if any(h in linea.upper() for h in ["DATOS DEL PACIENTE", "I.", "II.", "III.", "IV.", "FIRMA:"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Anexo de Imágenes
    doc.add_page_break()
    a = doc.add_paragraph()
    a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    a.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
    imgs = []
    for page in pdf_file:
        for img in page.get_images(full=True):
            imgs.append(pdf_file.extract_image(img[0])["image"])
    
    if imgs:
        tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
        for i, img_data in enumerate(imgs):
            run = tabla.cell(i//2, i%2).paragraphs[0].add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
    pdf_file.close()
    
    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

if archivo and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Analizando datos específicos del estudio..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                # Extraemos texto con orden lógico para capturar Altura/Peso
                texto_pdf = ""
                for pagina in pdf:
                    texto_pdf += pagina.get_text("text", sort=True) + "\n"
                pdf.close()

                client = Groq(api_key=api_key)
                
                # PROMPT SIN DATOS FIJOS (Dinámico y Seguro)
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES TRASCRIBIR LOS DATOS DEL PDF AL INFORME.
