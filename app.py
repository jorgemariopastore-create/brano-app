
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
    # Busca la etiqueta y el valor numérico siguiente, sin importar el desorden
    patron = re.compile(rf"{re.escape(etiqueta)}.*?value\s*=\s*([\d\.,]+)", re.DOTALL | re.IGNORECASE)
    match = patron.search(texto)
    if match:
        valor = match.group(1).replace(',', '.')
        return valor if valor != "******" else "No evaluado"
    return "No evaluado"

def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or any(x in linea.lower() for x in ["nota:", "disculpas", "advertencia"]): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_firma = firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    run_firma.bold = True

    if pdf_bytes:
        doc.add_page_break()
        header_img = doc.add_paragraph()
        header_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header_img.add_run("ANEXO DE IMÁGENES").bold = True
        
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        imagenes = []
        for page in pdf_file:
            for img in page.get_images(full=True):
                imagenes.append(pdf_file.extract_image(img[0])["image"])
        
        if imagenes:
            rows = (len(imagenes) + 1) // 2
            tabla = doc.add_table(rows=rows, cols=2)
            for i, img_data in enumerate(imagenes):
                paragraph = tabla.cell(i // 2, i % 2).paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf_file.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Escaneando datos del nuevo paciente..."):
                if archivo_datos.name.endswith('.docx'):
                    texto_crudo = docx2txt.process(archivo_datos)
                else:
                    texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")

                # EXTRACCIÓN DINÁMICA (Sin valores fijos de respaldo)
                ddvi = extraer_valor_preciso(texto_crudo, "LVID(d)")
                dsvi = extraer_valor_preciso(texto_crudo, "LVID(s)")
                septum = extraer_valor_preciso(texto_crudo, "IVS(d)")
                pared = extraer_valor_preciso(texto_crudo, "LVPW(d)")
                fey = extraer_valor_preciso(texto_crudo, "EF(Teich)")
                fa = extraer_valor_preciso(texto_crudo, "FS(Teich)")

                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. 
                Extrae el Nombre, Edad, Peso y Altura del bloque [PATINET INFO] del texto abajo.
                Usa estos valores técnicos detectados:
                DDVI: {ddvi} mm, DSVI: {dsvi} mm, Septum: {septum} mm, Pared: {pared} mm, FEy: {fey} %, FA: {fa} %.

                ESTRUCTURA DEL INFORME:
                DATOS DEL PACIENTE: (Nombre, Edad, Peso, Altura)
                I. EVALUACIÓN ANATÓMICA
                II. FUNCIÓN VENTRICULAR
                III. EVALUACIÓN HEMODINÁMICA
                IV. CONCLUSIÓN (Si FEy >= 55%: Función conservada)
                
                TEXTO CRUDO DEL EQUIPO:
                {texto_crudo[:15000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx_profesional(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Informe", docx_out, f"Informe_{archivo_datos.name}.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
