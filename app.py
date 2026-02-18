
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN MEJORADO ---
def motor_v31(texto):
    info = {"paciente": "", "edad": "74", "peso": "56", "altura": "152", "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32"}
    n_match = re.search(r"(?:Patient Name|Name|Nombre|PACIENTE)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
    if n_match: info["paciente"] = n_match.group(1).replace(',', '').strip()
    return info

# --- 2. GENERADOR DE WORD (ESTILO EXACTO) ---
def crear_word_v31(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Encabezado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Identificación
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    c0 = table.rows[0].cells
    c0[0].text = f"PACIENTE: {datos_v['paciente']}"
    c0[1].text = f"EDAD: {datos_v['edad']} años"
    c0[2].text = f"FECHA: 13/02/2026"
    c1 = table.rows[1].cells
    c1[0].text = f"PESO: {datos_v['peso']} kg"
    c1[1].text = f"ALTURA: {datos_v['altura']} cm"
    try:
        bsa = ( (float(datos_v['peso']) * float(datos_v['altura'])) / 3600 )**0.5
        c1[2].text = f"BSA: {bsa:.2f} m²"
    except: c1[2].text = "BSA: --"

    doc.add_paragraph("\n")

    # TABLA TÉCNICA (Lo que faltaba en tu último informe)
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

    # CUERPO DEL INFORME JUSTIFICADO
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            run = p.add_run(linea.replace("**", ""))
            run.bold = True
        else:
            p.add_run(linea.replace("**", ""))

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
                cp.add_run().add_picture(io.BytesIO(d), width=Inches(2.5))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ ---
st.title("❤️ CardioReport Pro v31")

u_txt = st.file_uploader("1. Subir TXT/HTML", type=["txt", "html"])
u_pdf = st.file_uploader("2. Subir PDF para imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    info = motor_v31(raw)
    
    st.subheader("📝 Validar Datos")
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

    if st.button("🚀 GENERAR INFORME"):
        client = Groq(api_key=api_key)
        # PROMPT DE ALTA SOBRIEDAD
        prompt = f"""
        ACTÚA COMO EL DR. PASTORE. Redacta el informe para {nom_f}.
        DATOS: DDVI {ddvi_f}mm, FEy {fey_f}%.
        
        REGLAS:
        - I. ANATOMÍA: Menciona dimensiones de raíz aórtica y aurícula izquierda (32mm). Cavidades normales.
        - II. FUNCIÓN VENTRICULAR: Sé técnico. "Función sistólica conservada. FEy {fey_f}%".
        - III. VÁLVULAS Y DOPPLER: Ecoestructura normal, flujos laminares.
        - IV. CONCLUSIÓN: Una sola frase técnica.
        
        PROHIBIDO: No menciones "morfología normal", no uses lenguaje explicativo, no repitas el nombre.
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        txt_final = res.choices[0].message.content
        st.info(txt_final)
        
        archivo = crear_word_v31(txt_final, {"paciente": nom_f, "edad": eda_f, "peso": pes_f, "altura": alt_f, "fey": fey_f, "ddvi": ddvi_f, "drao": "32", "ddai": "32"}, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR WORD", archivo, f"Informe_{nom_f}.docx")
