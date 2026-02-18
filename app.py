
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN SONOSCAPE E3 ---
def extraer_datos_sonoscape(texto):
    datos = {k: "No evaluado" for k in ["fey", "ddvi", "dsvi", "sep", "par"]}
    
    # 1. El "Efecto Alicia": El valor 49.19 está en el bloque resultNo = 1
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey:
        datos["fey"] = match_fey.group(1)
    
    # 2. Búsqueda de medidas en mm (Anatomía)
    # Buscamos valores numéricos que tengan 'mm' como unidad
    medidas_mm = re.findall(r"value\s*=\s*([\d\.]+)\s*displayUnit\s*=\s*mm", texto)
    if len(medidas_mm) >= 2:
        datos["ddvi"] = medidas_mm[0]
        datos["dsvi"] = medidas_mm[1]
    if len(medidas_mm) >= 4:
        datos["sep"] = medidas_mm[2]
        datos["par"] = medidas_mm[3]
            
    return datos

# --- GENERADOR DE WORD CON IMÁGENES ---
def crear_word_final(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Encabezado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Texto de la IA
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.add_run(linea.replace("**", ""))

    # Firma
    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    # Procesar Imágenes del PDF
    if pdf_bytes:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            doc.add_page_break()
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, data in enumerate(imgs):
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    return doc

# --- INTERFAZ PRINCIPAL ---
st.title("❤️ CardioReport Pro v14")

# CARGADORES DE ARCHIVOS
u_txt = st.file_uploader("1. Subir ALBORNOZTEXT.txt", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])

# API KEY (Prioriza st.secrets, si no, pide entrada manual)
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Ingresar Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    v = extraer_datos_sonoscape(contenido)
    
    st.markdown("### Verificación de Datos")
    col1, col2, col3 = st.columns(3)
    with col1:
        fey_v = st.text_input("FEy (%)", v["fey"])
    with col2:
        ddvi_v = st.text_input("DDVI (mm)", v["ddvi"])
    with col3:
        sep_v = st.text_input("Septum (mm)", v["sep"])

    if st.button("🚀 GENERAR INFORME"):
        client = Groq(api_key=api_key)
        prompt = f"""
        ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE. Redacta el informe para ALICIA ALBORNOZ.
        DATOS: FEy: {fey_v}%, DDVI: {ddvi_v}mm, Septum: {sep_v}mm.
        ESTRUCTURA: I. Anatomía, II. Función (Indicar disfunción si FEy < 55%), III. Hemodinámica, IV. Conclusión.
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        texto_informe = res.choices[0].message.content
        st.info(texto_informe)
        
        # Generar y Descargar Word
        word_doc = crear_word_final(texto_informe, u_pdf.getvalue())
        target = io.BytesIO()
        word_doc.save(target)
        st.download_button("📥 Descargar Word con Imágenes", target.getvalue(), "Informe_Alicia.docx")
