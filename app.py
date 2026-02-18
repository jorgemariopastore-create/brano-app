
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. BUSCADOR DE VALORES (LA BASE QUE FUNCIONA) ---

def extraer_valor(texto, etiquetas):
    for etiqueta in etiquetas:
        # Buscamos la etiqueta y el primer valor numérico que aparezca después
        # Aumentamos el rango de búsqueda para saltar asteriscos
        patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,400}}?value\s*=\s*([\d\.,]+)", re.I)
        match = patron.search(texto)
        if match:
            valor = match.group(1).replace(',', '.')
            try:
                # Si es un número lógico (ni fecha ni ID), lo devolvemos
                if 0.5 <= float(valor) <= 95:
                    return valor
            except: continue
    return "No evaluado"

# --- 2. GENERADOR DE WORD (ESTILO DR. PASTORE) ---

def generar_informe_docx(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)

    # Título Profesional
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Cuerpo (Limpia notas de la IA)
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea or "proporcionan" in linea.lower(): continue
        para = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            para.add_run(linea.replace("**", "")).bold = True
        else:
            para.add_run(linea.replace("**", ""))

    # Firma
    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    # Imágenes
    if pdf_bytes:
        doc.add_page_break()
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            doc.add_paragraph("ANEXO DE IMÁGENES").alignment = WD_ALIGN_PARAGRAPH.CENTER
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, img_data in enumerate(imgs):
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. APLICACIÓN ---

st.set_page_config(page_title="CardioReport Pro")
st.title("❤️ Generador de Informes Médicos")

archivo_txt = st.file_uploader("1. TXT de Alicia o Silvia", type=["txt"])
archivo_pdf = st.file_uploader("2. PDF con Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if archivo_txt and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        # Leemos el archivo
        contenido = archivo_txt.read().decode("latin-1", errors="ignore")
        
        # Extracción directa (Volviendo a lo que funcionó)
        datos = {
            "ddvi": extraer_valor(contenido, ["LVID d", "LVIDd", "DDVI", "LVID(d)"]),
            "dsvi": extraer_valor(contenido, ["LVID s", "LVIDs", "DSVI", "LVID(s)"]),
            "sep": extraer_valor(contenido, ["IVS d", "IVSd", "Septum", "IVS(d)"]),
            "par": extraer_valor(contenido, ["LVPW d", "LVPWd", "Pared", "LVPW(d)"]),
            "fey": extraer_valor(contenido, ["EF", "FEy", "LVEF", "EF(Teich)"]),
            "fa": extraer_valor(contenido, ["FS", "FA", "FS(Teich)"])
        }

        # Prompt de IA (Corto y al pie)
        prompt = f"""
        ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE.
        Redacta el informe para ALICIA ALBORNOZ. 
        VALORES: DDVI: {datos['ddvi']}mm, DSVI: {datos['dsvi']}mm, Septum: {datos['sep']}mm, Pared: {datos['par']}mm, FEy: {datos['fey']}%, FA: {datos['fa']}%.
        
        ESTRUCTURA: I. Anatomía, II. Función, III. Hemodinámica (Sin particularidades), IV. Conclusión.
        REGLA: Si FEy < 55% indicar disfunción. NO digas que no hay datos si el número está presente.
        """
        
        client = Groq(api_key=api_key)
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        resultado = res.choices[0].message.content
        st.info(resultado)
        
        st.download_button("📥 Descargar Word", generar_informe_docx(resultado, archivo_pdf.getvalue()), "Informe_Pastore.docx")
