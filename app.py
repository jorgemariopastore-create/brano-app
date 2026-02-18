
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. LÓGICA DEL SABUESO (EXTRACCIÓN DE ALTA PRECISIÓN) ---

def sabueso_parser_final(texto_sucio, etiquetas):
    """
    Busca la etiqueta y captura el primer valor numérico real.
    Ajustado específicamente para el archivo ALBORNOZTEXT.txt
    """
    for etiqueta in etiquetas:
        # Buscamos la etiqueta y luego el patrón 'value = ' ignorando los asteriscos
        # El archivo de Alicia usa nombres como 'LVID d', 'LVID s', 'IVS d'
        patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,500}}?value\s*=\s*([\d\.,]+)", re.I)
        match = patron.search(texto_sucio)
        
        if match:
            valor_str = match.group(1).replace(',', '.')
            try:
                valor = float(valor_str)
                # Filtros de rango lógico médico para el SonoScape E3
                if any(x in etiqueta.upper() for x in ["EF", "FS", "FE", "FA"]):
                    if 10 <= valor <= 95: return f"{valor:.1f}"
                else:
                    if 0.5 <= valor <= 80: return f"{valor:.1f}"
            except:
                continue
    return "No evaluado"

# --- 2. GENERADOR DE WORD ---

def generar_word_pastore(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea or "proporcionan" in linea.lower(): continue
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
                cell_p = tabla.cell(i//2, i%2).paragraphs[0]
                cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell_p.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. APLICACIÓN PRINCIPAL ---

st.title("❤️ CardioReport Pro: Dr. Pastore")

u_txt = st.file_uploader("1. Cargar TXT", type=["txt"])
u_pdf = st.file_uploader("2. Cargar PDF", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        contenido = u_txt.read().decode("latin-1", errors="ignore")
        
        # EXTRACCIÓN CON ETIQUETAS EXACTAS DE ALICIA
        v = {
            "ddvi": sabueso_parser_final(contenido, ["LVID d", "LVIDd", "DDVI"]),
            "dsvi": sabueso_parser_final(contenido, ["LVID s", "LVIDs", "DSVI"]),
            "sep": sabueso_parser_final(contenido, ["IVS d", "IVSd", "Septum"]),
            "par": sabueso_parser_final(contenido, ["LVPW d", "LVPWd", "Pared"]),
            "fey": sabueso_parser_final(contenido, ["EF", "FEy", "LVEF"]),
            "fa": sabueso_parser_final(contenido, ["FS", "FA"])
        }

        client = Groq(api_key=api_key)
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta el informe para ALICIA ALBORNOZ.
        USA ESTOS VALORES (Python los extrajo del TXT):
        DDVI: {v['ddvi']} mm | DSVI: {v['dsvi']} mm | Septum: {v['sep']} mm | Pared: {v['par']} mm.
        FEy: {v['fey']} % | FA: {v['fa']} %.
        
        ESTRUCTURA: I. Anatomía, II. Función, III. Hemodinámica, IV. Conclusión.
        REGLA: Si FEy < 55% indica 'Disfunción sistólica del ventrículo izquierdo'.
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        st.info(res.choices[0].message.content)
        
        st.download_button("📥 Descargar Word", generar_word_pastore(res.choices[0].message.content, u_pdf.getvalue()), "Informe.docx")
