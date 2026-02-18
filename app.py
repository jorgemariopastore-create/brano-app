
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN DINÁMICO ---
def motor_universal(texto):
    info = {
        "paciente": "No detectado", "edad": "", 
        "peso": "70", "altura": "170", 
        "fey": "55", "ddvi": "50", "sep": "10", "par": "10"
    }
    if texto:
        n = re.search(r"Patient Name\s*:\s*(.*)", texto, re.I)
        if n: info["paciente"] = n.group(1).strip()
        e = re.search(r"Age\s*:\s*(\d+)", texto, re.I)
        if e: info["edad"] = e.group(1).strip()
        p = re.search(r"Weight\s*:\s*([\d\.]+)", texto, re.I)
        if p: info["peso"] = p.group(1)
        a = re.search(r"Height\s*:\s*([\d\.]+)", texto, re.I)
        if a: info["altura"] = a.group(1)
        f = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.,]+)", texto, re.DOTALL)
        if f: info["fey"] = f.group(1).replace(',', '.')
    return info

# --- 2. GENERADOR DE WORD (TEXTO JUSTIFICADO Y LIMPIO) ---
def crear_word_profesional(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Datos
    table_adm = doc.add_table(rows=2, cols=3)
    table_adm.style = 'Table Grid'
    c0 = table_adm.rows[0].cells
    c0[0].text = f"PACIENTE: {datos_v['paciente']}"
    c0[1].text = f"EDAD: {datos_v['edad']} años"
    c0[2].text = f"FECHA: 18/02/2026"
    c1 = table_adm.rows[1].cells
    c1[0].text = f"PESO: {datos_v['peso']} kg"
    c1[1].text = f"ALTURA: {datos_v['altura']} cm"
    try:
        bsa = ( (float(datos_v['peso']) * float(datos_v['altura'])) / 3600 )**0.5
        c1[2].text = f"BSA: {bsa:.2f} m²"
    except: c1[2].text = "BSA: --"

    doc.add_paragraph("\n")

    # Tabla Técnica
    doc.add_paragraph("MEDICIONES ECOCARDIOGRÁFICAS").bold = True
    table_med = doc.add_table(rows=4, cols=2)
    table_med.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Espesor de Septum (IVS)", f"{datos_v['sep']} mm"),
        ("Espesor de Pared Posterior (PW)", f"{datos_v['par']} mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_med.cell(i, 0).text = n
        table_med.cell(i, 1).text = v

    doc.add_paragraph("\n")

    # Texto de la IA - JUSTIFICADO
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # <--- JUSTIFICACIÓN
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma
    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo\nMN 74144").bold = True

    # Anexo de Imágenes
    if pdf_bytes:
        doc.add_page_break()
        doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            t_img = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, data in enumerate(imgs):
                cp = t_img.cell(i//2, i%2).paragraphs[0]
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ ---
st.title("❤️ CardioReport Pro v25")

u_txt = st.file_uploader("1. Subir Reporte TXT", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    texto_sucio = u_txt.read().decode("latin-1", errors="ignore")
    info_auto = motor_universal(texto_sucio)
    
    st.subheader("📝 Validar Datos")
    c1, c2, c3 = st.columns(3)
    with c1:
        nom_f = st.text_input("Paciente", info_auto["paciente"])
        pes_f = st.text_input("Peso (kg)", info_auto["peso"])
    with c2:
        eda_f = st.text_input("Edad", info_auto["edad"])
        alt_f = st.text_input("Altura (cm)", info_auto["altura"])
    with c3:
        fey_f = st.text_input("FEy (%)", info_auto["fey"])
        ddvi_f = st.text_input("DDVI (mm)", info_auto["ddvi"])
    
    if st.button("🚀 GENERAR INFORME MÉDICO", type="primary"):
        client = Groq(api_key=api_key)
        # PROMPT RESTRINGIDO PARA EVITAR RECOMENDACIONES Y CAPÍTULOS EXTRAS
        prompt_medico = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta el informe para {nom_f}.
        DATOS: FEy {fey_f}%, DDVI {ddvi_f}mm.
        
        REGLAS ESTRICTAS:
        1. Solo secciones I. ANATOMÍA, II. FUNCIÓN, III. HEMODINÁMICA y IV. CONCLUSIÓN.
        2. NO incluyas sección de 'Recomendaciones' ni ningún capítulo final adicional.
        3. El informe debe ser puramente descriptivo y técnico.
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt_medico}], temperature=0)
        texto_final = res.choices[0].message.content
        st.info(texto_final)
        
        word_bin = crear_word_profesional(texto_final, {"paciente": nom_f, "edad": eda_f, "peso": pes_f, "altura": alt_f, "fey": fey_f, "ddvi": ddvi_f, "sep": info_auto["sep"], "par": info_auto["par"]}, u_pdf.getvalue())
        
        st.download_button("📥 DESCARGAR INFORME EN WORD", word_bin, f"Informe_{nom_f}.docx")
