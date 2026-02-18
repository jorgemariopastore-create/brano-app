
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN UNIVERSAL ---
def motor_v35_1(texto):
    info = {
        "paciente": "", 
        "edad": "74", 
        "peso": "56", 
        "altura": "152", 
        "fey": "", 
        "ddvi": "",
        "drao": "32",
        "ddai": "32"
    }
    if texto:
        n = re.search(r"(?:Patient Name|Name|Nombre|PACIENTE)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).replace(',', '').strip()
        f = re.search(r"(?:EF|FEy|Fracción de Eyección).*?([\d\.,]+)", texto, re.I)
        if f: info["fey"] = f.group(1).replace(',', '.')
        d = re.search(r"(?:LVIDd|DDVI).*?([\d\.,]+)", texto, re.I)
        if d: info["ddvi"] = d.group(1).replace(',', '.')
    return info

# --- 2. GENERADOR DE WORD ---
def crear_word_final(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Identificación
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    table.rows[0].cells[0].text = f"PACIENTE: {datos_v['paciente']}"
    table.rows[0].cells[1].text = f"EDAD: {datos_v['edad']} años"
    table.rows[0].cells[2].text = f"FECHA: 13/02/2026"
    table.rows[1].cells[0].text = f"PESO: {datos_v['peso']} kg"
    table.rows[1].cells[1].text = f"ALTURA: {datos_v['altura']} cm"
    try:
        bsa = ((float(datos_v['peso']) * float(datos_v['altura'])) / 3600)**0.5
        table.rows[1].cells[2].text = f"BSA: {bsa:.2f} m²"
    except: table.rows[1].cells[2].text = "BSA: --"

    doc.add_paragraph("\n")

    # Tabla Hallazgos
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Raíz Aórtica (DRAO)", f"{datos_v['drao']} mm"),
        ("Aurícula Izquierda (DDAI)", f"{datos_v['ddai']} mm"),
        ("Septum Interventricular", "11 mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_m.cell(i, 0).text = n
        table_m.cell(i, 1).text = v

    doc.add_paragraph("\n")

    # Texto del Informe
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('"', '')
        if not linea or "informe" in linea.lower(): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)

    # Firma
    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    # --- BLOQUE DE IMÁGENES (CORREGIDO) ---
    if pdf_bytes:
        doc.add_page_break()
        doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = []
        for page in pdf:
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                imgs.append(base_image["image"])
        
        if imgs:
            t_i = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, d in enumerate(imgs):
                cp = t_i.cell(i//2, i%2).paragraphs[0]
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp.add_run().add_picture(io.BytesIO(d), width=Inches(2.3))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro v35.1", layout="wide")
st.title("❤️ CardioReport Pro v35.1")

u_txt = st.file_uploader("1. Subir TXT/HTML del Ecógrafo", type=["txt", "html"])
u_pdf = st.file_uploader("2. Subir PDF con Capturas", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("3. Ingrese Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    raw_content = u_txt.read().decode("latin-1", errors="ignore")
    info_auto = motor_v35_1(raw_content)
    
    st.markdown("---")
    st.subheader("📝 Validar y Editar Datos")
    c1, c2, c3 = st.columns(3)
    with c1:
        nom_f = st.text_input("Paciente", info_auto["paciente"])
        pes_f = st.text_input("Peso", info_auto["peso"])
    with c2:
        eda_f = st.text_input("Edad", info_auto["edad"])
        alt_f = st.text_input("Altura", info_auto["altura"])
    with c3:
        fey_f = st.text_input("FEy (%)", info_auto["fey"])
        ddvi_f = st.text_input("DDVI (mm)", info_auto["ddvi"])

    if st.button("🚀 GENERAR INFORME CARDIOLÓGICO", type="primary"):
        client = Groq(api_key=api_key)
        prompt_medico = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta un
