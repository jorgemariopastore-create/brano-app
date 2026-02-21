
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

# Configuración API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def lectura_universal_excel(file):
    """Intenta leer el archivo Sonoscape de 3 formas distintas para no fallar"""
    datos = {"Eco": None, "Doppler": None}
    try:
        # Intento 1: Excel Estándar (.xlsx o .xls real)
        xls = pd.ExcelFile(file)
        if "Ecodato" in xls.sheet_names:
            datos["Eco"] = pd.read_excel(xls, "Ecodato", header=None)
        if "Doppler" in xls.sheet_names:
            datos["Doppler"] = pd.read_excel(xls, "Doppler", header=None)
    except:
        try:
            # Intento 2: Si el .xls es en realidad un HTML (común en Sonoscape)
            file.seek(0)
            tablas = pd.read_html(file)
            datos["Eco"] = tablas[0] # Usualmente la primera tabla
            if len(tablas) > 1: datos["Doppler"] = tablas[1]
        except:
            st.error("El formato del Excel no es compatible. Intenta exportarlo desde el ecógrafo como CSV si es posible.")
    return datos

def procesar_datos_medicos(tablas):
    """Extrae la info clave y la prepara para la narrativa"""
    info = {"paciente": {}, "mediciones": "", "doppler": ""}
    
    df_eco = tablas["Eco"]
    if df_eco is not None:
        # Extraer Encabezado (Peso, Altura, BSA de las celdas de Sonoscape)
        try:
            info["paciente"]["Nombre"] = str(df_eco.iloc[3, 1])
            info["paciente"]["Peso"] = str(df_eco.iloc[7, 9])
            info["paciente"]["Altura"] = str(df_eco.iloc[8, 9])
            info["paciente"]["BSA"] = str(df_eco.iloc[7, 11])
        except: pass

        # Mapeo de mediciones para la IA
        dicc = {"DDVI": "Diámetro Diastólico VI", "DSVI": "Diámetro Sistólico VI", 
                "FA": "Fracción de Acortamiento", "DDVD": "Diámetro VD", 
                "DDAI": "Aurícula Izquierda"}
        
        for i in range(7, 20):
            try:
                sigla = str(df_eco.iloc[i, 0]).strip()
                if sigla in dicc:
                    val = df_eco.iloc[i, 1]
                    ref = df_eco.iloc[i, 3]
                    info["mediciones"] += f"{dicc[sigla]}: {val} (Referencia: {ref})\n"
            except: pass

    df_dop = tablas["Doppler"]
    if df_dop is not None:
        for i in range(2, len(df_dop)):
            try:
                v = str(df_dop.iloc[i, 0])
                vel = str(df_dop.iloc[i, 1])
                if v in ["Tricúspide", "Pulmonar", "Mitral", "Aórtica"]:
                    info["doppler"] += f"Válvula {v}: {vel} cm/s\n"
            except: pass
            
    return info

def redactar_informe_prosa(info):
    """La IA convierte los datos en un informe de cardiólogo real"""
    prompt = f"""
    Actúa como un Cardiólogo Senior. Redacta la 'Descripción Técnica' de un ecocardiograma.
    USA PROSA MÉDICA (Párrafos fluidos). NO USES LISTAS NI VIÑETAS.
    
    DATOS:
    {info['mediciones']}
    {info['doppler']}
    
    ESTRUCTURA:
    1. Cavidades izquierdas y función sistólica (menciona si hay dilatación o deterioro basado en las referencias).
    2. Cavidades derechas.
    3. Análisis Doppler valvular.
    
    REGLA DE ORO: Si el Diámetro Diastólico VI es superior a la referencia, descríbelo como 'dilatado'. 
    Si la FA es inferior al 27%, descríbelo como 'función sistólica deteriorada'. 
    Sé técnico, breve y profesional. No des consejos de salud.
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

def crear_word(info, narrativa, pdf_file):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {info['paciente'].get('Nombre', 'N/A')}\n").bold = True
    p.add_run(f"PESO: {info['paciente'].get('Peso', '-')} kg | ALTURA: {info['paciente'].get('Altura', '-')} cm | SC: {info['paciente'].get('BSA', '-')} m²")

    doc.add_heading('Hallazgos Clínicos', level=1)
    doc.add_paragraph(narrativa)

    # Anexo Imágenes 4x2
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    try:
        pdf_file.seek(0)
        pdf = fitz.open(stream=pdf_file.read(), filetype="pdf")
        imgs = [io.BytesIO(pdf.extract_image(img[0])["image"]) for p in pdf for img in p.get_images()]
        if imgs:
            tabla = doc.add_table(rows=4, cols=2)
            for i in range(min(len(imgs), 8)):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(imgs[i], width=Inches(2.8))
    except: pass

    # Firma
    if os.path.exists("firma_doctor.png"):
        f_p = doc.add_paragraph()
        f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_p.add_run().add_picture("firma_doctor.png", width=Inches(1.8))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- Interfaz ---
st.title("CardioReport Sonoscape 🩺")
f_excel = st.file_uploader("Subir Excel del Ecógrafo", type=["xls", "xlsx"])
f_pdf = st.file_uploader("Subir PDF de Imágenes", type="pdf")

if f_excel and f_pdf:
    if st.button("Generar Informe Médico"):
        with st.spinner("Leyendo datos y redactando..."):
            tablas = lectura_universal_excel(f_excel)
            if tablas["Eco"] is not None:
                info = procesar_datos_medicos(tablas)
                narrativa = redactar_informe_prosa(info)
                word = crear_word(info, narrativa, f_pdf)
                st.success("Informe generado.")
                st.download_button("Descargar Word", word, "Informe.docx")
            else:
                st.error("No se pudo extraer información del archivo. Verifica que sea el exportado por el Sonoscape.")
