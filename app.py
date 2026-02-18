
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN MEJORADO ---
def motor_precision_v27(texto):
    info = {"paciente": "", "edad": "74", "peso": "70", "altura": "170", "fey": "49.2", "ddvi": "50"}
    
    # Búsqueda de nombre más agresiva (busca patrones comunes de ecógrafos)
    n_match = re.search(r"(?:Patient Name|Name|Nombre)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
    if n_match: 
        info["paciente"] = n_match.group(1).replace(',', '').strip()
    
    # Búsqueda de FEy (Fracción de Eyección)
    f_match = re.search(r"value\s*=\s*([\d\.,]+)\s*displayUnit\s*=\s*%", texto)
    if f_match:
        info["fey"] = f_match.group(1).replace(',', '.')
    
    return info

# --- 2. GENERADOR DE WORD (ESTILO PASTORE JUSTIFICADO) ---
def crear_word_v27(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Datos
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    c0 = table.rows[0].cells
    c0[0].text = f"PACIENTE: {datos_v['paciente']}"
    c0[1].text = f"EDAD: {datos_v['edad']} años"
    c0[2].text = f"FECHA: 18/02/2026"
    c1 = table.rows[1].cells
    c1[0].text = f"PESO: {datos_v['peso']} kg"
    c1[1].text = f"ALTURA: {datos_v['altura']} cm"
    try:
        bsa = ( (float(datos_v['peso']) * float(datos_v['altura'])) / 3600 )**0.5
        c1[2].text = f"BSA: {bsa:.2f} m²"
    except: c1[2].text = "BSA: --"

    doc.add_paragraph("\n")
    
    # Tabla de Mediciones
    doc.add_paragraph("MEDICIONES TÉCNICAS").bold = True
    table_m = doc.add_table(rows=4, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Espesor de Septum (IVS)", "10 mm"),
        ("Espesor de Pared Posterior (PW)", "10 mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_m.cell(i, 0).text = n
        table_m.cell(i, 1).text = v

    doc.add_paragraph("\n")

    # Texto Justificado
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
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
st.title("❤️ CardioReport Pro v27")

u_txt = st.file_uploader("1. Subir TXT/HTML", type=["txt", "html"])
u_pdf = st.file_uploader("2. Subir PDF con Capturas", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    info = motor_precision_v27(raw)
    
    st.subheader("📝 Validación de Datos")
    # AVISO SI EL NOMBRE ESTÁ VACÍO
    if not info["paciente"]:
        st.warning("⚠️ No se detectó el nombre. Por favor, escríbalo debajo.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        nom_f = st.text_input("Paciente", info["paciente"])
        pes_f = st.text_input("Peso (kg)", info["peso"])
    with c2:
        eda_f = st.text_input("Edad", info["edad"])
        alt_f = st.text_input("Altura (cm)", info["altura"])
    with c3:
        fey_f = st.text_input("FEy (%)", info["fey"])
        ddvi_f = st.text_input("DDVI (mm)", info["ddvi"])

    if st.button("🚀 GENERAR INFORME CARDIOLÓGICO"):
        client = Groq(api_key=api_key)
        # PROMPT DE ALTA PRECISIÓN
        prompt = f"""
        ERES EL DR. PASTORE, CARDIÓLOGO. Redacta informe de eco para {nom_f}.
        DATOS: FEy {fey_f}%, DDVI {ddvi_f}mm.
        
        CRITERIO MÉDICO:
        - Si FEy >= 55%: Función sistólica conservada (Normal).
        - Si FEy < 55%: Disfunción sistólica leve.
        
        ESTRUCTURA: I. Anatomía, II. Función, III. Hemodinámica, IV. Conclusión.
        Sin recomendaciones. Texto profesional y directo.
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        txt_final = res.choices[0].message.content
        st.info(txt_final)
        
        word = crear_word_v27(txt_final, {"paciente": nom_f, "edad": eda_f, "peso": pes_f, "altura": alt_f, "fey": fey_f, "ddvi": ddvi_f}, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR INFORME", word, f"Informe_{nom_f}.docx")
