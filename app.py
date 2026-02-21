
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cardio-IA Report Pro", layout="centered")

# --- CONEXIÓN CON GROQ (Secrets) ---
try:
    # Intenta leer la clave de los secrets
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error de Configuración: No se encontró la clave GROQ_API_KEY en los Secrets.")
    st.stop()

def extraer_datos(file):
    """Extrae datos de CSV, XLSX o XLS con manejo de errores"""
    try:
        nombre_archivo = file.name.lower()
        if nombre_archivo.endswith('.csv'):
            df = pd.read_csv(file, header=None)
        elif nombre_archivo.endswith('.xls'):
            df = pd.read_excel(file, header=None, engine='xlrd')
        else:
            df = pd.read_excel(file, header=None, engine='openpyxl')
        
        datos = {}
        for _, row in df.iterrows():
            if len(row) >= 2:
                key = str(row[0]).strip()
                val = str(row[1]).strip() if pd.notna(row[1]) else ""
                if key and key.lower() != "nan":
                    datos[key] = val
        return datos
    except Exception as e:
        st.error(f"Error al leer el archivo de Excel/CSV: {e}")
        return None

def redactar_informe_ia(datos_dict):
    """Groq redacta el texto médico. Si falla el modelo grande, intenta con el pequeño."""
    if not datos_dict:
        return "No se encontraron datos para procesar."

    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Eres un cardiólogo profesional. Redacta los 'Hallazgos' técnicos de un ecocardiograma. 
    DATOS: {datos_texto}
    REGLAS: Sin recomendaciones, sin consejos, lenguaje formal, integra 'Observaciones' si existen.
    """
    
    # Intentamos con el modelo más estable
    modelos_a_probar = ["llama-3.3-70b-versatile", "llama3-70b-8192", "llama3-8b-8192"]
    
    for modelo in modelos_a_probar:
        try:
            completion = client.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                temperature=0, 
            )
            return completion.choices[0].message.content
        except Exception:
            continue # Si falla, intenta con el siguiente modelo
            
    return "Error: La IA de Groq no pudo procesar el informe en este momento. Intente más tarde."

def generar_word(datos, cuerpo_texto, pdf_file, firma_path):
    """Crea el Word con cuadrícula 4x2"""
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos Paciente
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{datos.get('Paciente', 'N/A')}\n")
    p.add_run("FECHA: ").bold = True
    p.add_run(f"{datos.get('Fecha de estudio', 'N/A')}")

    # Hallazgos
    doc.add_heading('Hallazgos Ecocardiográficos', level=1)
    doc.add_paragraph(cuerpo_texto)

    # Anexo de Imágenes (4 filas x 2 columnas)
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    
    try:
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        img_list = []
        for page in pdf_doc:
            for img_info in page.get_images(full=True):
                img_list.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

        if img_list:
            table = doc.add_table(rows=4, cols=2)
            for i in range(min(len(img_list), 8)):
                row, col = i // 2, i % 2
                paragraph = table.rows[row].cells[col].paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(img_list[i], width=Inches(3.0))
    except Exception as e:
        st.warning(f"No se pudieron extraer imágenes del PDF: {e}")

    # Firma
    if os.path.exists(firma_path):
        doc.add_paragraph("\n")
        f_para = doc.add_paragraph()
        f_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_para.add_run().add_picture(firma_path, width=Inches(2.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ ---
st.title("🩺 Generador de Reportes Cardio-IA")
st.info("Sube los archivos para procesar el informe.")

col1, col2 = st.columns(2)
with col1:
    f_data = st.file_uploader("1. Cálculos (XLS, XLSX, CSV)", type=["csv", "xlsx", "xls"])
with col2:
    f_pdf = st.file_uploader("2. PDF del Ecógrafo", type=["pdf"])

if f_data and f_pdf:
    if st.button("🚀 Generar Informe Word"):
        with st.spinner("Redactando informe..."):
            dict_datos = extraer_datos(f_data)
            if dict_datos:
                texto_ia = redactar_informe_ia(dict_datos)
                docx_out = generar_word(dict_datos, texto_ia, f_pdf, "firma_doctor.png")
                
                st.success("✅ ¡Listo!")
                st.download_button(
                    label="📥 Descargar Word",
                    data=docx_out,
                    file_name=f"Informe_{dict_datos.get('Paciente', 'Estudio')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
