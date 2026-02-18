
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN DE ALTA PRECISIÓN (ESPECÍFICO SONOSCAPE) ---

def extraer_valor_sonoscape(texto, etiquetas, es_porcentaje=False):
    """
    Busca el valor numérico real. 
    En el archivo de Alicia, los datos aparecen después de 'value ='.
    """
    for etiqueta in etiquetas:
        # Buscamos el bloque donde aparece la etiqueta y luego el primer 'value =' que tenga números
        # Este patrón es mucho más agresivo para saltar los '******'
        patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,500}}?value\s*=\s*([\d\.,]+)", re.I)
        matches = patron.finditer(texto)
        for m in matches:
            val_str = m.group(1).replace(',', '.')
            try:
                val = float(val_str)
                # Filtros lógicos para no capturar fechas o IDs
                if es_porcentaje:
                    if 15 <= val <= 95: return f"{val:.1f}"
                else:
                    if 0.5 <= val <= 85: return f"{val:.1f}"
            except:
                continue
    return "No evaluado"

# --- GENERACIÓN DE INFORME ---

def crear_docx(texto_ia, pdf_bytes):
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
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- INTERFAZ ---

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Generador de Informes Médicos")

u_txt = st.file_uploader("1. Subir TXT (Datos)", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF (Imágenes)", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            content = u_txt.read().decode("latin-1", errors="ignore")
            
            # Extracción quirúrgica de datos
            datos = {
                "ddvi": extraer_valor_sonoscape(content, ["LVIDd", "LVID(d)", "DDVI"]),
                "dsvi": extraer_valor_sonoscape(content, ["LVIDs", "LVID(s)", "DSVI"]),
                "sep": extraer_valor_sonoscape(content, ["IVSd", "IVS(d)", "DDSIV"]),
                "par": extraer_valor_sonoscape(content, ["LVPWd", "LVPW(d)", "DDPP"]),
                "fey": extraer_valor_sonoscape(content, ["EF", "EF(Teich)", "LVEF"], True),
                "fa": extraer_valor_sonoscape(content, ["FS", "FS(Teich)", "FA"], True)
            }

            client = Groq(api_key=key)
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE.
            Redacta el informe médico para la paciente ALICIA ALBORNOZ basándote en:
            DDVI: {datos['ddvi']} mm, DSVI: {datos['dsvi']} mm, Septum: {datos['sep']} mm, Pared: {datos['par']} mm.
            FEy: {datos['fey']} %, FA: {datos['fa']} %.
            
            Usa el texto para nombre y edad: {content[:1500]}
            
            ESTRUCTURA: DATOS PACIENTE, I. ANATOMÍA, II. FUNCIÓN, III. HEMODINÁMICA, IV. CONCLUSIÓN.
            IMPORTANTE: No digas 'No evaluado' si el número está presente arriba.
            Si FEy >= 55%: 'Función ventricular izquierda conservada'.
            """
            
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
            st.info(res.choices[0].message.content)
            
            st.download_button("📥 Descargar Word", crear_docx(res.choices[0].message.content, u_pdf.getvalue()), "Informe.docx")
            
        except Exception as e:
            st.error(f"Error: {e}")
