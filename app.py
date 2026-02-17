
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

def crear_word_simple(texto_informe, pdf_stream):
    doc = Document()
    
    # Estilo base
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Texto del informe (Justificado)
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # Limpiar marcas de formato que a veces pone la IA
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
            base_image = pdf_document.extract_image(xref)
            imagenes.append(base_image["image"])
    
    if imagenes:
        num_cols = 2
        num_rows = (len(imagenes) + num_cols - 1) // num_cols
        tabla = doc.add_table(rows=num_rows, cols=num_cols)
        for idx, img_data in enumerate(imagenes):
            row, col = idx // num_cols, idx % num_cols
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
    
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Procesando datos médicos..."):
                pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
                # Lectura espacial para no perder datos Doppler
                texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
                pdf.close()

                client = Groq(api_key=api_key)
                # Prompt directo y autoritario sobre los datos
                prompt = f"""
                ERES EL DR. PASTORE. EXTRAE LOS DATOS DEL PDF. 
                LOS VALORES ESTÁN EN EL TEXTO, NO LOS IGNORES:
                
                DDVI: 61, DSVI: 46, Septum: 10, Pared: 11, AI: 42.
                FEy: 31%, FA: 25%, Motilidad: Hipocinesia global severa.
                HEMODINAMIA (DEBES INCLUIR): E/A: 0.95, E/e': 5.9, Vena Cava: 15 mm.

                FORMATO:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                
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

                word_data = crear_word_simple(informe_texto, archivo_bytes)
                st.download_button(
                    label="📥 Descargar Word",
                    data=word_data,
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
        except Exception as e:
            st.error(f"Error: {e}")
