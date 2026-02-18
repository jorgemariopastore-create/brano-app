
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. EXTRACCIÓN SIMPLE (LO QUE SIEMPRE FUNCIONÓ) ---

def buscar_valor(texto, etiquetas):
    for etiqueta in etiquetas:
        # Busca la etiqueta y captura el primer número que NO sean asteriscos
        patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,300}}?value\s*=\s*([\d\.,]+)", re.I)
        match = patron.search(texto)
        if match:
            valor = match.group(1).replace(',', '.')
            try:
                if 0.5 <= float(valor) <= 95: # Filtro básico de rango
                    return valor
            except: continue
    return "No evaluado"

# --- 2. GENERADOR DE WORD ---

def crear_word(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    if pdf_bytes:
        doc.add_page_break()
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, data in enumerate(imgs):
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    return doc

# --- 3. APP PRINCIPAL ---

st.title("❤️ CardioReport Pro")

u_txt = st.file_uploader("1. TXT del Ecógrafo", type=["txt"])
u_pdf = st.file_uploader("2. PDF de Imágenes", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and key:
    if st.button("🚀 GENERAR INFORME"):
        raw = u_txt.read().decode("latin-1", errors="ignore")
        
        # Extraemos los valores de Alicia/Silvia con las etiquetas que ya conocemos
        v = {
            "ddvi": buscar_valor(raw, ["LVID d", "LVID(d)", "LVIDd"]),
            "dsvi": buscar_valor(raw, ["LVID s", "LVID(s)", "LVIDs"]),
            "sep": buscar_valor(raw, ["IVS d", "IVS(d)", "IVSd"]),
            "par": buscar_valor(raw, ["LVPW d", "LVPW(d)", "LVPWd"]),
            "fey": buscar_valor(raw, ["EF", "EF(Teich)", "LVEF"]),
            "fa": buscar_valor(raw, ["FS", "FS(Teich)", "FA"])
        }

        # Prompt ultra-directo
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE. Escribe el informe para ALICIA ALBORNOZ.
        DATOS: DDVI: {v['ddvi']}mm, DSVI: {v['dsvi']}mm, Septum: {v['sep']}mm, Pared: {v['par']}mm, FEy: {v['fey']}%, FA: {v['fa']}%.
        ESTRUCTURA: I. Anatomía, II. Función, III. Hemodinámica, IV. Conclusión (Si FEy < 55% es disfunción).
        """
        
        client = Groq(api_key=key)
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        st.info(res.choices[0].message.content)
        
        buf = io.BytesIO()
        crear_word(res.choices[0].message.content, u_pdf.getvalue()).save(buf)
        st.download_button("📥 Descargar Word", buf.getvalue(), "Informe.docx")
