
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de Interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_final(texto_informe, pdf_stream):
    doc = Document()
    
    # Estilo base: Arial 11
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # Título centrado
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    lineas = texto_informe.split('\n')
    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Lógica de Negritas y Prolijidad
        es_encabezado = any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"])
        
        if es_encabezado:
            p.add_run(linea).bold = True
            # Si es la conclusión o la firma, intentamos que no queden huérfanas
            if "IV." in linea.upper() or "FIRMA" in linea.upper():
                p.paragraph_format.keep_with_next = True
        else:
            p.add_run(linea)

    # El Anexo de imágenes SÍ debe ir siempre en hoja nueva por espacio
    doc.add_page_break()
    anexo = doc.add_paragraph()
    anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anexo.add_run("ANEXO DE IMÁGENES").bold = True
    
    # Extracción de imágenes
    pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
    imagenes = []
    for pagina in pdf_document:
        for img in pagina.get_images(full=True):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            imagenes.append(base_image["image"])
    
    # Grilla de 2 columnas
    num_cols = 2
    num_rows = (len(imagenes) + num_cols - 1) // num_cols
    tabla = doc.add_table(rows=num_rows, cols=num_cols)
    
    for idx, img_data in enumerate(imagenes):
        row = idx // num_cols
        col = idx % num_cols
        parrafo = tabla.cell(row, col).paragraphs[0]
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = parrafo.add_run()
        run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
    
    pdf_document.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo and api_key:
    archivo_bytes = archivo.getvalue()
    
    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            with st.spinner("Analizando datos médicos..."):
                pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
                texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
                pdf.close()

                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. PASTORE. EXTRAE LOS DATOS DEL SONOSCAPE E3.
                DATOS: DDVI 61, DSVI 46, Septum 10, Pared 11, AI 42, FEy 31%, FA 25, Hipocinesia global severa.
                
                ESTRUCTURA:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                TEXTO DEL PDF: {texto_pdf}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                informe_texto = resp.choices[0].message.content
                st.markdown("---")
                st.info(informe_texto)

                word_data = crear_word_final(informe_texto, archivo_bytes)
                
                st.download_button(
                    label="📥 Descargar Word",
                    data=word_data,
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
        except Exception as e:
            st.error(f"Error: {e}")
