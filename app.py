
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de Interfaz
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_profesional(texto_informe, imagenes_bytes):
    doc = Document()
    
    # Título Principal
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.underline = True
    run_t.size = Pt(14)

    # Procesar Texto con Negritas en Títulos
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Si la línea parece un título (I, II, III, IV o palabras clave)
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
        else:
            p.add_run(linea)

    # Firma
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        p_firma = doc.add_paragraph()
        p_firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_firma.add_run().add_picture("firma.jpg", width=Inches(1.5))

    # ANEXO DE IMÁGENES (4 por fila)
    if imagenes_bytes:
        doc.add_page_break()
        titulo_anexo = doc.add_paragraph()
        titulo_anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        titulo_anexo.add_run("ANEXO DE IMÁGENES").bold = True
        
        # Crear tabla para la grilla de 4 columnas
        num_cols = 4
        num_rows = (len(imagenes_bytes) + num_cols - 1) // num_cols
        tabla = doc.add_table(rows=num_rows, cols=num_cols)
        
        for idx, img_data in enumerate(imagenes_bytes):
            row = idx // num_cols
            col = idx % num_cols
            celda = tabla.cell(row, col)
            parrafo_img = celda.paragraphs[0]
            run_img = parrafo_img.add_run()
            run_img.add_picture(io.BytesIO(img_data), width=Inches(1.5))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo and api_key:
    # Procesamiento del PDF (Texto e Imágenes)
    with st.spinner("Procesando reporte e imágenes..."):
        pdf = fitz.open(stream=archivo.read(), filetype="pdf")
        texto_acumulado = ""
        imagenes_extraidas = []
        
        for pagina in pdf:
            # Texto
            texto_acumulado += pagina.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) + "\n"
            # Imágenes
            for img in pagina.get_images(full=True):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                imagenes_extraidas.append(base_image["image"])
        pdf.close()

    if st.button("🚀 GENERAR INFORME"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. PASTORE. ANALIZA EL REPORTE DEL SONOSCAPE E3.
            Extrae valores (DDVI 61, FEy 31%, etc) y redacta el informe profesional.
            
            FORMATO REQUERIDO:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA:
            II. FUNCIÓN VENTRICULAR:
            III. EVALUACIÓN HEMODINÁMICA:
            IV. CONCLUSIÓN:
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO: {texto_acumulado}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            resultado = resp.choices[0].message.content
            st.markdown("### Vista Previa del Informe")
            st.write(resultado)
            
            # Generar el Word con el formato recuperado
            word_file = crear_word_profesional(resultado, imagenes_extraidas)
            
            st.download_button(
                label="📥 Descargar Word con Imágenes y Formato",
                data=word_file,
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
