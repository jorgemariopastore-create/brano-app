
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

def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    for linea in texto.split('\n'):
        linea = linea.strip()
        # Filtro estricto para que no pasen disculpas de la IA al documento
        if not linea or any(x in linea.lower() for x in ["lo siento", "no puedo", "falta de información", "proporcionado"]):
            continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if any(h in linea.upper() for h in ["DATOS DEL PACIENTE", "I.", "II.", "III.", "IV.", "FIRMA:"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

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
            with st.spinner("Analizando minuciosamente las tablas de Alicia..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                texto_pdf = ""
                for pagina in pdf:
                    # CLAVE: preservamos los espacios para que la IA vea la tabla como tal
                    texto_pdf += pagina.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) + "\n"
                pdf.close()

                client = Groq(api_key=api_key)
                
                # Prompt con instrucciones de búsqueda forzada
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES EXTRAER LOS DATOS DEL ESTUDIO.
                
                ATENCIÓN: Los datos de ALICIA ALBORNOZ están en formato de tabla. Búscalos así:
                - DDVI: busca el número cerca de 'DDVI' (debería ser 40).
                - FEy (EF): busca el porcentaje (debería ser 67%).
                - Hemodinamia: busca E/A (0.77) y E/e' (5.6).

                REGLA DE ORO: No digas que faltan datos. Si ves un número cerca de una sigla, úsalo.
                
                ESTRUCTURA OBLIGATORIA:
                DATOS DEL PACIENTE: (Nombre, ID, Peso, Altura, BSA)
                I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, Septum, Pared, AI)
                II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad: Normal)
                III. EVALUACIÓN HEMODINÁMICA: (E/A, E/e', Vena Cava)
                IV. CONCLUSIÓN: (Basada en los hallazgos. Si la FEy es 67%, la función es CONSERVADA).
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                TEXTO DEL PDF:
                {texto_pdf}
                """

                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx_profesional(resultado, archivo.getvalue())
                st.download_button("📥 Descargar Informe Alicia Corregido", docx_out, f"Informe_{archivo.name}.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
