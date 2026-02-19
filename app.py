
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTORES DE EXTRACCIÓN TÉCNICA ---

def extraer_valor_txt(texto, etiqueta):
    """Busca el código de la máquina y captura el primer valor numérico que le sigue."""
    patron = rf"{etiqueta}.*?value\s*=\s*([\d.]+)"
    match = re.search(patron, texto, re.S | re.I)
    if match:
        try:
            val = float(match.group(1))
            return str(int(val)) if val.is_integer() else str(val)
        except: return match.group(1)
    return "--"

def extraer_paciente_txt(texto, etiqueta):
    """Busca en el bloque [PATINET INFO] del ecógrafo."""
    patron = rf"{etiqueta}\s*=\s*([\d.\w^/]+)"
    match = re.search(patron, texto, re.I)
    return match.group(1).replace("^", " ").strip() if match else "--"

# --- CONFIGURACIÓN DE ESTADO ---

def inicializar_estado():
    if 'datos' not in st.session_state:
        st.session_state.datos = {
            "pac": "", "ed": "--", "fecha": "--", "peso": "--", "alt": "--",
            "dv": "--", "si": "--", "fy": "60", "dr": "--", "ai": "--"
        }
    if 'informe_ia' not in st.session_state:
        st.session_state.informe_ia = ""
    if 'word_buffer' not in st.session_state:
        st.session_state.word_buffer = None

# --- LÓGICA DE PROCESAMIENTO HÍBRIDO ---

def procesar_archivos(txt_bytes, pdf_bytes):
    txt_raw = txt_bytes.decode("latin-1", errors="ignore")
    
    # 1. Prioridad PDF: Identidad y Fecha
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pdf_text = doc[0].get_text()
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", pdf_text)
            if f_m: st.session_state.datos["fecha"] = f_m.group(1)
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", pdf_text, re.I)
            if n_m: st.session_state.datos["pac"] = n_m.group(1).strip().upper()
    except: pass

    # 2. Prioridad TXT: Medidas y Datos Físicos
    d = st.session_state.datos
    d["peso"] = extraer_paciente_txt(txt_raw, "Weight")
    d["alt"] = extraer_paciente_txt(txt_raw, "Height")
    d["ed"] = extraer_paciente_txt(txt_raw, "Age")
    
    # Mapeo exacto de los archivos de texto de tu equipo
    d["dv"] = extraer_valor_txt(txt_raw, "LVIDd") # DDVI
    d["si"] = extraer_valor_txt(txt_raw, "IVSd")  # Septum
    d["dr"] = extraer_valor_txt(txt_raw, "AORootDiam")
    d["ai"] = extraer_valor_txt(txt_raw, "LADiam")
    d["fy"] = extraer_valor_txt(txt_raw, "EF")

# --- GENERACIÓN DEL WORD (ESTILO PASTORE) ---

def generar_word_pastore(reporte, d, fotos):
    doc = Document()
    # Fuente Arial 10 para estilo técnico
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)
    
    # Título Minimalista
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla 1: Datos (Sin bordes excesivos si prefieres, pero mantenemos Grid por orden)
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    vals = [f"PACIENTE: {d['pac']}", f"EDAD: {d['ed']}", f"FECHA: {d['fecha']}", 
            f"PESO: {d['peso']} kg", f"ALTURA: {d['alt']} cm", "BSA: --"]
    for i, txt in enumerate(vals): t1.cell(i//3, i%3).text = txt
    
    doc.add_paragraph("\n")
    # Tabla 2: Medidas (Directo al punto)
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    meds = [("DDVI", f"{d['dv']} mm"), ("Raíz Aórtica", f"{d['dr']} mm"), 
            ("Aurícula Izq.", f"{d['ai']} mm"), ("Septum", f"{d['si']} mm"), ("FEy", f"{d['fy']} %")]
    for i, (n, v) in enumerate(meds):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    # Cuerpo del informe (Numérico/Esquemático)
    doc.add_paragraph("\n")
    for linea in reporte.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        if any(linea.startswith(x) for x in ["I.", "II.", "III.", "IV.", "CONCL"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)
    
    # Firma Derecha
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    # ANEXO DE IMÁGENES: Filas de 2 (4 filas x 2 cols = 8 fotos)
    if fotos:
        doc.add_page_break()
        at = doc.add_paragraph()
        at.alignment = WD_ALIGN_PARAGRAPH.CENTER
        at.add_run("ANEXO DE IMÁGENES").bold = True
        
        # Tabla de 2 columnas para organizar las fotos de a 2
        num_fotos = len(fotos)
        filas = (num_fotos + 1) // 2
        tabla_fotos = doc.add_table(rows=filas, cols=2)
        
        for i, img_data in enumerate(fotos):
            celda = tabla_fotos.cell(i // 2, i % 2).paragraphs[0]
            celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = celda.add_run()
            # Ajuste de tamaño para que quepan bien 2 por fila
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
            
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- INTERFAZ STREAMLIT ---

st.set_page_config(page_title="CardioPro 47.0", layout="wide")
inicializar_estado()

st.title("🏥 CardioReport Pro v47.0")

with st.sidebar:
    st.header("📂 Carga de Archivos")
    f_txt = st.file_uploader("1. Archivo de Texto (TXT)", type=["txt"])
    f_pdf = st.file_uploader("2. Archivo PDF (Fotos)", type=["pdf"])
    
    if st.button("🔄 EXTRAER DATOS") and f_txt and f_pdf:
        procesar_archivos(f_txt.read(), f_pdf.getvalue())
        st.success("Extracción finalizada.")

# Panel de Validación
st.subheader("📋 Validación de Datos")
c1, c2, c3 = st.columns(3)
d = st.session_state.datos
d["pac"] = c1.text_input("Paciente", d["pac"])
d["fy"] = c1.text_input("FEy (%)", d["fy"])
d["ed"] = c2.text_input("Edad", d["ed"])
d["dv"] = c2.text_input("DDVI (mm)", d["dv"])
d["peso"] = c3.text_input("Peso (kg)", d["peso"])
d["si"] = c3.text_input("SIV (mm)", d["si"])

if st.button("🚀 GENERAR INFORME"):
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: st.error("Falta API Key")
    else:
        with st.spinner("IA procesando estilo Pastore..."):
            client = Groq(api_key=api_key)
            # PROMPT ESTILO PASTORE: Numérico, sin versos, sin adjetivos decorativos.
            prompt = f"""
            Actúa como un cardiólogo técnico. Redacta un informe de ecocardiograma. 
            ESTILO: Estrictamente numérico, directo, sin adjetivos innecesarios (sin 'excelente', 'notable').
            DATOS: DDVI {d['dv']}mm, SIV {d['si']}mm, FEy {d['fy']}%, Raíz Aórtica {d['dr']}mm, AI {d['ai']}mm.
            SECCIONES: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS, IV. CONCLUSIÓN.
            """
            
            try:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], temperature=0.1)
                st.session_state.informe_ia = res.choices[0].message.content
                
                # Extraer fotos
                imgs = []
                with fitz.open(stream=f_pdf.getvalue(), filetype="pdf") as pdf:
                    for pag in pdf:
                        for img_info in pag.get_images():
                            imgs.append(pdf.extract_image(img_info[0])["image"])
