
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN ---
def extraer_datos_completos(texto):
    info = {"paciente": "ALICIA ALBORNOZ", "edad": "74", "peso": "56.0", "altura": "152", "fey": "49.2"}
    n = re.search(r"Patient Name\s*:\s*(.*)", texto, re.I)
    if n: info["paciente"] = n.group(1).strip()
    e = re.search(r"Age\s*:\s*(\d+)", texto, re.I)
    if e: info["edad"] = e.group(1).strip()
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey: info["fey"] = f"{float(match_fey.group(1)):.1f}"
    return info

# --- GENERADOR DE WORD (ESTILO CONSULTORIO) ---
def crear_word_final(texto_ia, datos, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Encabezado formal
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    cells0 = table.rows[0].cells
    cells0[0].text = f"PACIENTE: {datos['paciente']}"
    cells0[1].text = f"EDAD: {datos['edad']} años"
    cells0[2].text = f"FECHA: 18/02/2026"
    cells1 = table.rows[1].cells
    cells1[0].text = f"PESO: {datos['peso']} kg"
    cells1[1].text = f"ALTURA: {datos['altura']} cm"
    bsa = ( (float(datos['peso']) * float(datos['altura'])) / 3600 )**0.5
    cells1[2].text = f"BSA: {bsa:.2f} m²"

    doc.add_paragraph("\n")

    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            run = p.add_run(linea.replace("**", ""))
            run.bold = True
            run.font.size = Pt(11)
        else:
            p.add_run(linea.replace("**", ""))

    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo\nMN 74144").bold = True

    if pdf_bytes:
        doc.add_page_break()
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

# --- UI ---
st.title("❤️ CardioReport Pro v20")

u_txt = st.file_uploader("1. Subir ALBORNOZTEXT.txt", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    info = extraer_datos_completos(contenido)
    
    st.markdown("### 📝 Datos a Validar")
    c1, c2, c3 = st.columns(3)
    with c1: 
        pac = st.text_input("Paciente", info["paciente"])
        pes = st.text_input("Peso (kg)", info["peso"])
    with c2: 
        eda = st.text_input("Edad", info["edad"])
        alt = st.text_input("Altura (cm)", info["altura"])
    with c3: 
        fey = st.text_input("FEy (%)", info["fey"])
    
    if st.button("🚀 GENERAR INFORME CARDIOLÓGICO"):
        client = Groq(api_key=api_key)
        
        # PROMPT REFORZADO - ESTILO PASTORE
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE, MÉDICO CARDIÓLOGO.
        Redacta un informe de ECOCARDIOGRAMA DOPPLER COLOR para el paciente {pac}.
        
        DATO CLAVE: Fracción de Eyección (FEy) = {fey}%.
        
        INSTRUCCIONES ESTRICTAS:
        1. NO hables de hematocrito, sangre, anemia ni síntomas generales.
        2. Céntrate exclusivamente en hallazgos ecocardiográficos.
        3. Como la FEy es {fey}%, debes informar "Disfunción sistólica del ventrículo izquierdo" (ya que es < 55%).
        
        ESTRUCTURA DEL INFORME:
        I. ANATOMÍA: Describe cavidades cardíacas, espesores de paredes y ecoestructura valvular (indicar rangos normales o cambios degenerativos leves si corresponde).
        II. FUNCIÓN VENTRICULAR: Informa la FEy de {fey}% y analiza la motilidad parietal.
        III. EVALUACIÓN HEMODINÁMICA: Describe flujos valvulares y función diastólica mediante Doppler.
        IV. CONCLUSIÓN: Resume el hallazgo principal (Disfunción sistólica del VI).
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        
        texto_ia = res.choices[0].message.content
        st.info(texto_ia)
        
        docx = crear_word_final(texto_ia, {"paciente": pac, "edad": eda, "peso": pes, "altura": alt}, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR INFORME CARDIOLÓGICO", docx, f"Informe_{pac}.docx")
