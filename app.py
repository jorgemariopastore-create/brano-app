
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# 1. CONEXIÓN CON GROQ (Secrets)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró 'GROQ_API_KEY' en los Secrets.")
    st.stop()

def extraer_datos(file):
    """Lee Excel o CSV y extrae los datos del ecógrafo"""
    if file.name.endswith('.csv'):
        df = pd.read_csv(file, header=None)
    else:
        df = pd.read_excel(file, header=None)
    
    datos = {}
    for _, row in df.iterrows():
        key = str(row[0]).strip()
        val = str(row[1]).strip() if pd.notna(row[1]) else ""
        if key and key != "nan":
            datos[key] = val
    return datos

def redactar_con_ia(datos_dict):
    """Envía los datos a Groq para redacción médica pura"""
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Actúa como un cardiólogo. Redacta los hallazgos de un ecocardiograma y doppler.
    DATOS:
    {datos_texto}
    
    REGLAS:
    - Redacción técnica y formal.
    - NO incluyas recomendaciones ni tratamientos.
    - NO inventes datos.
    - Sé directo. Si hay 'Observaciones' en los datos, inclúyelas.
    """
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return completion.choices[0].message.content

def generar_word(datos, texto_ia, pdf_file):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{datos.get('Paciente', 'N/A')}\n")
    p.add_run("FECHA: ").bold = True
    p.add_run(f"{datos.get('Fecha de estudio', 'N/A')}")

    # Cuerpo redactado por IA
    doc.add_heading('Descripción Técnica', level=1)
    doc.add_paragraph(texto_ia)

    # Anexo de Imágenes (4 filas x 2 columnas)
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    
    pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    imgs = []
    for page in pdf_doc:
        for img_info in page.get_images(full=True):
            imgs.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

    if imgs:
        table = doc.add_table(rows=4, cols=2)
        for i in range(min(len(imgs), 8)):
            row, col = i // 2, i % 2
            paragraph = table.rows[row].cells[col].paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            run.add_picture(imgs[i], width=Inches(3.0))

    # FIRMA DIGITAL (firma_doctor.png)
    ruta_firma = "firma_doctor.png"
    if os.path.exists(ruta_firma):
        doc.add_paragraph("\n")
        f_para = doc.add_paragraph()
        f_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_para.add_run().add_picture(ruta_firma, width=Inches(1.8))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ ---
st.title("Cardio-Report IA 🩺")

c1, c2 = st.columns(2)
with c1:
    f_excel = st.file_uploader("Subir Cálculos (Excel/CSV)", type=["csv", "xlsx"])
with c2:
    f_pdf = st.file_uploader("Subir PDF (Imágenes)", type=["pdf"])

if f_excel and f_pdf:
    if st.button("Generar Informe"):
        with st.spinner("Procesando..."):
            datos_ext = extraer_datos(f_excel)
            texto_ia = redactar_con_ia(datos_ext)
            docx_file = generar_word(datos_ext, texto_ia, f_pdf)
            
            st.success("¡Informe listo!")
            st.download_button("📥 Descargar Word", docx_file, 
                               f"Informe_{datos_ext.get('Paciente','Cardio')}.docx")
