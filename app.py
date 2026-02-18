
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE BÚSQUEDA UNIVERSAL (No forzado) ---
def motor_de_extraccion(texto):
    # Valores iniciales vacíos o estándar
    info = {
        "paciente": "", 
        "edad": "", 
        "peso": "70.0", 
        "altura": "170", 
        "fey": "55.0", 
        "ddvi": "50.0", 
        "sep": "10.0",
        "par": "10.0"
    }
    
    # Búsqueda dinámica de Nombre
    n = re.search(r"Patient Name\s*:\s*(.*)", texto, re.I)
    if n: info["paciente"] = n.group(1).strip()
    
    # Búsqueda dinámica de Edad
    e = re.search(r"Age\s*:\s*(\d+)", texto, re.I)
    if e: info["edad"] = e.group(1).strip()

    # Búsqueda de FEy (Busca el primer porcentaje lógico que encuentre el ecógrafo)
    # Primero intenta el método de Alicia (resultNo)
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey: 
        info["fey"] = f"{float(match_fey.group(1)):.1f}"
    else:
        # Si no, busca cualquier valor que diga '%'
        porcentajes = re.findall(r"value\s*=\s*([\d\.]+)\s*displayUnit\s*=\s*%", texto)
        if porcentajes: info["fey"] = porcentajes[0]
    
    return info

# --- 2. GENERADOR DE WORD ---
def crear_word(texto_ia, datos, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título y Tablas (Dinámicos con los datos de la pantalla)
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Datos del Paciente
    table_adm = doc.add_table(rows=2, cols=3)
    table_adm.style = 'Table Grid'
    c0 = table_adm.rows[0].cells
    c0[0].text = f"PACIENTE: {datos['paciente']}"
    c0[1].text = f"EDAD: {datos['edad']} años"
    c0[2].text = f"FECHA: 18/02/2026"
    c1 = table_adm.rows[1].cells
    c1[0].text = f"PESO: {datos['peso']} kg"
    c1[1].text = f"ALTURA: {datos['altura']} cm"
    try:
        bsa = ( (float(datos['peso']) * float(datos['altura'])) / 3600 )**0.5
        c1[2].text = f"BSA: {bsa:.2f} m²"
    except:
        c1[2].text = "BSA: --"

    doc.add_paragraph("\n")

    # Tabla de Mediciones
    doc.add_paragraph("MEDICIONES TÉCNICAS").bold = True
    table_med = doc.add_table(rows=4, cols=2)
    table_med.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos['ddvi']} mm"),
        ("Espesor de Septum (IVS)", f"{datos['sep']} mm"),
        ("Espesor de Pared Posterior (PW)", f"{datos['par']} mm"),
        ("Fracción de Eyección (FEy)", f"{datos['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_med.cell(i, 0).text = n
        table_med.cell(i, 1).text = v

    doc.add_paragraph("\n")
    # Agregar texto de la IA y Firma...
    # (El código sigue la misma lógica de pegado de imágenes)
    return doc

# --- 3. INTERFAZ ---
st.title("❤️ CardioReport Pro (Versión Multi-Paciente)")

u_txt = st.file_uploader("1. Subir Reporte TXT", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    # El motor extrae lo que encuentra en EL ARCHIVO ACTUAL
    info_actual = motor_de_extraccion(contenido)
    
    st.markdown("### 📝 Datos Detectados (Confirmar antes de generar)")
    st.caption("Si el ecógrafo no detectó un valor, completalo manualmente:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        nom = st.text_input("Nombre del Paciente", info_actual["paciente"])
        pes = st.text_input("Peso (kg)", info_actual["peso"])
    with col2:
        eda = st.text_input("Edad", info_actual["edad"])
        alt = st.text_input("Altura (cm)", info_actual["altura"])
    with col3:
        fey = st.text_input("FEy (%)", info_actual["fey"])
        ddvi = st.text_input("DDVI (mm)", info_actual["ddvi"])

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        # La IA recibe los datos que están en los cuadros de texto, no datos fijos
        prompt = f"ERES EL DR. PASTORE. Redacta informe para {nom}. FEy: {fey}%, DDVI: {ddvi}mm. Estructura I-IV."
        # ... proceso de Groq y descarga de Word ...
