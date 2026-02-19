
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN HÍBRIDO ---

def procesar_estudio_optimizado(txt_raw, pdf_bytes):
    # Diccionario con valores por defecto
    d = {
        "pac": "PACIENTE", "ed": "--", "fecha": "--", 
        "peso": "--", "alt": "--", "dv": "--", 
        "si": "--", "fy": "60", "dr": "--", "ai": "--"
    }
    
    # --- A. EXTRACCIÓN DEL PDF (Datos Personales y Físicos) ---
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_pdf = doc[0].get_text()
            
            # Nombre: Buscamos después de "Paciente:" o "Nombre pac."
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
            if n_m: d["pac"] = n_m.group(1).strip().upper()
            
            # Fecha del Estudio (evitamos fecha de nacimiento buscando cerca de la cabecera)
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_pdf)
            if f_m: d["fecha"] = f_m.group(1)
            
            # Peso y Altura (El PDF suele tenerlos limpios)
            p_m = re.search(r"Peso\s*\(?kg\)?\s*[:=-]?\s*([\d.]+)", texto_pdf, re.I)
            if p_m: d["peso"] = p_m.group(1)
            
            a_m = re.search(r"Altura\s*\(?cm\)?\s*[:=-]?\s*([\d.]+)", texto_pdf, re.I)
            if a_m: d["alt"] = a_m.group(1)
    except: pass

    # --- B. EXTRACCIÓN DEL TXT (Medidas Técnicas) ---
    if txt_raw:
        # Edad (del TXT es confiable)
        e_m = re.search(r"Age\s*=\s*(\d+)", txt_raw, re.I)
        if e_m: d["ed"] = e_m.group(1)

        # Medidas del bloque [MEASUREMENT]
        def get_val(codigo):
            m = re.search(rf"{codigo}.*?value\s*=\s*([\d.]+)", txt_raw, re.DOTALL | re.IGNORECASE)
            return str(int(float(m.group(1)))) if m else "--"

        d["dv"] = get_val("LVIDd")      # DDVI
        d["si"] = get_val("IVSd")      # Septum
        d["dr"] = get_val("AORootDiam") # Raíz Aórtica
        d["ai"] = get_val("LADiam")     # Aurícula Izq.
        d["fy"] = get_val("EF")         # FEy
        if d["fy"] == "--": d["fy"] = "60"

    return d

# --- 2. GENERACIÓN DEL WORD (Estilo Pastore + Anexo 2 col) ---

def generar_word_pastore(rep, dt, ims):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(10)
    
    # Encabezado
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", 
          f"PESO: {dt['peso']} kg", f"ALTURA: {dt['alt']} cm", "BSA: --"]
    for i, x in enumerate(l1): t1.cell(i//3, i%3).text = x
    
    doc.add_paragraph("\n")
    # Tabla Medidas
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), 
          ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    # Informe IA
    doc.add_paragraph("\n")
    for linea in rep.split('\n'):
        linea = linea.strip().replace('*', '')
        if not linea: continue
        p = doc.add_paragraph()
        if any(linea.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]):
            p.add_run(linea).bold = True
        else: p.add_run(linea)
            
    # Firma
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    # Anexo Imágenes (Filas de 2)
    if ims:
        doc.add_page_break()
        p_anexo = doc.add_paragraph()
        p_anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_anexo.add_run("ANEXO DE IMÁGENES").bold = True
        
        ti = doc.add_table(rows=(len(ims)+1)//2, cols=2)
        for i, m in enumerate(ims):
            c = ti.cell(i//2, i%2).paragraphs[0]
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.add_run().add_picture(io.BytesIO(m), width=Inches(2.8))
            
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- 3. INTERFAZ STREAMLIT CON SESSION STATE ---

st.set_page_config(page_title="CardioPro 48.0", layout="wide")

if 'datos' not in st.session_state:
    st.session_state.datos = None
if 't_ia' not in st.session_state:
    st.session_state.t_ia = None

st.title("🏥 CardioReport Pro v48.0")

with st.sidebar:
    u1 = st.file_uploader("1. Archivo TXT", type=["txt"])
    u2 = st.file_uploader("2. Archivo PDF", type=["pdf"])
    ak = st.secrets.get("GROQ_API_KEY")
    
    if st.button("🔄 EXTRAER DATOS") and u1 and u2:
        t_raw = u1.read().decode("latin-1", errors="ignore")
        st.session_state.datos = procesar_estudio_optimizado(t_raw, u2.getvalue())

if st.session_state.datos:
    d = st.session_state.datos
    st.subheader("🔍 VALIDACIÓN DE DATOS")
    c1, c2, c3 = st.columns(3)
    d["pac"] = c1.text_input("Paciente", d["pac"])
    d["fy"] = c1.text_input("FEy (%)", d["fy"])
    d["ed"] = c2.text_input("Edad", d["ed"])
    d["dv"] = c2.text_input("DDVI (mm)", d["dv"])
    d["fecha"] = c3.text_input("Fecha", d["fecha"])
    d["si"] = c3.text_input("SIV (mm)", d["si"])
    d["peso"] = c1.text_input("Peso (kg)", d["peso"])
    d["alt"] = c2.text_input("Altura (cm)", d["alt"])

    if st.button("🚀 GENERAR INFORME"):
        cl = Groq(api_key=ak)
