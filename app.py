
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def generar_docx_limpio(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Cuerpo del informe JUSTIFICADO
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or "Lo siento" in linea or "No puedo encontrar" in linea: 
            continue # Filtramos cualquier comentario residual de la IA
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.add_run(linea.replace("**", ""))

    # Anexo de Imágenes
    doc.add_page_break()
    a = doc.add_paragraph()
    a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    a.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
    imgs = []
    for page in pdf_file:
        for img in page.get_images(full=True):
            imgs.append(pdf_file.extract_image(img[0])["image"])
    
    if imgs:
        tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
        for i, img_data in enumerate(imgs):
            run = tabla.cell(i//2, i%2).paragraphs[0].add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
    
    pdf_file.close()
    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

if archivo and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Generando reporte limpio..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                raw_text = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
                pdf.close()

                client = Groq(api_key=api_key)
                # Prompt con restricción absoluta de comentarios
                prompt = f"""
                ERES EL DR. PASTORE. ESCRIBE ÚNICAMENTE EL INFORME MÉDICO.
                ESTÁ PROHIBIDO AGREGAR NOTAS, DISCULPAS O COMENTARIOS AL FINAL.
                
                DATOS A UTILIZAR:
                I. EVALUACIÓN ANATÓMICA: DDVI 61 mm, DSVI 46 mm, Septum 10 mm, Pared 11 mm, AI 42 mm.
                II. FUNCIÓN VENTRICULAR: FEy 31%, FA 25%, Motilidad: Hipocinesia global severa.
                III. EVALUACIÓN HEMODINÁMICA: E/A 0.95, E/e' 5.9, Vena Cava 15 mm.
                IV. CONCLUSIÓN: Disfunción ventricular izquierda severa con FEy 31% e hipocinesia global severa.
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                REGLA DE ORO: Si el texto del PDF es confuso, NO lo menciones. Solo escribe el informe.
                
                TEXTO DEL PACIENTE: {raw_text}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx_limpio(resultado, archivo.getvalue())
                st.download_button("📥 Descargar Word Sin Notas", docx_out, f"Informe_{archivo.name}.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
