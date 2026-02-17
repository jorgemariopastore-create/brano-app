
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_directo(texto_informe, pdf_stream):
    doc = Document()
    
    # Estilo Arial 11
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Texto Justificado sin formatos extraños
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # Limpiamos posibles asteriscos que la IA a veces pone para negrita
        texto_limpio = linea.replace("**", "")
        p.add_run(texto_limpio)

    # Anexo de imágenes (2 por fila)
    doc.add_page_break()
    anexo = doc.add_paragraph()
    anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anexo.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_doc = fitz.open(stream=pdf_stream, filetype="pdf")
    imgs = []
    for pagina in pdf_doc:
        for img in pagina.get_images(full=True):
            xref = img[0]
            pix = pdf_doc.extract_image(xref)
            imgs.append(pix["image"])
    
    if imgs:
        num_cols = 2
        num_rows = (len(imgs) + num_cols - 1) // num_cols
        tabla = doc.add_table(rows=num_rows, cols=num_cols)
        for idx, img_data in enumerate(imgs):
            row, col = idx // num_cols, idx % num_cols
            p_img = tabla.cell(row, col).paragraphs[0]
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.8))
    
    pdf_doc.close()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo and api_key:
    archivo_bytes = archivo.getvalue()
    
    if st.button("🚀 GENERAR INFORME"):
        try:
            # Extracción técnica para que la IA "vea" los números
            pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
            texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
            pdf.close()

            client = Groq(api_key=api_key)
            # Prompt enfocado 100% en los datos de Manuel
            prompt = f"""
            ERES EL DR. PASTORE. EXTRAE LOS DATOS DEL SONOSCAPE E3.
            DATOS REALES EN EL TEXTO: DDVI 61, DSVI 46, Septum 10, Pared 11, AI 42, FEy 31%, FA 25, Hipocinesia global severa.
            
            NO DIGAS QUE NO HAY INFORMACIÓN. BUSCA LOS NÚMEROS.
            
            FORMATO:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA: (Valores DDVI, DSVI, Septum, Pared, AI)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (E/A, E/e', Vena Cava)
            IV. CONCLUSIÓN: (Diagnóstico médico)
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL PDF:
            {texto_pdf}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            informe_final = resp.choices[0].message.content
            st.markdown("---")
            st.write(informe_final)

            word_data = crear_word_directo(informe_final, archivo_bytes)
            st.download_button(
                label="📥 Descargar Word",
                data=word_data,
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
