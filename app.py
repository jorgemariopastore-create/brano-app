
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN AVANZADA (MODO SABUESO) ---

def extraer_dato_final(texto, posibles_nombres, es_fey=False):
    """
    Busca el valor numérico recorriendo todos los bloques de medición.
    Diseñado específicamente para las variaciones de Alicia (Area-Len, Simpson, etc.)
    """
    # Buscamos cada nombre posible
    for nombre in posibles_nombres:
        # Escaneamos el texto buscando el nombre y el primer 'value =' que no sea asteriscos
        # El patrón busca el nombre y luego el número más cercano hasta 400 caracteres después
        patron = re.compile(rf"{re.escape(nombre)}[\s\S]{{0,400}}?value\s*=\s*([\d\.,]+)", re.I)
        matches = patron.finditer(texto)
        for m in matches:
            val_str = m.group(1).replace(',', '.')
            try:
                val = float(val_str)
                # Filtros de lógica médica para evitar IDs o fechas
                if es_fey:
                    if 15 <= val <= 95: return f"{val:.1f}"
                else:
                    if 0.5 <= val <= 85: return f"{val:.1f}"
            except:
                continue
    return "No evaluado"

def generar_word_oficial(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)

    # Encabezado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Cuerpo del informe
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea or "proporcionan" in linea.lower(): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

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
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, data in enumerate(imgs):
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- INTERFAZ ---

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")

u_txt = st.file_uploader("1. Subir TXT (Datos del Ecógrafo)", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF (Imágenes)", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            content = u_txt.read().decode("latin-1", errors="ignore")
            
            # EXTRACCIÓN QUIRÚRGICA (Ajustada para Alicia y Silvia)
            res = {
                "ddvi": extraer_dato_final(content, ["LVID d", "LVIDd", "DDVI", "LVID(d)"]),
                "dsvi": extraer_dato_final(content, ["LVID s", "LVIDs", "DSVI", "LVID(s)"]),
                "sep": extraer_dato_final(content, ["IVS d", "IVSd", "DDSIV", "IVS(d)"]),
                "par": extraer_dato_final(content, ["LVPW d", "LVPWd", "DDPP", "LVPW(d)"]),
                "fey": extraer_dato_final(content, ["EF", "LVEF", "EF(Teich)", "FEy"], True),
                "fa": extraer_dato_final(content, ["FS", "FS(Teich)", "FA"], True)
            }

            client = Groq(api_key=key)
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE.
            Redacta el informe médico para ALICIA ALBORNOZ usando estos datos:
            VALORES OBLIGATORIOS:
            - DDVI: {res['ddvi']} mm
            - DSVI: {res['dsvi']} mm
            - Septum: {res['sep']} mm
            - Pared: {res['par']} mm
            - FEy: {res['fey']} %
            - FA: {res['fa']} %
            
            Busca nombre y edad aquí: {content[:1500]}
            
            FORMATO: I. ANATOMÍA, II. FUNCIÓN, III. HEMODINÁMICA, IV. CONCLUSIÓN.
            IMPORTANTE: Si los mm están arriba, ÚSALOS. No digas 'No se evaluaron'.
            Si FEy < 55%: 'Disfunción ventricular izquierda'.
            """
            
            resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
            st.info(resp.choices[0].message.content)
            
            st.download_button("📥 Descargar Word", generar_word_oficial(resp.choices[0].message.content, u_pdf.getvalue()), "Informe.docx")
            
        except Exception as e:
            st.error(f"Error técnico: {e}")
