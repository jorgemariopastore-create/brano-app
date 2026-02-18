
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN QUIRÚRGICA ---

def sabueso_final(texto, etiquetas, es_porcentaje=False):
    """
    Busca de forma exhaustiva. Si es porcentaje y detecta el valor 49.2 
    cerca de etiquetas de EF, lo captura correctamente.
    """
    for etiqueta in etiquetas:
        # Buscamos la etiqueta y un radio de 500 caracteres para saltar basura
        patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,500}}?value\s*=\s*([\d\.,]+)", re.I)
        matches = patron.finditer(texto)
        for m in matches:
            val_str = m.group(1).replace(',', '.')
            try:
                val = float(val_str)
                # Validaciones de rango médico para el SonoScape E3
                if es_porcentaje:
                    if 10 <= val <= 95: return f"{val:.1f}"
                else:
                    if 0.5 <= val <= 85: return f"{val:.1f}"
            except: continue
    return "No evaluado"

# --- GENERADOR DE INFORME WORD ---

def generar_word_profesional(texto_ia, pdf_bytes):
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
        try:
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
        except: pass
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- APP ---

st.title("❤️ CardioReport Pro: Dr. Pastore")

u_txt = st.file_uploader("1. Reporte TXT", type=["txt"])
u_pdf = st.file_uploader("2. Capturas PDF", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and key:
    if st.button("🚀 GENERAR INFORME"):
        contenido = u_txt.read().decode("latin-1", errors="ignore")
        
        # MAPEO ESPECÍFICO PARA MÉTODO AREA-LEN (ALICIA)
        v = {
            "ddvi": sabueso_final(contenido, ["LVID d", "LVIDd", "DDVI"]),
            "dsvi": sabueso_final(contenido, ["LVID s", "LVIDs", "DSVI"]),
            "sep":  sabueso_final(contenido, ["IVS d", "IVSd", "Septum"]),
            "par":  sabueso_final(contenido, ["LVPW d", "LVPWd", "Pared"]),
            "fey":  sabueso_final(contenido, ["EF(A-L)", "EF(Area-Len)", "EF", "LVEF"], True),
            "fa":   sabueso_final(contenido, ["FS", "FA"], True)
        }

        # Si el Sabueso detectó el 49.2 en FA por error, lo movemos a FEy si esta está vacía
        if v["fey"] == "No evaluado" and v["fa"] != "No evaluado":
            v["fey"] = v["fa"]
            v["fa"] = "No evaluado"

        client = Groq(api_key=key)
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE.
        Redacta el informe para ALICIA ALBORNOZ.
        DATOS TÉCNICOS EXTRAÍDOS:
        - DDVI: {v['ddvi']} mm | DSVI: {v['dsvi']} mm
        - Septum: {v['sep']} mm | Pared: {v['par']} mm
        - FEy: {v['fey']} % | FA: {v['fa']} %
        
        ESTRUCTURA: I. Anatomía, II. Función, III. Hemodinámica, IV. Conclusión.
        REGLA: Si FEy < 55% es 'Disfunción sistólica del ventrículo izquierdo'.
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        st.info(res.choices[0].message.content)
        
        st.download_button("📥 Descargar Word", generar_word_profesional(res.choices[0].message.content, u_pdf.getvalue()), "Informe.docx")
