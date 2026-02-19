
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTORES DE EXTRACCIÓN PARA TU ECÓGRAFO ---

def extraer_valor_txt(texto_completo, etiqueta):
    """Busca en el TXT el formato: Etiqueta ... value = Numero"""
    # Escaneamos 300 caracteres después de la etiqueta para encontrar su valor
    patron = rf"{etiqueta}.*?value\s*=\s*([\d.]+)"
    match = re.search(patron, texto_completo, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            return str(int(val)) if val.is_integer() else str(val)
        except: return match.group(1)
    return "--"

def extraer_info_paciente(texto_txt, etiqueta):
    """Busca en el bloque [PATINET INFO] del TXT"""
    patron = rf"{etiqueta}\s*=\s*([\d.\w^/]+)"
    match = re.search(patron, texto_txt, re.IGNORECASE)
    return match.group(1).replace("^", " ").strip() if match else "--"

# --- 2. GESTIÓN DE ESTADO (SESSION STATE) ---

def inicializar_estado():
    if 'datos' not in st.session_state:
        st.session_state.datos = {
            "pac": "", "ed": "--", "fecha": "--", "peso": "--", "alt": "--",
            "dv": "--", "si": "--", "fy": "60", "dr": "--", "ai": "--"
        }
    if 'word_buffer' not in st.session_state:
        st.session_state.word_buffer = None
    if 'texto_ia' not in st.session_state:
        st.session_state.texto_ia = ""

# --- 3. PROCESAMIENTO HÍBRIDO ---

def procesar_archivos(txt_bytes, pdf_bytes):
    txt_raw = txt_bytes.decode("latin-1", errors="ignore")
    
    # Extraer del PDF (Prioridad Nombre y Fecha)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pdf_text = doc[0].get_text()
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", pdf_text)
            if f_m: st.session_state.datos["fecha"] = f_m.group(1)
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", pdf_text, re.I)
            if n_m: st.session_state.datos["pac"] = n_m.group(1).strip().upper()
    except: pass

    # Extraer del TXT (Prioridad Medidas y Datos Físicos)
    d = st.session_state.datos
    d["peso"] = extraer_info_paciente(txt_raw, "Weight")
    d["alt"] = extraer_info_paciente(txt_raw, "Height")
    d["ed"] = extraer_info_paciente(txt_raw, "Age")
    
    # Medidas técnicas según tus archivos (LVIDd, IVSd, etc.)
    d["dv"] = extraer_valor_txt(txt_raw, "LVIDd")
    d["si"] = extraer_valor_txt(txt_raw, "IVSd")
    d["dr"] = extraer_valor_txt(txt_raw, "AORootDiam")
    d["ai"] = extraer_valor_txt(txt_raw, "LADiam")
    d["fy"] = extraer_valor_txt(txt_raw, "EF")
    
    st.session_state.datos = d

# --- 4. GENERACIÓN DE DOCUMENTO ---

def crear_word(reporte, d, fotos):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    vals = [f"PACIENTE: {d['pac']}", f"EDAD: {d['ed']}", f"FECHA: {d['fecha']}", 
            f"PESO: {d['peso']} kg", f"ALTURA: {d['alt']} cm", "BSA: --"]
    for i, txt in enumerate(vals): t1.cell(i//3, i%3).text = txt
    
    doc.add_paragraph("\n")
    # Tabla Medidas
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    meds = [("DDVI", f"{d['dv']} mm"), ("Raíz Aórtica", f"{d['dr']} mm"), 
            ("Aurícula Izq.", f"{d['ai']} mm"), ("Septum", f"{d['si']} mm"), ("FEy", f"{d['fy']} %")]
    for i, (n, v) in enumerate(meds):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    # Cuerpo del informe
    doc.add_paragraph("\n" + reporte + "\n")
    
    # Firma
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    # Imágenes del PDF
    if fotos:
        doc.add_page_break()
        tf = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
        for i, img_data in enumerate(fotos):
            celda = tf.cell(i//2, i%2).paragraphs
