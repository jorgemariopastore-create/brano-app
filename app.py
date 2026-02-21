
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# 1. CONEXIÓN
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Falta API Key")
    st.stop()

# Mapeo de siglas para que la IA no invente "Frecuencias Cardíacas"
DICCIONARIO_MEDICO = {
    "DDVD": "Diámetro Diastólico del Ventrículo Derecho",
    "DDVI": "Diámetro Diastólico del Ventrículo Izquierdo",
    "DSVI": "Diámetro Sistólico del Ventrículo Izquierdo",
    "FA": "Fracción de Acortamiento",
    "ES": "Distancia Mitro-Septal (EPSS)",
    "DDSIV": "Diámetro Diastólico del Septum Interventricular",
    "DDPP": "Diámetro Diastólico de la Pared Posterior",
    "DRAO": "Diámetro de la Raíz Aórtica",
    "DDAI": "Diámetro de la Aurícula Izquierda",
    "AAO": "Apertura Aórtica"
}

def extraer_datos_completos(f_eco, f_doppler):
    """Extrae y combina datos de ambas hojas"""
    datos = {}
    
    # Procesar Eco (Ecodato)
    try:
        df_eco = pd.read_csv(f_eco, header=None, encoding='latin-1')
        for _, row in df_eco.iterrows():
            k, v = str(row[0]).strip(), str(row[1]).strip()
            if k and k != "nan": datos[k] = v
    except: pass

    # Procesar Doppler
    try:
        f_doppler.seek(0)
        df_dop = pd.read_csv(f_doppler, header=None, encoding='latin-1')
        # Buscamos las filas de válvulas (Tricúspide, Pulmonar, etc.)
        for _, row in df_dop.iterrows():
            valvula = str(row[0]).strip()
            if valvula in ["Tricúspide", "Pulmonar", "Mitral", "Aórtica"]:
                datos[f"Velocidad {valvula}"] = str(row[1])
    except: pass
    
    return datos

def redactar_informe_ia(datos):
    # Traducir siglas para el prompt
    datos_expandidos = ""
    for k, v in datos.items():
        nombre = DICCIONARIO_MEDICO.get(k, k)
        datos_expandidos += f"{nombre}: {v}\n"

    prompt = f"""
    Eres un cardiólogo. Redacta el informe técnico basado en estos datos:
    {datos_expandidos}
    
    REGLAS CRÍTICAS:
    1. Usa los nombres completos (ej. 'Diámetro Diastólico...') NO uses siglas.
    2. Compara con los valores normales. Si el DDVI es 61mm (normal hasta 56), descríbelo como aumentado.
    3. Si la Fracción de Acortamiento (FA) es baja (24%), descríbelo como deterioro de la función sistólica.
    4. NO des consejos de salud, ni hables de obesidad ni cambios de dieta.
    5. NO menciones 'Frecuencia cardíaca' a menos que el dato diga 'FC'.
    6. Sé puramente descriptivo y técnico.
    """
    
    chat = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return chat.choices[0].message.content

def generar_word(datos, texto_ia, f_pdf):
    doc = Document()
    
    # 1. ENCABEZADO CON DATOS GENERALES
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    table_hdr = doc.add_table(rows=3, cols=2)
    table_hdr.cell(0,0).text = f"PACIENTE: {datos.get('Paciente', 'N/A')}"
    table_hdr.cell(0,1).text = f"FECHA: 27/01/2026"
    table_hdr.cell(1,0).text = f"PESO: {datos.get('Peso', 'N/A')} Kg"
    table_hdr.cell(1,1).text = f"ALTURA: {datos.get('Altura', '150')} cm"
    table_hdr.cell(2,0).text = f"S. CORPORAL: {datos.get('Sup. Corporal', 'N/A')} m²"

    # 2. CUERPO DEL INFORME
    doc.add_heading('Descripción Técnica', level=1)
    doc.add_paragraph(texto_ia)

    # 3. IMÁGENES
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    try:
        f_pdf.seek(0)
        pdf = fitz.open(stream=f_pdf.read(), filetype="pdf")
        imgs = []
        for page in pdf:
            for img in page.get_images():
                imgs.append(io.BytesIO(pdf.extract_image(img[0])["image"]))
        
        if imgs:
            tabla_img = doc.add_table(rows=4, cols=2)
            for i in range(min(len(imgs), 8)):
                run = tabla_img.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(imgs[i], width=Inches(2.8))
    except: pass

    # 4. FIRMA (Asegurada al final)
    if os.path.exists("firma_doctor.png"):
        p_firma = doc.add_paragraph()
        p_firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_firma.add_run().add_picture("firma_doctor.png", width=Inches(2.0))

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

# --- UI ---
st.title("Generador Pro 🩺")
f_eco = st.file_uploader("Subir Ecodato (CSV)", type="csv")
f_dop = st.file_uploader("Subir Doppler (CSV)", type="csv")
f_pdf = st.file_uploader("Subir PDF", type="pdf")

if f_eco and f_dop and f_pdf:
    if st.button("Generar Informe"):
        datos = extraer_datos_completos(f_eco, f_dop)
        texto = redactar_informe_ia(datos)
        word = generar_word(datos, texto, f_pdf)
        st.download_button("Descargar Informe", word, "Informe_Final.docx")
