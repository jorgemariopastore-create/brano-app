
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN DE DATOS PERSONALES Y TÉCNICOS ---
def extraer_todo(texto):
    info = {
        "paciente": "No detectado",
        "edad": "No detectada",
        "fecha": "No detectada",
        "fey": "49.2", "ddvi": "50.0", "sep": "10.0"
    }
    
    # Datos Personales (Patrones típicos de SonoScape)
    n = re.search(r"Patient Name\s*:\s*(.*)", texto, re.I)
    if n: info["paciente"] = n.group(1).strip()
    
    e = re.search(r"Age\s*:\s*(\d+)", texto, re.I)
    if e: info["edad"] = e.group(1).strip()
    
    # Datos Técnicos (Alicia)
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey: info["fey"] = f"{float(match_fey.group(1)):.1f}"
    
    return info

# --- FUNCIÓN DE WORD (CORREGIDA) ---
def generar_docx(texto_ia, paciente_info, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Encabezado Médico
    tit = doc.add_paragraph()
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tit.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Bloque de Datos del Paciente
    p_info = doc.add_paragraph()
    p_info.add_run(f"PACIENTE: {paciente_info['paciente']}\n").bold = True
    p_info.add_run(f"EDAD: {paciente_info['edad']} años\n")
    p_info.add_run("-" * 30)

    # Cuerpo del Informe
    for linea in texto_ia.split('\n'):
        if not linea.strip(): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma
    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    # Anexo de Imágenes
    if pdf_bytes:
        doc.add_page_break()
        doc.add_paragraph("ANEXO DE IMÁGENES").alignment = WD_ALIGN_PARAGRAPH.CENTER
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, data in enumerate(imgs):
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf.close()
    
    return doc

# --- INTERFAZ STREAMLIT ---
st.title("❤️ CardioReport Pro v17")

u_txt = st.file_uploader("1. Cargar Reporte TXT", type=["txt"])
u_pdf = st.file_uploader("2. Cargar PDF con Capturas", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Ingresar Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    info = extraer_todo(contenido)
    
    st.subheader("📝 Validar Información")
    c1, c2, c3 = st.columns(3)
    with c1: nom = st.text_input("Paciente", info["paciente"])
    with c2: ed = st.text_input("Edad", info["edad"])
    with c3: fy = st.text_input("FEy (%)", info["fey"])

    if st.button("🚀 GENERAR INFORME Y WORD"):
        client = Groq(api_key=api_key)
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta el informe para {nom}, de {ed} años.
        DATOS: FEy {fy}%. 
        INSTRUCCIONES: Formato profesional (I a IV). Si FEy < 55% indicar disfunción.
        """
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        texto_ia = res.choices[0].message.content
        
        st.markdown("---")
        st.info(texto_ia)
        
        # Generación del archivo Word
        doc_final = generar_docx(texto_ia, {"paciente": nom, "edad": ed}, u_pdf.getvalue())
        buffer = io.BytesIO()
        doc_final.save(buffer)
        
        st.download_button(
            label="📥 DESCARGAR INFORME EN WORD (CON IMÁGENES)",
            data=buffer.getvalue(),
            file_name=f"Informe_{nom.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
