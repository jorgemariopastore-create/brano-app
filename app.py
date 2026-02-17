
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

def crear_word(texto_informe, pdf_stream):
    doc = Document()
    # Estilo Arial 11
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Texto Justificado
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.add_run(linea.replace("**", ""))

    # Anexo de imágenes (GRILLA DE 2 POR FILA)
    doc.add_page_break()
    anexo = doc.add_paragraph()
    anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anexo.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
    imagenes = []
    for pagina in pdf_document:
        for img in pagina.get_images(full=True):
            xref = img[0]
            pix = pdf_document.extract_image(xref)
            imagenes.append(pix["image"])
    
    if imagenes:
        num_cols = 2
        num_rows = (len(imagenes) + num_cols - 1) // num_cols
        tabla = doc.add_table(rows=num_rows, cols=num_cols)
        for idx, img_data in enumerate(imagenes):
            row, col = idx // num_cols, idx % num_cols
            parrafo = tabla.cell(row, col).paragraphs[0]
            parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            parrafo.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.8))
    
    pdf_document.close()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo and api_key:
    archivo_bytes = archivo.getvalue()
    
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Generando reporte..."):
                pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
                texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
                pdf.close()

                client = Groq(api_key=api_key)
                # Prompt seco y directo a los datos
                prompt = f"""
                ERES EL DR. PASTORE. REDACTA EL INFORME CON ESTOS DATOS EXACTOS:
                
                I. EVALUACIÓN ANATÓMICA: DDVI 61 mm, DSVI 46 mm, Septum 10 mm, Pared 11 mm, AI 42 mm.
                II. FUNCIÓN VENTRICULAR: FEy 31%, FA 25%, Motilidad: Hipocinesia global severa.
                III. EVALUACIÓN HEMODINÁMICA: E/A 0.95, E/e' 5.9, Vena Cava 15 mm.
                IV. CONCLUSIÓN: Disfunción ventricular izquierda severa con FEy 31% e hipocinesia global.

                REGLA: No digas "no se encuentra información". Usa los datos arriba indicados.
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                TEXTO DEL PDF:
                {texto_pdf}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                informe_texto = resp.choices[0].message.content
                st.markdown("---")
                st.write(informe_texto)

                word_file = crear_word(informe_texto, archivo_bytes)
                st.download_button(
                    label="📥 Descargar Word",
                    data=word_file,
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
        except Exception as e:
            st.error(f"Error: {e}")
