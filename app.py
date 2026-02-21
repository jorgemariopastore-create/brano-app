
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Cardio-IA Report", layout="wide")

# 2. CONEXIÓN CON GROQ (Secrets)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró la clave GROQ_API_KEY en los Secrets.")
    st.stop()

def extraer_datos(file):
    """Extrae datos de CSV, XLSX o XLS (formato antiguo)"""
    try:
        nombre_archivo = file.name.lower()
        if nombre_archivo.endswith('.csv'):
            df = pd.read_csv(file, header=None)
        elif nombre_archivo.endswith('.xls'):
            # El motor 'xlrd' permite leer archivos Excel antiguos
            df = pd.read_excel(file, header=None, engine='xlrd')
        else:
            # Para .xlsx modernos
            df = pd.read_excel(file, header=None, engine='openpyxl')
        
        datos = {}
        for _, row in df.iterrows():
            key = str(row[0]).strip()
            val = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
            if key and key != "nan":
                datos[key] = val
        return datos
    except Exception as e:
        st.error(f"Error al procesar el archivo de datos: {e}")
        return None

def redactar_informe_ia(datos_dict):
    """Groq redacta el texto médico puro sin recomendaciones"""
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Actúa como un cardiólogo profesional redactando los 'Hallazgos' de un ecocardiograma. 
    Usa estos datos técnicos: 
    {datos_texto}
    
    REGLAS ESTRICTAS:
    - NO incluyas recomendaciones ni pasos a seguir.
    - NO des consejos de salud.
    - Usa lenguaje médico formal y técnico.
    - Si el médico escribió 'Observaciones', incorpóralas al texto.
    - Sé directo, empieza con la descripción del estudio.
    """
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0, 
    )
    return completion.choices[0].message.content

def generar_word(datos, cuerpo_texto, pdf_file, firma_path):
    """Genera el documento Word con cuadrícula 4x2 e imágenes del PDF"""
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos del paciente (ajustar claves según tu Excel)
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{datos.get('Paciente', 'N/A')}\n")
    p.add_run("FECHA DE ESTUDIO: ").bold = True
    p.add_run(f"{datos.get('Fecha de estudio', 'N/A')}")

    # Texto de la IA
    doc.add_heading('Hallazgos Ecocardiográficos', level=1)
    doc.add_paragraph(cuerpo_texto)

    # ANEXO DE IMÁGENES: 4 FILAS X 2 COLUMNAS
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    
    # Extraer imágenes del PDF de Sonoscape
    pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    img_list = []
    for page in pdf_doc:
        for img_info in page.get_images(full=True):
            img_list.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

    if img_list:
        # Definir tabla de 4 filas x 2 columnas
        table = doc.add_table(rows=4, cols=2)
        for i in range(min(len(img_list), 8)):
            row, col = i // 2, i % 2
            paragraph = table.rows[row].cells[col].paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            # Ancho de 3 pulgadas para que quepan 2 por fila
            run.add_picture(img_list[i], width=Inches(3.0))

    # FIRMA FINAL
    if os.path.exists(firma_path):
        doc.add_paragraph("\n")
        f_para = doc.add_paragraph()
        f_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_para.add_run().add_picture(firma_path, width=Inches(2.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ DE STREAMLIT ---
st.title("🩺 Generador de Reportes Cardiológicos Pro")
st.write("Suba el archivo de cálculos y el PDF con capturas.")

col1, col2 = st.columns(2)
with col1:
    # Agregamos 'xls' a los tipos permitidos
    f_data = st.file_uploader("1. Archivo de Cálculos (XLS, XLSX, CSV)", type=["csv", "xlsx", "xls"])
with col2:
    f_pdf = st.file_uploader("2. PDF del Ecógrafo", type=["pdf"])

if f_data and f_pdf:
    if st.button("🚀 Generar Informe Word"):
        with st.spinner("Procesando datos y redactando con IA..."):
            dict_datos = extraer_datos(f_data)
            if dict_datos:
                texto_ia = redactar_informe_ia(dict_datos)
                docx_out = generar_word(dict_datos, texto_ia, f_pdf, "firma_doctor.png")
                
                st.success("✅ Informe generado correctamente")
                
                st.download_button(
                    label="📥 Descargar Word Editable",
                    data=docx_out,
                    file_name=f"Informe_{dict_datos.get('Paciente', 'Estudio')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
