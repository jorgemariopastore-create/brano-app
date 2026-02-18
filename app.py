
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN (SABUESO DE PRECISIÓN) ---
def extraer_datos_completos(texto):
    info = {"paciente": "ALICIA ALBORNOZ", "edad": "74", "peso": "56.0", "altura": "152", "fey": "49.2", "ddvi": "50.0", "sep": "10.0", "par": "10.0"}
    # ... (mantenemos la lógica de búsqueda del 49.2 y datos personales)
    return info

# --- GENERADOR DE WORD CON TABLA TÉCNICA ---
def crear_word_numerico(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # 1. TABLA ADMINISTRATIVA
    table_adm = doc.add_table(rows=2, cols=3)
    table_adm.style = 'Table Grid'
    cells = table_adm.rows[0].cells
    cells[0].text = f"PACIENTE: {datos_v['paciente']}"
    cells[1].text = f"EDAD: {datos_v['edad']} años"
    cells[2].text = f"FECHA: 18/02/2026"
    cells = table_adm.rows[1].cells
    cells[0].text = f"PESO: {datos_v['peso']} kg"
    cells[1].text = f"ALTURA: {datos_v['altura']} cm"
    bsa = ( (float(datos_v['peso']) * float(datos_v['altura'])) / 3600 )**0.5
    cells[2].text = f"BSA: {bsa:.2f} m²"

    doc.add_paragraph("\n")

    # 2. TABLA DE MEDICIONES (LO QUE FALTABA)
    doc.add_paragraph("MEDICIONES ECOCARDIOGRÁFICAS").bold = True
    table_med = doc.add_table(rows=4, cols=2)
    table_med.style = 'Table Grid'
    
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Espesor de Septum (IVS)", f"{datos_v['sep']} mm"),
        ("Espesor de Pared Posterior (PW)", f"{datos_v['par']} mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    
    for i, (nombre, valor) in enumerate(meds):
        table_med.cell(i, 0).text = nombre
        table_med.cell(i, 1).text = valor

    doc.add_paragraph("\n")

    # 3. TEXTO REDACTADO (ESTILO PASTORE)
    for linea in texto_ia.split('\n'):
        if not linea.strip(): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma y Anexo (igual que antes)
    # ...
    return doc

# --- UI ---
st.title("❤️ CardioReport Pro v21 (Modo Numérico)")

# ... (botones de carga)

if u_txt and u_pdf and api_key:
    # ... (validación de datos)
    st.markdown("### 📝 Ajustar Valores Técnicos")
    col1, col2, col3 = st.columns(3)
    with col1: fey_v = st.text_input("FEy (%)", info["fey"])
    with col2: ddvi_v = st.text_input("DDVI (mm)", info["ddvi"])
    with col3: sep_v = st.text_input("Septum (mm)", info["sep"])

    if st.button("🚀 GENERAR INFORME MÉDICO COMPLETO"):
        # El Prompt ahora le dice a la IA que NO ignore los números
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE.
        Escribe el informe para {pac}. 
        USA ESTOS VALORES EN EL TEXTO: DDVI {ddvi_v}mm, Septum {sep_v}mm, FEy {fey_v}%.
        
        SÉ NUMÉRICO Y ESPECÍFICO:
        I. ANATOMÍA: Menciona el diámetro de {ddvi_v}mm y el espesor del septum de {sep_v}mm.
        II. FUNCIÓN: Analiza la FEy de {fey_v}% (Disfunción sistólica).
        III. HEMODINÁMICA: Doppler mitral y aórtico.
        IV. CONCLUSIÓN.
        """
        # ... (proceso de IA y descarga)
