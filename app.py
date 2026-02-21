
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

# Diccionario Maestro para traducir siglas a nombres técnicos reales
DICCIONARIO_TECNICO = {
    "DDVD": "Diámetro Diastólico del Ventrículo Derecho",
    "DDVI": "Diámetro Diastólico del Ventrículo Izquierdo",
    "DSVI": "Diámetro Sistólico del Ventrículo Izquierdo",
    "FA": "Fracción de Acortamiento",
    "ES": "Distancia Mitro-Septal (EPSS)",
    "DDSIV": "Espesor del Septum Interventricular",
    "DDPP": "Espesor de la Pared Posterior",
    "DRAO": "Diámetro de la Raíz Aórtica",
    "DDAI": "Diámetro de la Aurícula Izquierda",
    "AAO": "Apertura Aórtica",
    "Masa": "Masa Ventricular Izquierda",
    "Índice Masa": "Índice de Masa Ventricular"
}

def extraer_datos_excel(file):
    """Lee las dos hojas del Excel y extrae datos de paciente y mediciones"""
    datos = {"mediciones": {}, "doppler": [], "paciente": {}}
    
    try:
        # Cargar todas las hojas
        xls = pd.ExcelFile(file)
        
        # 1. Procesar Hoja "Ecodato"
        if "Ecodato" in xls.sheet_names:
            df_eco = pd.read_excel(xls, "Ecodato", header=None)
            # Datos generales (basado en la estructura de Sonoscape)
            datos["paciente"]["Nombre"] = str(df_eco.iloc[3, 1]) if len(df_eco) > 3 else "N/A"
            # Peso, Altura y BSA suelen estar en las columnas I, J, K (índices 8, 9, 11)
            try:
                datos["paciente"]["Peso"] = df_eco.iloc[7, 9] 
                datos["paciente"]["Altura"] = df_eco.iloc[8, 9]
                datos["paciente"]["BSA"] = df_eco.iloc[7, 11]
            except: pass

            # Mediciones de cavidades
            for i in range(6, 18): # Rango típico de siglas
                if i < len(df_eco):
                    sigla = str(df_eco.iloc[i, 0]).strip()
                    valor = str(df_eco.iloc[i, 1]).strip()
                    ref = str(df_eco.iloc[i, 3]).strip()
                    if sigla in DICCIONARIO_TECNICO:
                        datos["mediciones"][DICCIONARIO_TECNICO[sigla]] = f"{valor} (Ref: {ref})"

        # 2. Procesar Hoja "Doppler"
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(2, len(df_dop)):
                valvula = str(df_dop.iloc[i, 0]).strip()
                vel = str(df_dop.iloc[i, 1]).strip()
                if valvula in ["Tricúspide", "Pulmonar", "Mitral", "Aórtica"]:
                    datos["doppler"].append(f"Válvula {valvula}: {vel} cm/seg")
                    
    except Exception as e:
        st.error(f"Error técnico al leer el Excel: {e}")
    return datos

def redactar_informe_estricto(datos):
    """Genera el texto usando ÚNICAMENTE los datos del Excel"""
    contexto = "\n".join([f"{k}: {v}" for k, v in datos["mediciones"].items()])
    contexto_dop = "\n".join(datos["doppler"])
    
    prompt = f"""
    Eres un transcriptor médico. Tu tarea es redactar los hallazgos de un ecocardiograma.
    
    DATOS DE CAVIDADES:
    {contexto}
    
    DATOS DOPPLER:
    {contexto_dop}
    
    REGLAS ESTRICTAS:
    1. Prohibido inventar datos o dar consejos de salud/dieta/ejercicio.
    2. Usa los nombres completos proporcionados.
    3. Si el Diámetro Diastólico del VI está fuera de rango, descríbelo como 'aumentado'.
    4. Si la Fracción de Acortamiento está baja, descríbelo como 'deterioro de la función sistólica'.
    5. Redacta en párrafos técnicos y formales.
    """
    
    chat = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0 # Cero creatividad
    )
    return chat.choices[0].message.content

def generar_word(datos, texto_ia, pdf_file):
    doc = Document()
    
    # 1. ENCABEZADO PROFESIONAL (Punto 5)
    header = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER COLOR', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['paciente'].get('Nombre', 'N/A')}\n").bold = True
    p.add_run(f"FECHA DE ESTUDIO: 27/01/2026\n").bold = True
    p.add_run(f"PESO: {datos['paciente'].get('Peso', 'N/A')} kg  |  ALTURA: {datos['paciente'].get('Altura', 'N/A')} cm  |  SC: {datos['paciente'].get('BSA', 'N/A')} m²")

    # 2. HALLAZGOS (Punto 3 y 6 corregidos)
    doc.add_heading('Descripción Técnica', level=1)
    doc.add_paragraph(texto_ia)

    # 3. ANEXO DE IMÁGENES 4x2
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    try:
        pdf_file.seek(0)
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        imgs = []
        for page in pdf_doc:
            for img in page.get_images(full=True):
                imgs.append(io.BytesIO(pdf_doc.extract_image(img[0])["image"]))
        
        if imgs:
            table = doc.add_table(rows=4, cols=2)
            for i in range(min(len(imgs), 8)):
                run = table.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(imgs[i], width=Inches(2.8))
    except: pass

    # 4. FIRMA (Punto 4)
    if os.path.exists("firma_doctor.png"):
        doc.add_paragraph("\n")
        f_p = doc.add_paragraph()
        f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_p.add_run().add_picture("firma_doctor.png", width=Inches(2.0))

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

# --- INTERFAZ ---
st.title("Sistema de Informes Sonoscape 🩺")
st.write("Procesamiento fiel de datos de Ecocardiografía.")

f_excel = st.file_uploader("Subir Excel (Pestañas Ecodato y Doppler)", type="xlsx")
f_pdf = st.file_uploader("Subir PDF de Imágenes", type="pdf")

if f_excel and f_pdf:
    if st.button("🚀 Generar Informe Fiel"):
        with st.spinner("Leyendo datos del ecógrafo..."):
            datos = extraer_datos_excel(f_excel)
            if datos["mediciones"]:
                texto = redactar_informe_estricto(datos)
                docx = generar_word(datos, texto, f_pdf)
                st.success("Informe generado con éxito.")
                st.download_button("📥 Descargar Word", docx, "Informe_Cardio.docx")
            else:
                st.error("No se pudieron leer las pestañas 'Ecodato' o 'Doppler'. Revisa el nombre de las hojas.")
