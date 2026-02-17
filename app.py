
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
        if not linea or any(x in linea.lower() for x in ["lo siento", "no se proporcionan", "falta de información"]):
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
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
            with st.spinner("Analizando minuciosamente los datos de las tablas..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                # EXTRAER TEXTO DE FORMA BRUTA Y POR BLOQUES
                texto_pdf = ""
                for pagina in pdf:
                    texto_pdf += pagina.get_text("blocks") # Usamos blocks para no perder estructura de tablas
                pdf.close()

                client = Groq(api_key=api_key)
                # PROMPT DE EXTRACCIÓN AGRESIVA
                prompt = f"""
                ERES UN EXPERTO EN EXTRACCIÓN DE DATOS DE ECOCARDIOGRAMA (SONOSCAPE E3).
                TU TRABAJO ES SER EL DR. PASTORE Y REDACTAR EL INFORME.
                
                DAME LOS DATOS QUE ESTÁN EN LAS TABLAS DEL SIGUIENTE TEXTO.
                SI VES VALORES COMO '40 mm', '25 mm', '67%', ÚSALOS.
                
                ESTRUCTURA DEL INFORME (OBLIGATORIA):
                DATOS DEL PACIENTE: (Nombre, ID, Peso, Altura, BSA)
                I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, Septum, Pared, AI)
                II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad)
                III. EVALUACIÓN HEMODINÁMICA: (E/A, E/e', Vena Cava)
                IV. CONCLUSIÓN: (Redacta una conclusión médica según la FEy encontrada)
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                REGLA: ESTÁ PROHIBIDO DECIR "NO SE PROPORCIONAN DATOS". 
                BUSCA EN CADA RINCÓN DEL TEXTO.
                
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
                
                docx_out = generar_docx(resultado, archivo.getvalue())
                st.download_button("📥 Descargar Word", docx_out, f"Informe_{archivo.name}.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
