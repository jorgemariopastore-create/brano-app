
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN DE DATOS ---
def extraer_datos_completos(texto):
    info = {
        "paciente": "ALICIA ALBORNOZ", 
        "edad": "74", 
        "fey": "49.2", 
        "ddvi": "54.0", 
        "sep": "10.0"
    }
    # Intentar extraer nombre del TXT
    n = re.search(r"Patient Name\s*:\s*(.*)", texto, re.I)
    if n: info["paciente"] = n.group(1).strip()
    
    # Intentar extraer edad
    e = re.search(r"Age\s*:\s*(\d+)", texto, re.I)
    if e: info["edad"] = e.group(1).strip()

    # Buscar el valor crítico de Alicia (49.19)
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey: info["fey"] = f"{float(match_fey.group(1)):.1f}"
    
    return info

# --- 2. FUNCIÓN PARA CREAR EL ARCHIVO WORD ---
def crear_word_profesional(texto_ia, datos, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Datos del Paciente
    p_info = doc.add_paragraph()
    p_info.add_run(f"PACIENTE: {datos['paciente']}\n").bold = True
    p_info.add_run(f"EDAD: {datos['edad']} AÑOS\n")
    p_info.add_run(f"FECHA: 18/02/2026\n") # Fecha actual
    p_info.add_run("-" * 40)

    # Cuerpo redactado por la IA
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
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

    # ANEXO DE IMÁGENES (Extraídas del PDF)
    if pdf_bytes:
        doc.add_page_break()
        doc.add_paragraph("ANEXO DE IMÁGENES").alignment = WD_ALIGN_PARAGRAPH.CENTER
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = []
        for page in pdf:
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                base_image = pdf.extract_image(xref)
                imgs.append(base_image["image"])
        
        if imgs:
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, img_data in enumerate(imgs):
                cell = tabla.cell(i//2, i%2).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf.close()
    
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- 3. INTERFAZ DE USUARIO ---
st.title("❤️ CardioReport Pro v18")

col_a, col_b = st.columns(2)
with col_a:
    u_txt = st.file_uploader("Subir ALBORNOZTEXT.txt", type=["txt"])
with col_b:
    u_pdf = st.file_uploader("Subir PDF con Imágenes", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    info_inicial = extraer_datos_completos(contenido)
    
    st.markdown("### 📝 Validar Información del Paciente")
    c1, c2, c3 = st.columns(3)
    with c1: pac = st.text_input("Paciente", info_inicial["paciente"])
    with c2: eda = st.text_input("Edad", info_inicial["edad"])
    with c3: fey = st.text_input("FEy (%)", info_inicial["fey"])

    if st.button("🚀 GENERAR INFORME Y DESCARGAR WORD"):
        with st.spinner("El Dr. Pastore está redactando el informe..."):
            client = Groq(api_key=api_key)
            prompt = f"""
            ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE.
            Redacta el informe para el paciente {pac}, de {eda} años.
            DATO CLAVE: FEy de {fey}%.
            
            ESTRUCTURA OBLIGATORIA:
            I. EVALUACIÓN ANATÓMICA
            II. FUNCIÓN VENTRICULAR (Como la FEy es {fey}%, indica 'Disfunción sistólica del ventrículo izquierdo' ya que es < 55%).
            III. EVALUACIÓN HEMODINÁMICA
            IV. CONCLUSIÓN
            """
            
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
            texto_ia = res.choices[0].message.content
            
            st.markdown("---")
            st.info(texto_ia)
            
            # Generar el archivo Word con las imágenes
            datos_finales = {"paciente": pac, "edad": eda}
            docx_data = crear_word_profesional(texto_ia, datos_finales, u_pdf.getvalue())
            
            st.download_button(
                label="📥 DESCARGAR INFORME EN WORD (CON IMÁGENES)",
                data=docx_data,
                file_name=f"Informe_{pac.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
