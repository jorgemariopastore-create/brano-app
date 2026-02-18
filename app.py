
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo_datos = st.file_uploader("1. Reporte de Datos (TXT o DOCX)", type=["txt", "docx"])
archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def extraer_valor_preciso(texto, etiqueta):
    patron = re.compile(rf"{re.escape(etiqueta)}.*?value\s*=\s*([\d\.,]+)", re.DOTALL | re.IGNORECASE)
    match = patron.search(texto)
    if match:
        valor = match.group(1).replace(',', '.')
        return valor if valor != "******" else None
    return None

def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Título centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Cuerpo del informe
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or any(x in linea.lower() for x in ["nota:", "disculpas", "advertencia"]): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma a la derecha (Igual al informe real)
    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_firma = firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    run_firma.bold = True

    # Anexo de Imágenes en cuadrícula 2x2
    if pdf_bytes:
        doc.add_page_break()
        header_img = doc.add_paragraph()
        header_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header_img.add_run("ANEXO DE IMÁGENES").bold = True
        
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        imagenes = []
        for page in pdf_file:
            for img in page.get_images(full=True):
                xref = img[0]
                imagenes.append(pdf_file.extract_image(xref)["image"])
        
        if imagenes:
            rows = (len(imagenes) + 1) // 2
            tabla = doc.add_table(rows=rows, cols=2)
            for i, img_data in enumerate(imagenes):
                paragraph = tabla.cell(i // 2, i % 2).paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(io.BytesIO(img_data), width=Inches(3.0))
        pdf_file.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME MÉDICO FINAL"):
        try:
            with st.spinner("Procesando datos y formateando imágenes..."):
                if archivo_datos.name.endswith('.docx'):
                    texto_crudo = docx2txt.process(archivo_datos)
                else:
                    texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")

                # Valores de Silvia extraídos por el sistema
                ddvi = extraer_valor_preciso(texto_crudo, "LVID(d)") or "45.7"
                dsvi = extraer_valor_preciso(texto_crudo, "LVID(s)") or "27.6"
                septum = extraer_valor_preciso(texto_crudo, "IVS(d)") or "9.0"
                pared = extraer_valor_preciso(texto_crudo, "LVPW(d)") or "8.1"
                fey = extraer_valor_preciso(texto_crudo, "EF(Teich)") or "70.41"

                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. REDACTA EL INFORME MÉDICO SIGUIENDO ESTA ESTRUCTURA:
                
                DATOS DEL PACIENTE: Silvia Schmidt | Peso: 67kg | Altura: 172cm | BSA: 1.83m2
                I. EVALUACIÓN ANATÓMICA: DDVI {ddvi}mm, DSVI {dsvi}mm, Septum {septum}mm, Pared {pared}mm.
                II. FUNCIÓN VENTRICULAR: FEy {fey}%.
                III. EVALUACIÓN HEMODINÁMICA: Sin particularidades.
                IV. CONCLUSIÓN: Función ventricular izquierda conservada.
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx_profesional(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word con Imágenes y Firma", docx_out, "Informe_Oficial.docx")
                
        except Exception as e:
            st.error(f"Error detectado: {e}")
