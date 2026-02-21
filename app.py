
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# CONFIGURACIÓN
st.set_page_config(page_title="Cardio-IA Report Pro", layout="wide")

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró la clave GROQ_API_KEY en los Secrets.")
    st.stop()

def extraer_datos_completos(file):
    """Lee todas las hojas del Excel para no perder datos de Doppler"""
    datos = {}
    try:
        # Leemos todas las hojas del Excel
        dict_dfs = pd.read_excel(file, sheet_name=None, header=None)
        
        for nombre_hoja, df in dict_dfs.items():
            for _, row in df.iterrows():
                if len(row) >= 2:
                    key = str(row[0]).strip()
                    val = str(row[1]).strip() if pd.notna(row[1]) else ""
                    if key and key.lower() != "nan":
                        datos[key] = val
        return datos
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

def redactar_informe_ia(datos_dict):
    """Pide a la IA una redacción médica narrativa y dividida"""
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Eres un médico cardiólogo experto. Tu tarea es redactar un informe profesional basado en estos datos:
    {datos_texto}

    ESTRUCTURA OBLIGATORIA:
    1. Sección 'ECOCARDIOGRAMA 2D': Describe diámetros, espesores y función sistólica de forma narrativa.
    2. Sección 'DOPPLER CARDIACO': Describe flujos valvulares y hallazgos hemodinámicos.
    
    REGLAS:
    - NO hagas listas de puntos. Redacta párrafos médicos fluidos.
    - NO incluyas recomendaciones ni consejos.
    - Usa terminología técnica (ej. 'Fracción de eyección conservada', 'Raíz aórtica de diámetros normales').
    - Si hay observaciones en los datos, inclúyelas de forma coherente.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception:
        return "Error en la redacción de la IA."

def generar_word_mejorado(datos, cuerpo_texto, pdf_file, firma_path):
    doc = Document()
    
    # Encabezado principal
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER COLOR', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Bloque de datos del paciente (Encabezado detallado)
    table_info = doc.add_table(rows=3, cols=2)
    table_info.autofit = True
    
    # Fila 1
    table_info.cell(0,0).text = f"PACIENTE: {datos.get('Paciente', 'N/A')}"
    table_info.cell(0,1).text = f"FECHA: {datos.get('Fecha de estudio', 'N/A')}"
    # Fila 2
    table_info.cell(1,0).text = f"PESO: {datos.get('Peso', 'N/A')} kg"
    table_info.cell(1,1).text = f"ALTURA: {datos.get('Altura', 'N/A')} cm"
    # Fila 3
    table_info.cell(2,0).text = f"S. CORPORAL: {datos.get('Superficie Corporal', 'N/A')} m²"
    table_info.cell(2,1).text = f"EDAD: {datos.get('Edad', 'N/A')}"

    doc.add_paragraph("\n") # Espacio

    # Cuerpo redactado por la IA
    doc.add_paragraph(cuerpo_texto)

    # Anexo de Imágenes (4x2)
    doc.add_page_break()
    doc.add_heading('ANEXO DE IMÁGENES', level=1)
    
    try:
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        img_list = []
        for page in pdf_doc:
            for img_info in page.get_images(full=True):
                img_list.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

        if img_list:
            grid = doc.add_table(rows=4, cols=2)
            for i in range(min(len(img_list), 8)):
                row, col = i // 2, i % 2
                paragraph = grid.rows[row].cells[col].paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(img_list[i], width=Inches(3.0))
    except:
        pass

    # FIRMA DIGITAL
    if os.path.exists(firma_path):
        doc.add_paragraph("\n\n")
        f_para = doc.add_paragraph()
        f_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_para.add_run().add_picture(firma_path, width=Inches(1.8))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# INTERFAZ STREAMLIT
st.title("🩺 Generador de Informes Cardiológicos Avanzado")

col1, col2 = st.columns(2)
with col1:
    f_data = st.file_uploader("Subir Cálculos (Excel/CSV)", type=["xlsx", "xls", "csv"])
with col2:
    f_pdf = st.file_uploader("Subir PDF de Sonoscape", type=["pdf"])

if f_data and f_pdf:
    if st.button("🚀 Generar Informe Profesional"):
        with st.spinner("Procesando todas las hojas y redactando informe..."):
            dict_datos = extraer_datos_completos(f_data)
            texto_ia = redactar_informe_ia(dict_datos)
            docx_out = generar_word_mejorado(dict_datos, texto_ia, f_pdf, "firma_doctor.png")
            
            st.success("Informe redactado con éxito.")
            st.download_button("📥 Descargar Word", docx_out, 
                               f"Informe_{dict_datos.get('Paciente','Estudio')}.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
