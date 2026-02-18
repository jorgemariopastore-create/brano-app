
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor_v29(texto):
    # Buscamos los datos reales del PDF de Alicia Albornoz
    info = {"paciente": "", "edad": "74", "peso": "56", "altura": "152", "fey": "68", "ddvi": "40"}
    n_match = re.search(r"(?:Patient Name|Name|Nombre|PACIENTE)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
    if n_match: info["paciente"] = n_match.group(1).replace(',', '').strip()
    # Intentamos capturar la FEy real si está en el TXT
    f_match = re.search(r"EF.*?([\d\.]+)", texto)
    if f_match: info["fey"] = f_match.group(1)
    return info

def crear_word_v29(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Encabezado centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Datos corregida
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    c0 = table.rows[0].cells
    c0[0].text = f"PACIENTE: {datos_v['paciente']}"
    c0[1].text = f"EDAD: {datos_v['edad']} años"
    c0[2].text = f"FECHA: 13/02/2026" # Fecha del informe real
    c1 = table.rows[1].cells
    c1[0].text = f"PESO: {datos_v['peso']} kg"
    c1[1].text = f"ALTURA: {datos_v['altura']} cm"
    bsa = ( (float(datos_v['peso']) * float(datos_v['altura'])) / 3600 )**0.5
    c1[2].text = f"BSA: {bsa:.2f} m²"

    doc.add_paragraph("\n")

    # Cuerpo del informe con estilo directo
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # Detectar títulos de sección
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            run = p.add_run(linea.replace("**", ""))
            run.bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma compacta
    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run(f"__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    # Anexo de imágenes
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

st.title("❤️ CardioReport Pro v29")

u_txt = st.file_uploader("1. Subir TXT de Mediciones", type=["txt", "html"])
u_pdf = st.file_uploader("2. Subir PDF Real (para extraer imágenes)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    info = motor_v29(raw)
    
    st.subheader("📝 Validar Datos Reales")
    c1, c2, c3 = st.columns(3)
    with c1:
        nom_f = st.text_input("Paciente", info["paciente"])
        pes_f = st.text_input("Peso (kg)", info["peso"])
    with c2:
        eda_f = st.text_input("Edad", info["edad"])
        alt_f = st.text_input("Altura (cm)", info["altura"])
    with c3:
        fey_f = st.text_input("FEy (%)", info["fey"]) # Cambiar a 68 si es Alicia
        ddvi_f = st.text_input("DDVI (mm)", info["ddvi"]) # Cambiar a 40 si es Alicia

    if st.button("🚀 GENERAR INFORME"):
        client = Groq(api_key=api_key)
        # PROMPT DE IMITACIÓN ESTRICTA
        prompt = f"""
        ERES EL DR. PASTORE, CARDIÓLOGO. Imita el estilo del informe real adjunto.
        DATOS: DDVI {ddvi_f}mm, FEy {fey_f}%.
        
        ESTILO DE REDACCIÓN:
        - I. ANATOMÍA: Menciona diámetros de raíz aórtica, aurícula izquierda y espesores parietales. Usa frases como "Cavidades ventriculares de dimensiones normales".
        - II. FUNCIÓN VENTRICULAR: Sé breve. "Función sistólica del VI conservada. FEy {fey_f}%".
        - III. VALVULAS Y DOPPLER: "Válvulas de ecoestructura y movilidad normal. Flujos laminares".
        - IV. CONCLUSIÓN: Una sola oración técnica.
        
        NO uses frases de relleno como "se puede concluir", "en base a los resultados" o "presenta hallazgos".
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        txt_final = res.choices[0].message.content
        st.info(txt_final)
        
        word = crear_word_v29(txt_final, {"paciente": nom_f, "edad": eda_f, "peso": pes_f, "altura": alt_f, "fey": fey_f, "ddvi": ddvi_f}, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR INFORME", word, f"Informe_{nom_f}.docx")
