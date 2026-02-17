
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches

# 1. Configuración de Interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_con_imagenes(texto_informe, pdf_stream):
    doc = Document()
    # Título simple
    doc.add_paragraph("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    
    # Agregar el texto del informe
    for linea in texto_informe.split('\n'):
        doc.add_paragraph(linea.strip())

    # Procesar imágenes directamente para el Word (evita error de memoria)
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES")
    
    pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
    imagenes = []
    for pagina in pdf_document:
        for img in pagina.get_images(full=True):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            imagenes.append(base_image["image"])
    
    # Grilla de imágenes de a 4
    num_cols = 4
    num_rows = (len(imagenes) + num_cols - 1) // num_cols
    tabla = doc.add_table(rows=num_rows, cols=num_cols)
    
    for idx, img_data in enumerate(imagenes):
        row = idx // num_cols
        col = idx % num_cols
        parrafo = tabla.cell(row, col).paragraphs[0]
        run = parrafo.add_run()
        run.add_picture(io.BytesIO(img_data), width=Inches(1.5))
    
    pdf_document.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo and api_key:
    # Leemos el contenido del archivo una sola vez
    archivo_bytes = archivo.read()
    
    if st.button("🚀 GENERAR INFORME E IMÁGENES"):
        try:
            # 2. Extracción de texto para la IA (Modo que funcionó para Manuel)
            pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
            texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
            pdf.close()

            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. PASTORE. EXTRAE LOS DATOS DEL SONOSCAPE E3.
            IMPORTANTE: Busca DDVI (61), FEy (31%), FA (25), Hipocinesia global severa.
            
            ESTRUCTURA:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA:
            II. FUNCIÓN VENTRICULAR:
            III. EVALUACIÓN HEMODINÁMICA:
            IV. CONCLUSIÓN:
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO: {texto_pdf}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            informe_texto = resp.choices[0].message.content
            st.write(informe_texto)

            # 3. Generación del Word (incluye las imágenes)
            word_data = crear_word_con_imagenes(informe_texto, archivo_bytes)
            
            st.download_button(
                label="📥 Descargar Word con Imágenes",
                data=word_data,
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
