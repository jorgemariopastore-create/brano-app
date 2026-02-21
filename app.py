
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
        # Limpiar celdas y convertir a texto
        k = str(row[0]).strip() if pd.notna(row[0]) else ""
        v = str(row[1]).strip() if pd.notna(row[1]) else ""
        
        # Solo agregar si la clave tiene contenido real
        if k and k.lower() != "nan" and len(k) > 1:
            datos[k] = v
            
    return datos

def redactar_con_ia(datos_dict):
    # VALIDACIÓN CRÍTICA: Si no hay datos, no llamar a Groq
    if not datos_dict:
        return "No se detectaron datos numéricos suficientes en el archivo para redactar el informe automáticamente."

    # Filtrar solo datos con valores para no enviar basura a la IA
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items() if v and v.lower() != "nan"])

    prompt = f"""
    Actúa como un cardiólogo. Redacta los hallazgos técnicos de un ecocardiograma.
    DATOS:
    {datos_texto}
    
    REGLAS:
    - Redacción técnica formal.
    - SIN recomendaciones ni tratamientos.
    - Si el médico escribió observaciones, inclúyelas.
    - Sé breve.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", # Cambiamos a 8b que es más estable y rápido para textos cortos
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error en Groq: {str(e)}"

def generar_word(datos, texto_ia, pdf_file):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Intentar sacar nombre del paciente de los datos
    nombre_p = datos.get('Paciente', 'BALEIRON MANUEL')
    fecha_p = datos.get('Fecha de estudio', '27/12/2025')

    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {nombre_p}\n").bold = True
    p.add_run(f"FECHA: {fecha_p}").bold = True

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
        doc.add_paragraph("No se pudieron cargar imágenes.")

    # FIRMA
    ruta_f = "firma_doctor.png"
    if os.path.exists(ruta_f):
        f_p = doc.add_paragraph()
        f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_p.add_run().add_picture(ruta_f, width=Inches(1.8))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ STREAMLIT ---
st.title("Cardio-Report IA 🩺")

c1, c2 = st.columns(2)
with c1:
    f_excel = st.file_uploader("Excel/CSV", type=["csv", "xlsx", "xls"])
with c2:
    f_pdf = st.file_uploader("PDF", type=["pdf"])

if f_excel and f_pdf:
    if st.button("Generar Informe Profesional"):
        datos_ext = extraer_datos_limpios(f_excel)
        
        # Si el diccionario está vacío, avisar antes de llamar a la IA
        if not datos_ext:
            st.warning("El archivo Excel parece estar vacío o en un formato no reconocido. Revisa las columnas.")
        else:
            with st.spinner("Redactando informe con Groq..."):
                texto_ia = redactar_con_ia(datos_ext)
                docx = generar_word(datos_ext, texto_ia, f_pdf)
                st.success("Informe listo.")
                st.download_button("Descargar Word", docx, "Informe.docx")
