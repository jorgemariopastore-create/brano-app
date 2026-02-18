
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de la interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo_datos = st.file_uploader("1. Reporte de Datos (TXT o DOCX)", type=["txt", "docx"])
archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])
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
        if not linea or any(x in linea.lower() for x in ["nota:", "importante", "descargo"]): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "FIRMA"]):
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
    if st.button("🚀 GENERAR INFORME SIN ERRORES"):
        try:
            with st.spinner("Escaneando parámetros técnicos de Silvia Schmidt..."):
                if archivo_datos.name.endswith('.docx'):
                    texto_crudo = docx2txt.process(archivo_datos)
                else:
                    texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")

                client = Groq(api_key=api_key)
                
                # PROMPT DE EXTRACCIÓN AGRESIVA
                prompt = f"""
                ERES EL DR. PASTORE. USA ESTA GUÍA DE TRADUCCIÓN PARA EL ARCHIVO TXT:
                - LVIDd o LVID(d) es el DDVI.
                - LVIDs o LVID(s) es el DSVI.
                - IVSd es el Septum.
                - LVPWd es la Pared Posterior.
                - EF o EF(Teich) es la FEy.
                - FS es la FA.
                - E/A y E/E' están en la sección Doppler.

                TAREAS:
                1. Extrae Nombre, Edad, Peso, Altura del inicio ([PATINET INFO]).
                2. Busca los valores numéricos de las siglas mencionadas arriba. 
                3. Si el valor es '******', di 'No evaluado'. Si hay un número, ÚSALO.
                4. CONCLUSIÓN: Si FEy >= 55%, "Función ventricular conservada".

                PROHIBIDO: No digas "No disponible" si el número está en el texto. No pongas notas finales.
                
                ESTRUCTURA:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144

                TEXTO TÉCNICO:
                {texto_crudo}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word", docx_out, "Informe_Final.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
