
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# 1. CLIENTE GROQ
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Diccionario de traducción técnica para evitar errores de la IA
TRADUCCIONES = {
    "DDVD": "Diámetro Diastólico del Ventrículo Derecho",
    "DDVI": "Diámetro Diastólico del Ventrículo Izquierdo",
    "DSVI": "Diámetro Sistólico del Ventrículo Izquierdo",
    "FA": "Fracción de Acortamiento",
    "ES": "Distancia Mitro-Septal (ES)",
    "DDSIV": "Espesor del Septum Interventricular",
    "DDPP": "Espesor de la Pared Posterior",
    "DRAO": "Diámetro de la Raíz Aórtica",
    "DDAI": "Diámetro de la Aurícula Izquierda",
    "AAO": "Apertura Aórtica",
    "Masa": "Masa Ventricular Izquierda",
    "Índice Masa": "Índice de Masa Ventricular"
}

def extraer_datos_excel(file):
    """Lee ambas hojas del único archivo Excel"""
    datos = {}
    try:
        # Leer hoja de Ecocardiograma
        df_eco = pd.read_excel(file, sheet_name="Ecodato", header=None)
        for _, row in df_eco.iterrows():
            k = str(row[0]).strip()
            v = str(row[1]).strip()
            if k and k != "nan": datos[k] = v
            # Capturar peso/altura de las columnas de la derecha si están ahí
            if "Peso" in str(row[8]): datos["Peso"] = row[9]
            if "Altura" in str(row[8]): datos["Altura"] = row[9]
            if "DUBOIS" in str(row[10]): datos["BSA"] = row[11]

        # Leer hoja de Doppler
        df_dop = pd.read_excel(file, sheet_name="Doppler", header=None)
        datos["Doppler_Info"] = df_dop.to_string() # Enviamos la tabla completa a la IA
    except Exception as e:
        st.error(f"Error leyendo las hojas del Excel: {e}")
    return datos

def redactar_informe_ia(datos):
    # Preparamos los datos con nombres completos para que la IA no invente
    lista_datos = ""
    for k, v in datos.items():
        if k in TRADUCCIONES:
            lista_datos += f"- {TRADUCCIONES[k]}: {v}\n"
        elif k not in ["Doppler_Info", "Peso", "Altura", "BSA"]:
            lista_datos += f"- {k}: {v}\n"

    prompt = f"""
    Eres un Cardiólogo experto. Redacta los 'Hallazgos' de un ecocardiograma.
    DATOS TÉCNICOS:
    {lista_datos}
    DATOS DOPPLER:
    {datos.get('Doppler_Info', 'No disponible')}

    INSTRUCCIONES:
    1. Usa NOMBRES COMPLETOS, no siglas (Ej: 'Diámetro Diastólico...' en vez de 'DDVI').
    2. Compara valores: Si el Diámetro Diastólico (DDVI) es 61mm (Ref: 56mm), descríbelo como AUMENTADO.
    3. Si la Fracción de Acortamiento (FA) es 25% (Ref: 27-47%), reporta DETERIORO de la función sistólica.
    4. NO incluyas recomendaciones de estilo de vida, dieta u obesidad.
    5. Redacta de forma corrida, técnica y formal.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return completion.choices[0].message.content

def generar_word(datos, texto_ia, pdf_file):
    doc = Document()
    
    # ENCABEZADO CON DATOS GENERALES (Punto 5)
    header = doc.add_heading('INFORME DE ECOCARDIOGRAMA Y DOPPLER', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos.get('Paciente', 'BALEIRON MANUEL')}\n").bold = True
    p.add_run(f"FECHA: 27/01/2026\n").bold = True
    p.add_run(f"PESO: {datos.get('Peso', 'N/A')} kg | ALTURA: {datos.get('Altura', 'N/A')} cm | SC: {datos.get('BSA', 'N/A')} m²")

    # HALLAZGOS (Punto 3)
    doc.add_heading('Descripción de Hallazgos', level=1)
    doc.add_paragraph(texto_ia)

    # ANEXO IMÁGENES 4x2
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
            run = table.rows[row].cells[col].paragraphs[0].add_run()
            run.add_picture(imgs[i], width=Inches(3.0))

    # FIRMA (Punto 4)
    if os.path.exists("firma_doctor.png"):
        doc.add_paragraph("\n")
        f_p = doc.add_paragraph()
        f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_p.add_run().add_picture("firma_doctor.png", width=Inches(2.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ STREAMLIT ---
st.title("Generador de Informes Cardiológicos V2")

col1, col2 = st.columns(2)
with col1:
    f_excel = st.file_uploader("Subir Excel (Hojas: Ecodato y Doppler)", type=["xlsx", "xls"])
with col2:
    f_pdf = st.file_uploader("Subir PDF de Imágenes", type=["pdf"])

if f_excel and f_pdf:
    if st.button("🚀 Generar Informe Word"):
        with st.spinner("Procesando datos médicos..."):
            datos = extraer_datos_excel(f_excel)
            texto_ia = redactar_informe_ia(datos)
            docx = generar_word(datos, texto_ia, f_pdf)
            st.success("Informe generado.")
            st.download_button("📥 Descargar Word", docx, "Informe_Cardio.docx")
