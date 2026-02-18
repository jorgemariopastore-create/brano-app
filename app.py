
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN DE ALTA PRECISIÓN ---

class SonoscapeEngine:
    @staticmethod
    def parse_biometry(text):
        # Mapeo exhaustivo basado en el TXT de Alicia y Silvia
        mapping = {
            'ddvi': ['LVIDd', 'LVID(d)', 'DDVI', 'Diastolic LVID'],
            'dsvi': ['LVIDs', 'LVID(s)', 'DSVI', 'Systolic LVID'],
            'septum': ['IVSd', 'IVS(d)', 'DDSIV', 'Septum'],
            'pared': ['LVPWd', 'LVPW(d)', 'DDPP', 'Pared'],
            'fey': ['EF', 'EF(Teich)', 'LVEF', 'FEy'],
            'fa': ['FS', 'FS(Teich)', 'FA', 'Fractional Shortening']
        }
        
        results = {k: "No evaluado" for k in mapping.keys()}
        
        # Separamos por bloques de medición para evitar cruces
        blocks = text.split('[MEASUREMENT]')
        
        for block in blocks:
            # Extraer ítem y valor del bloque actual
            item_match = re.search(r'item\s*=\s*([^\r\n]+)', block, re.I)
            val_match = re.search(r'value\s*=\s*([\d\.,]+)', block, re.I)
            
            if item_match and val_match:
                found_tag = item_match.group(1).strip()
                val_str = val_match.group(1).replace(',', '.')
                
                for key_internal, tags_list in mapping.items():
                    if any(t.lower() == found_tag.lower() for t in tags_list):
                        try:
                            val_f = float(val_str)
                            # Filtro de seguridad médica: evita capturar IDs o fechas
                            if (key_internal in ['fey', 'fa'] and 10 < val_f < 95) or \
                               (key_internal not in ['fey', 'fa'] and 0.5 < val_f < 80):
                                results[key_internal] = f"{val_f:.1f}"
                        except: continue
        return results

# --- GENERADOR DE DOCUMENTOS ---

def build_word_report(ia_text, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)

    # Encabezado centrado
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Cuerpo del informe (Limpieza de frases de error de la IA)
    for line in ia_text.split('\n'):
        line = line.strip()
        if not line or "proporcionan" in line.lower(): continue
        p = doc.add_paragraph()
        if any(h in line.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(line.replace("**", "")).bold = True
        else:
            p.add_run(line.replace("**", ""))

    # Firma Dr. Pastore
    doc.add_paragraph("\n")
    signature = doc.add_paragraph()
    signature.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    # Anexo de Imágenes
    if pdf_bytes:
        doc.add_page_break()
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            doc.add_paragraph("ANEXO DE IMÁGENES").alignment = WD_ALIGN_PARAGRAPH.CENTER
            table = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, img_data in enumerate(imgs):
                cell_p = table.cell(i//2, i%2).paragraphs[0]
                cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell_p.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf.close()

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- INTERFAZ STREAMLIT ---

st.set_page_config(page_title="CardioReport Senior v6", layout="centered")
st.title("❤️ Generador de Informes Médicos")

u_txt = st.file_uploader("1. Subir TXT del Ecógrafo", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF de Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            raw_content = u_txt.read().decode("latin-1", errors="ignore")
            
            # Paso 1: Extracción Técnica (Código Python Puro)
            data_tech = SonoscapeEngine.parse_biometry(raw_content)
            
            # Paso 2: Redacción con IA
            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta el informe para ALICIA ALBORNOZ.
            DATOS TÉCNICOS DETECTADOS (ÚSALOS SÍ O SÍ):
            DDVI: {data_tech['ddvi']} mm, DSVI: {data_tech['dsvi']} mm, 
            Septum: {data_tech['septum']} mm, Pared: {data_tech['pared']} mm,
            FEy: {data_tech['fey']} %, FA: {data_tech['fa']} %.
            
            TEXTO ORIGINAL PARA ANTECEDENTES: {raw_content[:2000]}
            
            FORMATO: I. ANATÓMICA, II. FUNCIÓN, III. HEMODINÁMICA, IV. CONCLUSIÓN.
            REGLA MÉDICA: Si FEy >= 55% -> Función conservada.
            """
            
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
            final_txt = chat.choices[0].message.content
            st.info(final_txt)
            
            st.download_button("📥 Descargar Informe Oficial", build_word_report(final_txt, u_pdf.getvalue()), f"Informe_{u_txt.name}.docx")
            
        except Exception as e:
            st.error(f"Error de sistema: {e}")
