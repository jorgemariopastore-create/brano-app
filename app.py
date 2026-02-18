
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. EXTRACCIÓN DE DATOS ---
def motor_v35(texto):
    info = {"paciente": "", "edad": "74", "peso": "56", "altura": "152", "fey": "68", "ddvi": "40"}
    n = re.search(r"(?:Name|Nombre|PACIENTE)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
    if n: info["paciente"] = n.group(1).replace(',', '').strip()
    return info

# --- 2. GENERADOR DE WORD ---
def crear_word_v35(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Encabezado centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Datos
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

    # Cuadro de Mediciones (Estilo PDF Real)
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Raíz Aórtica (DRAO)", "32 mm"),
        ("Aurícula Izquierda (DDAI)", "32 mm"),
        ("Septum Interventricular", "11 mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_m.cell(i, 0).text = n
        table_m.cell(i, 1).text = v

    doc.add_paragraph("\n")

    # Cuerpo del Informe (Sin comillas, estilo directo)
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

    # Imágenes
    if pdf_bytes:
        doc.add_page_break()
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
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
st.title("❤️ CardioReport Pro v35")

u_txt = st.file_uploader("1. Reporte del Ecógrafo", type=["txt", "html"])
u_pdf = st.file_uploader("2. PDF para Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    info = motor_v35(raw)
    
    st.subheader("📝 Revisión de Datos")
    c1, c2, c3 = st.columns(3)
    with c1:
        nom_f = st.text_input("Paciente", info["paciente"])
        fey_f = st.text_input("FEy (%)", info["fey"])
    with c2:
        eda_f = st.text_input("Edad", "74")
        ddvi_f = st.text_input("DDVI (mm)", info["ddvi"])
    with c3:
        pes_f = st.text_input("Peso (kg)", "56")
        alt_f = st.text_input("Altura (cm)", "152")

    if st.button("🚀 GENERAR INFORME FINAL"):
        client = Groq(api_key=api_key)
        # PROMPT DE IMITACIÓN ESTRICTA
        prompt = f"""
        ERES EL DR. PASTORE. Escribe el informe médico. 
        REGLA DE ORO: Usa solo frases técnicas y secas. SIN ADORNOS. SIN COMILLAS.
        
        I. ANATOMÍA: Raíz aórtica y aurícula izquierda de diámetros normales. Cavidades ventriculares de dimensiones y espesores parietales normales.
        II. FUNCIÓN VENTRICULAR: Función sistólica del VI conservada. FEy {fey_f}%. Fracción de acortamiento normal. 
        III. VÁLVULAS Y DOPPLER: Ecoestructura y movilidad valvular normal. Apertura y cierre conservado. Flujos laminares sin reflujos patológicos.
        IV. CONCLUSIÓN: Estudio dentro de parámetros normales para la edad.
        """
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        reporte = res.choices[0].message.content
        st.info(reporte)
        archivo = crear_word_v35(reporte, {"paciente": nom_f, "edad": eda_f, "peso": pes_f, "altura": alt_f, "fey": fey_f, "ddvi": ddvi_f}, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR WORD", archivo, f"Informe_{nom_f}.docx")
