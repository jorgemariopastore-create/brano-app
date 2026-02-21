
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# 1. CONFIGURACIÓN DE SEGURIDAD
st.set_page_config(page_title="Cardio-Report IA", layout="centered")

try:
    # Intenta leer desde secrets
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("⚠️ Error de Configuración: No se encontró la clave API en Secrets.")
    st.stop()

def extraer_datos_limpios(file):
    df = None
    for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
        try:
            file.seek(0)
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, sep=None, engine='python', encoding=encoding, header=None)
            else:
                df = pd.read_excel(file, header=None)
            break
        except:
            continue
    
    if df is None or df.empty:
        return {}

    datos = {}
    for _, row in df.iterrows():
        k = str(row[0]).strip() if pd.notna(row[0]) else ""
        v = str(row[1]).strip() if pd.notna(row[1]) else ""
        if k and k.lower() != "nan" and len(k) > 1:
            datos[k] = v
    return datos

def redactar_con_ia(datos_dict):
    if not datos_dict:
        return "Datos no detectados en el archivo."

    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items() if v])

    prompt = f"""
    Actúa como un cardiólogo. Redacta los hallazgos técnicos de un ecocardiograma.
    DATOS:
    {datos_texto}
    REGLAS: Redacción técnica, formal, SIN recomendaciones ni tratamientos. Sé breve.
    """
    
    try:
        # MODELO ACTUALIZADO A 3.1 (El que funciona hoy)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error en redacción (IA): {str(e)}"

def generar_word(datos, texto_ia, pdf_file):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    paciente = datos.get('Paciente', 'BALEIRON MANUEL')
    fecha = datos.get('Fecha de estudio', '27/12/2025')

    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {paciente}\n").bold = True
    p.add_run(f"FECHA: {fecha}").bold = True

    doc.add_heading('Descripción Técnica', level=1)
    doc.add_paragraph(texto_ia)

    # Anexo de Imágenes 4x2
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    
    try:
        pdf_file.seek(0)
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        imgs = []
        for page in pdf_doc:
            for img_info in page.get_images(full=True):
                imgs.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

        if imgs:
            table = doc.add_table(rows=4, cols=2)
            for i in range(min(len(imgs), 8)):
                row, col = i // 2, i % 2
                cell = table.rows[row].cells[col]
                run = cell.paragraphs[0].add_run()
                run.add_picture(imgs[i], width=Inches(3.0))
    except:
        doc.add_paragraph("No se pudieron extraer imágenes del PDF.")

    # FIRMA
    ruta_f = "firma_doctor.png"
    if os.path.exists(ruta_f):
