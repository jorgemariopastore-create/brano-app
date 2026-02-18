
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

col1, col2 = st.columns(2)
with col1:
    archivo_datos = st.file_uploader("1. Reporte de Datos (TXT, DOCX o HTML)", type=["txt", "docx", "html"])
with col2:
    archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

def procesar_archivo_datos(archivo):
    if archivo.name.endswith('.docx'):
        return docx2txt.process(archivo)
    elif archivo.name.endswith('.html'):
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
        # Filtro de seguridad para eliminar cualquier residuo de comentarios de la IA
        if not linea or any(x in linea.lower() for x in ["importante tener en cuenta", "nota:", "descargo", "interpretación", "proporcionado"]):
            continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS DEL PACIENTE", "I.", "II.", "III.", "IV.", "CONCLUSIÓN", "FIRMA"]):
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
    if st.button("🚀 GENERAR INFORME ESTRUCTURADO"):
        try:
            with st.spinner("Generando informe médico oficial..."):
                texto_crudo = procesar_archivo_datos(archivo_datos)
                
                client = Groq(api_key=api_key)
                
                # PROMPT REDISEÑADO: MODO TRANSCRIPCIÓN MÉDICA ESTRICTA
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. TU ÚNICA FUNCIÓN ES TRANSCRIPCIÓN MÉDICA.
                
                INSTRUCCIONES DE FORMATO:
                1. NO incluyas introducciones ni despedidas.
                2. NO incluyas notas aclaratorias, advertencias ni comentarios sobre la calidad de los datos.
                3. Usa EXCLUSIVAMENTE los encabezados romanos (I, II, III, IV).
                
                BÚSQUEDA DE DATOS (REGLAS):
                - DATOS DEL PACIENTE: Extrae Nombre, Edad, Peso, Altura y BSA.
                - I. EVALUACIÓN ANATÓMICA: Busca LVIDd (DDVI), LVIDs (DSVI), IVSd (Septum), LVPWd (Pared).
                - II. FUNCIÓN VENTRICULAR: Busca EF (FEy) y FS (FA). Si hay varios, usa el valor de 'scanMode = M'.
                - III. EVALUACIÓN HEMODINÁMICA: Busca valores de Doppler (E/A, E/e', Vena Cava).
                - IV. CONCLUSIÓN: Si FEy >= 55%: "Función ventricular izquierda conservada".
                
                ESTRUCTURA OBLIGATORIA:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                TEXTO TÉCNICO:
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
                st.download_button("📥 Descargar Word Oficial", docx_out, "Informe_Cardio.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
