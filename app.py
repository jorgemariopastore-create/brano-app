
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup # Para manejar HTML si decides subirlo

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

col1, col2 = st.columns(2)
with col1:
    # Ahora aceptamos también HTML
    archivo_datos = st.file_uploader("1. Reporte de Datos (TXT, DOCX o HTML)", type=["txt", "docx", "html"])
with col2:
    archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

def procesar_archivo_datos(archivo):
    """Detecta el tipo de archivo y extrae el texto limpiamente."""
    if archivo.name.endswith('.docx'):
        return docx2txt.process(archivo)
    elif archivo.name.endswith('.html'):
        # Si es HTML, quitamos las etiquetas para dejar solo el texto
        soup = BeautifulSoup(archivo.read().decode("latin-1", errors="ignore"), "html.parser")
        return soup.get_text(separator=' ')
    else:
        return archivo.read().decode("latin-1", errors="ignore")

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
        if not linea or any(x in linea.lower() for x in ["lo siento", "nota:", "asumiendo", "proporciona"]):
            continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS DEL PACIENTE", "I.", "II.", "III.", "IV.", "FIRMA"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    if pdf_bytes:
        doc.add_page_break()
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in pdf_file:
            for img in page.get_images(full=True):
                img_data = pdf_file.extract_image(img[0])["image"]
                doc.add_picture(io.BytesIO(img_data), width=Inches(4.5))
        pdf_file.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            with st.spinner("Escaneando reporte del paciente..."):
                texto_crudo = procesar_archivo_datos(archivo_datos)
                
                client = Groq(api_key=api_key)
                
                # El Prompt ahora es más inteligente para buscar los datos del paciente específico
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE.
                Extrae con precisión los datos de este estudio ecocardiográfico.
                
                DATOS DEL PACIENTE: Busca Nombre, Edad, Peso y Altura.
                
                VALORES TÉCNICOS:
                - DDVI: búscalo como LVIDd.
                - DSVI: búscalo como LVIDs.
                - Septum e Inferolateral: búscalo como IVSd y LVPWd.
                - FEy: búscalo como EF o Fracción de eyección.
                
                REGLAS:
                1. No inventes datos. Si no encuentras algo, no lo menciones.
                2. Si la FEy es >= 55%: Conclusión "Función ventricular izquierda conservada".
                3. Usa un tono médico profesional.
                
                TEXTO DEL ESTUDIO:
                {texto_crudo[:20000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx_profesional(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Informe en Word", docx_out, "Informe_Medico.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
