
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
    """
    Intenta leer el archivo con diferentes codificaciones y limpia 
    caracteres extraños típicos de formatos viejos.
    """
    df = None
    # Probamos diferentes codificaciones comunes en equipos médicos
    for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
        try:
            file.seek(0) # Reiniciar el puntero del archivo
            if file.name.endswith('.csv'):
                # Probamos coma y punto y coma como separadores
                df = pd.read_csv(file, sep=None, engine='python', encoding=encoding, header=None)
            else:
                df = pd.read_excel(file, header=None)
            break # Si lo lee, salimos del bucle
        except:
            continue
    
    if df is None:
        st.error("No se pudo leer el archivo. Verifica que no esté abierto en Excel o dañado.")
        return {}

    datos = {}
    for _, row in df.iterrows():
        # Limpiamos cada celda de espacios y caracteres de control
        key = str(row[0]).strip() if pd.notna(row[0]) else ""
        val = str(row[1]).strip() if pd.notna(row[1]) else ""
        
        # Filtramos filas vacías o basura
        if key and key.lower() != "nan" and key != "":
            datos[key] = val
            
    return datos

def redactar_con_ia(datos_dict):
    """Envía los datos a Groq para redacción médica pura"""
    # Creamos un resumen limpio para la IA
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items() if v])
    
    prompt = f"""
    Eres un cardiólogo procesando un estudio de Sonoscape. 
    Redacta los hallazgos técnicos de un ecocardiograma y doppler.
    
    DATOS DEL ESTUDIO:
    {datos_texto}
    
    REGLAS ESTRICTAS:
    1. Usa lenguaje médico formal y descriptivo.
    2. NO incluyas recomendaciones, consejos ni pasos a seguir.
    3. NO menciones tratamientos.
    4. Si hay 'Observaciones', lístalas como parte de los hallazgos.
    5. Empieza directamente con el informe.
    """
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return completion.choices[0].message.content

def generar_word(datos, texto_ia, pdf_file):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos básicos (buscando coincidencias comunes de nombres de campo)
    paciente = datos.get('Paciente', datos.get('Nombre', 'No especificado'))
    fecha = datos.get('Fecha de estudio', datos.get('Fecha', 'No especificada'))

    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{paciente}\n")
    p.add_run("FECHA: ").bold = True
    p.add_run(f"{fecha}")

    # Cuerpo redactado por IA
    doc.add_heading('Descripción Técnica', level=1)
    doc.add_paragraph(texto_ia)

    # Anexo de Imágenes (4 filas x 2 columnas)
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    
    try:
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
                paragraph = cell.paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(imgs[i], width=Inches(3.0))
    except Exception as e:
        doc.add_paragraph(f"\nNo se pudieron extraer imágenes del PDF: {e}")

    # FIRMA DIGITAL
    ruta_firma = "firma_doctor.png"
    if os.path.exists(ruta_firma):
        doc.add_paragraph("\n")
        f_para = doc.add_paragraph()
        f_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_run = f_para.add_run()
        f_run.add_picture(ruta_firma, width=Inches(1.8))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ STREAMLIT ---
st.title("Cardio-Report IA 🩺")
st.write("Carga de archivos con soporte para formatos antiguos.")

c1, c2 = st.columns(2)
with c1:
    f_excel = st.file_uploader("Subir Cálculos (Excel/CSV)", type=["csv", "xlsx", "xls"])
with c2:
    f_pdf = st.file_uploader("Subir PDF (Imágenes)", type=["pdf"])

if f_excel and f_pdf:
    if st.button("Generar Informe Profesional"):
        with st.spinner("Limpiando datos y redactando..."):
            datos_ext = extraer_datos_limpios(f_excel)
            if datos_ext:
                texto_ia = redactar_con_ia(datos_ext)
                docx_file = generar_word(datos_ext, texto_ia, f_pdf)
                
                st.success("¡Informe procesado con éxito!")
                st.download_button("📥 Descargar Word Editable", docx_file, 
                                   f"Informe_Medico.docx")
