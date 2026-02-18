
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

# 1. Subida de ambos archivos
col1, col2 = st.columns(2)
with col1:
    archivo_txt = st.file_uploader("📂 Subir reporte TXT/HTML (Datos)", type=["txt", "html", "docx"])
with col2:
    archivo_pdf = st.file_uploader("📂 Subir reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

def generar_docx(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or any(x in linea.lower() for x in ["lo siento", "no se proporciona"]): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Anexo de Imágenes desde el PDF
    if pdf_bytes:
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

if archivo_txt and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME PERFECTO"):
        try:
            with st.spinner("Cruzando datos de texto con imágenes del PDF..."):
                # Leemos el archivo de texto (que es súper preciso)
                contenido_datos = archivo_txt.read().decode("latin-1") 

                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. PASTORE. USA ESTE REPORTE DE MEDICIONES (TEXTO) PARA REDACTAR EL INFORME.
                
                DATOS CLAVE A BUSCAR:
                - PatientName, Weight, Height.
                - DDVI, DSVI, LVPWd (Pared), IVSd (Septum).
                - EF (FEy), FS (FA).
                
                LÓGICA:
                - Si EF es >= 55%: Conclusión "Función ventricular conservada".
                
                REPORTE DE ORIGEN:
                {contenido_datos}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Informe Perfecto", docx_out, f"Informe_{archivo_txt.name}.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
