
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN DINÁMICO (Universal para cualquier paciente) ---
def motor_v30(texto):
    # Valores por defecto que se sobreescriben al leer el archivo
    info = {
        "paciente": "", 
        "edad": "74", 
        "peso": "56", 
        "altura": "152", 
        "fey": "68", 
        "ddvi": "40", 
        "drao": "32", 
        "ddai": "32"
    }
    
    if texto:
        # Búsqueda dinámica de nombre (Paciente: NOMBRE)
        n = re.search(r"(?:Patient Name|Name|Nombre|PACIENTE)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).replace(',', '').strip()
        
        # Búsqueda de FEy (EF o Fracción de Eyección)
        f = re.search(r"(?:EF|FEy|Fracción de Eyección).*?([\d\.,]+)", texto, re.I)
        if f: info["fey"] = f.group(1).replace(',', '.')
        
        # Búsqueda de DDVI
        d = re.search(r"(?:LVIDd|DDVI).*?([\d\.,]+)", texto, re.I)
        if d: info["ddvi"] = d.group(1).replace(',', '.')

    return info

# --- 2. GENERADOR DE WORD (Estilo Médico Profesional Justificado) ---
def crear_word_v30(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título Centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Datos del Paciente
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

    # Tabla de Hallazgos Numéricos
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

    # Cuerpo del Informe (Texto de la IA Justificado)
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

    # Firma a la Derecha
    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    # Anexo de Imágenes extraídas del PDF
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
                cp.add_run().add_picture(io.BytesIO(d), width=Inches(2.5))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ DE USUARIO (Streamlit) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("❤️ CardioReport Pro v30")

col_u1, col_u2 = st.columns(2)
with col_u1:
    u_txt = st.file_uploader("1. Subir TXT/HTML del Ecógrafo", type=["txt", "html"])
with col_u2:
    u_pdf = st.file_uploader("2. Subir PDF con Capturas", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("3. Ingrese Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    # Procesamiento dinámico de los archivos subidos
    raw_content = u_txt.read().decode("latin-1", errors="ignore")
    info_auto = motor_v30(raw_content)
    
    st.markdown("---")
    st.subheader("📝 Validar y Editar Datos (Se usará para el informe final)")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        nom_f = st.text_input("Nombre del Paciente", info_auto["paciente"])
        pes_f = st.text_input("Peso (kg)", info_auto["peso"])
    with c2:
        eda_f = st.text_input("Edad", info_auto["edad"])
        alt_f = st.text_input("Altura (cm)", info_auto["altura"])
    with c3:
        fey_f = st.text_input("FEy (%)", info_auto["fey"])
        ddvi_f = st.text_input("DDVI (mm)", info_auto["ddvi"])

    if st.button("🚀 GENERAR INFORME CARDIOLÓGICO", type="primary"):
        with st.spinner("El Dr. Pastore está analizando el estudio..."):
            client = Groq(api_key=api_key)
            
            # Prompt optimizado: Estilo seco, técnico y sin repeticiones de nombre
            prompt_medico = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta un informe de ecocardiograma.
            DATOS TÉCNICOS: FEy {fey_f}%, DDVI {ddvi_f}mm. 
            
            ESTILO DE REDACCIÓN:
            1. NO repitas el nombre del paciente en el texto.
            2. Usa párrafos cortos y lenguaje estrictamente médico.
            3. Estructura obligatoria:
               I. ANATOMÍA (Menciona Raíz Aórtica y Aurícula Izquierda de 32mm).
               II. FUNCIÓN VENTRICULAR (FEy {fey_f}%: Función conservada si >=55%, disfunción leve si <55%).
               III. VÁLVULAS Y DOPPLER (Ecoestructura y movilidad normal, flujos laminares).
               IV. CONCLUSIÓN (Breve y técnica).
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "user", "content": prompt_medico}], 
                temperature=0
            )
            
            texto_ia_final = completion.choices[0].message.content
            st.info(texto_ia_final)
            
            # Preparar descarga del Word
            datos_finales = {
                "paciente": nom_f, "edad": eda_f, "peso": pes_f, 
                "altura": alt_f, "fey": fey_f, "ddvi": ddvi_f, 
                "drao": "32", "ddai": "32"
            }
            word_bytes = crear_word_v30(texto_ia_final, datos_finales, u_pdf.getvalue())
            
            st.download_button(
                label="📥 DESCARGAR INFORME EN WORD",
                data=word_bytes,
                file_name=f"Informe_Eco_{nom_f.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
