
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
    """Extrae datos de todas las hojas y normaliza claves"""
    datos = {}
    try:
        dict_dfs = pd.read_excel(file, sheet_name=None, header=None)
        for _, df in dict_dfs.items():
            for _, row in df.iterrows():
                if len(row) >= 2:
                    key = str(row[0]).strip().replace(":", "")
                    val = str(row[1]).strip() if pd.notna(row[1]) else ""
                    if key and key.lower() != "nan":
                        datos[key] = val
        return datos
    except Exception as e:
        st.error(f"Error al leer el Excel: {e}")
        return None

def redactar_informe_ia(datos_dict):
    """Redacción al estilo del informe médico real suministrado"""
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Eres un cardiólogo redactando un informe profesional. Usa estos datos: {datos_texto}
    
    ESTILO DEL INFORME:
    1. Divide en dos secciones: 'ECOCARDIOGRAMA 2D' y 'DOPPLER CARDÍACO'.
    2. Usa una lista numerada para cada hallazgo (1., 2., 3...).
    3. NO repitas el nombre del paciente ni la fecha en el texto.
    4. Usa lenguaje extremadamente técnico y conciso (ej: 'Hipocinesia global severa', 'Hipertrofia excéntrica').
    5. No incluyas recomendaciones ni conclusiones subjetivas.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except:
        return "Error en la redacción."

def generar_word_mejorado(datos, cuerpo_texto, pdf_file, firma_path):
    doc = Document()
    
    # 1. TÍTULO
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER COLOR', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 2. ENCABEZADO (Datos del Paciente)
    # Intentamos buscar variantes de nombres de columnas
    nombre = datos.get('Paciente', datos.get('Nombre', 'N/A'))
    fecha = datos.get('Fecha de estudio', datos.get('Fecha', 'N/A'))
    peso = datos.get('Peso', 'N/A')
    altura = datos.get('Altura', 'N/A')
    sc = datos.get('Superficie Corporal', datos.get('SC', 'N/A'))
    edad = datos.get('Edad', 'N/A')

    p_header = doc.add_paragraph()
    p_header.add_run(f"PACIENTE: {nombre}").bold = True
    p_header.add_run(f"\t\tFECHA: {fecha}").bold = True
    
    p_antropo = doc.add_paragraph()
    p_antropo.add_run(f"PESO: {peso} kg  |  ALTURA: {altura} cm  |  S.C: {sc} m²  |  EDAD: {edad}")
    
    doc.add_paragraph("_" * 50) # Línea divisoria

    # 3. CUERPO DEL INFORME (Justificado)
    for linea in cuerpo_texto.split('\n'):
        if linea.strip():
            p = doc.add_paragraph(linea)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # JUSTIFICADO
            # Si es un título de sección, ponerlo en negrita
            if "ECOCARDIOGRAMA 2D" in linea or "DOPPLER CARDÍACO" in linea:
                for run in p.runs: run.bold = True

    # 4. ANEXO DE IMÁGENES (4x2)
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

    # 5. FIRMA (Al final a la derecha)
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
st.title("🩺 Generador de Informes Médicos")

col1, col2 = st.columns(2)
with col1:
    f_data = st.file_uploader("Subir Cálculos (Excel/CSV)", type=["xlsx", "xls", "csv"])
with col2:
    f_pdf = st.file_uploader("Subir PDF de Sonoscape", type=["pdf"])

if f_data and f_pdf:
    if st.button("🚀 Generar Informe con Estilo Médico"):
        with st.spinner("Procesando y justificando texto..."):
            dict_datos = extraer_datos_completos(f_data)
            texto_ia = redactar_informe_ia(dict_datos)
            docx_out = generar_word_mejorado(dict_datos, texto_ia, f_pdf, "firma_doctor.png")
            
            st.success("Informe listo.")
            st.download_button("📥 Descargar Word Editable", docx_out, 
                               f"Informe_{dict_datos.get('Paciente','Estudio')}.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
