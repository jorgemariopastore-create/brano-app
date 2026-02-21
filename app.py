
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA Y API ---
st.set_page_config(page_title="Generador Cardio-IA", layout="wide")

# Conexión con Groq usando Secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("No se encontró 'GROQ_API_KEY' en los Secrets de Streamlit.")
    st.stop()

def extraer_datos(file):
    """Lee el archivo CSV o Excel y limpia los datos"""
    try:
        if file.name.endswith('.csv'):
            # Para CSVs como los de Sonoscape
            df = pd.read_csv(file, header=None)
        else:
            df = pd.read_excel(file, header=None)
        
        datos = {}
        for _, row in df.iterrows():
            key = str(row[0]).strip()
            val = str(row[1]).strip() if pd.notna(row[1]) else ""
            if key and key != "nan":
                datos[key] = val
        return datos
    except Exception as e:
        st.error(f"Error al leer el archivo de datos: {e}")
        return None

def redactar_informe_ia(datos_dict):
    """Groq redacta el informe técnico sin dar recomendaciones"""
    # Convertimos los datos a texto para la IA
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Eres un cardiólogo redactando un informe profesional. 
    Usa estos datos de ecocardiografía y doppler: 
    {datos_texto}
    
    INSTRUCCIONES:
    1. Redacta de forma técnica, profesional y fluida.
    2. NO incluyas recomendaciones de tratamiento ni pasos a seguir.
    3. NO incluyas consejos de salud.
    4. Si hay una fila llamada 'Observaciones', incluye ese texto en el cuerpo del informe.
    5. No inventes datos; solo usa lo proporcionado.
    """
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0, # Determinismo máximo
    )
    return completion.choices[0].message.content

def generar_word(datos, cuerpo_texto, pdf_file, firma_path):
    """Crea el documento Word con texto e imágenes en 4x2"""
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER COLOR', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Información del Paciente
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    # Intenta buscar 'Paciente' en los datos, si no usa un valor genérico
    nombre = datos.get('Paciente', 'BALEIRON MANUEL')
    p.add_run(f"{nombre}\n")
    p.add_run("FECHA DE ESTUDIO: ").bold = True
    p.add_run(f"{datos.get('Fecha de estudio', 'N/A')}")

    # Cuerpo del Informe (IA)
    doc.add_heading('Descripción de Hallazgos', level=1)
    doc.add_paragraph(cuerpo_texto)

    # Anexo de Imágenes (4 filas x 2 columnas)
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    
    pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    img_streams = []
    for page in pdf_doc:
        for img_info in page.get_images(full=True):
            img_streams.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

    if img_streams:
        # Tabla de 4 filas x 2 columnas
        table = doc.add_table(rows=4, cols=2)
        for i in range(min(len(img_streams), 8)):
            row, col = i // 2, i % 2
            celda = table.rows[row].cells[col]
            parrafo = celda.paragraphs[0]
            parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = parrafo.add_run()
            run.add_picture(img_streams[i], width=Inches(3.0))

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
st.title("👨‍⚕️ Generador de Informes Cardiológicos IA")
st.markdown("Suba el archivo de datos y el PDF de capturas para generar el Word.")

col1, col2 = st.columns(2)
with col1:
    f_data = st.file_uploader("Subir Cálculos (CSV/Excel)", type=["csv", "xlsx"])
with col2:
    f_pdf = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if f_data and f_pdf:
    if st.button("🚀 Generar Informe Profesional"):
        with st.spinner("Procesando..."):
            # 1. Extraer
            dict_datos = extraer_datos(f_data)
            # 2. IA Groq
            texto_ia = redactar_informe_ia(dict_datos)
            # 3. Crear Word
            docx_output = generar_word(dict_datos, texto_ia, f_pdf, "firma_doctor.png")
            
            st.success("Informe redactado por IA exitosamente.")
            
            with st.expander("Ver texto generado"):
                st.write(texto_ia)
            
            st.download_button(
                label="📥 Descargar Informe en Word",
                data=docx_output,
                file_name=f"Informe_{dict_datos.get('Paciente', 'Cardio')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
