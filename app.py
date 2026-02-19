
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def buscar_medida(texto, etiquetas):
    # Busca en los bloques [MEASUREMENT] del ecógrafo
    for etiqueta in etiquetas:
        patron = rf"\[MEASUREMENT\].*?{etiqueta}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto, re.S | re.I)
        if match:
            return str(int(float(match.group(1))))
    return ""

def motor_ecografo(txt, pdf_bytes):
    d = {"pac": "", "ed": "", "fy": "60", "dv": "", "dr": "", "ai": "", "si": "", "fecha": ""}
    
    # 1. Datos del PDF
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_p = doc[0].get_text()
            f_pdf = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_p)
            if f_pdf: d["fecha"] = f_pdf.group(1)
            n_pdf = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_p, re.I)
            if n_pdf: d["pac"] = n_pdf.group(1).strip().upper()
    except: pass

    # 2. Datos del TXT con etiquetas reales del ecógrafo
    if txt:
        if not d["pac"]:
            n_txt = re.search(r"PatientName\s*=\s*([^|\r\n]*)", txt, re.I)
            if n_txt: d["pac"] = n_txt.group(1).replace("^", " ").strip().upper()
        
        e_txt = re.search(r"Age\s*=\s*(\d+)", txt, re.I)
        if e_txt: d["ed"] = e_txt.group(1)

        # Mapeo según archivos analizados:
        d["dv"] = buscar_medida(txt, ["LVIDd", "DDVI"])
        d["dr"] = buscar_medida(txt, ["AORootDiam", "DRAO"])
        d["ai"] = buscar_medida(txt, ["LADiam", "DDAI"])
        d["si"] = buscar_medida(txt, ["IVSd", "DDSIV"])
        # Para FEy, buscamos 'EF' o 'FA'
        fey_val = buscar_medida(txt, ["LVEF", "EF", "FA"])
        if fey_val: d["fy"] = fey_val

    return d

def generar_docx(reporte, dt, imagenes):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Título
    tit = doc.add_paragraph()
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tit.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, txt in enumerate(l1): t1.cell(i//3, i%3).text = txt
    
    doc.add_paragraph("\n")
    # Tabla Medidas
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    # Redacción Médica
    for linea in reporte.split('\n'):
        linea = linea.strip().replace('*', '').replace('"', '')
        if not linea or any(x in linea.lower() for x in ["paciente", "dr.", "mn "]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(linea.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)
    
    # Firma
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    if imagenes:
        doc.add_page_break()
        t_img = doc.add_table(rows=(len(imagenes)+1)//2, cols=2)
        for i, img_data in enumerate(imagenes):
            celda = t_img.cell(i//2, i%2).paragraphs[0]
            celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            celda.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.5))
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

st.set_page_config(page_title="CardioPro 40.5", layout="wide")
st.title("🏥 CardioReport Pro v40.5")

u1 = st.file_uploader("1. Archivo TXT", type=["txt"])
u2 = st.file_uploader("2. Archivo PDF", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u1 and u2 and key:
    txt_raw = u1.read().decode("latin-1", errors="ignore")
    dt = motor_ecografo(txt_raw, u2.getvalue())
    
    st.subheader("🔍 VALIDACIÓN: Verifique los datos extraídos")
    c1, c2, c3 = st.columns(3)
    p_nom = c1.text_input("Paciente", dt["pac"])
    p_fey = c1.text_input("FEy (%)", dt["fy"])
    p_eda = c2.text_input("Edad", dt["ed"])
    p_dvi = c2.text_input("DDVI (mm)", dt["dv"])
    p_fec = c3.text_input("Fecha", dt["fecha"])
    p_siv = c3.text_input("SIV (mm)", dt["si"])

    if st.button("🚀 GENERAR INFORME"):
        client = Groq(api_key=key)
        prompt = f"""Escribe un informe de ecocardiograma profesional. 
        ESTRUCTURA: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS Y DOPPLER, IV. CONCLUSIÓN.
        DATOS: DDVI {p_dvi}mm, SIV {p_siv}mm, FEy {p_fey}%. 
        No menciones el nombre del paciente. Sé técnico y breve."""
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], temperature=0)
        texto_ia = res.choices[0].message.content
        
        imgs = []
        try:
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as doc_pdf:
                for pagina in doc_pdf:
                    for img in pagina.get_images():
                        imgs.append(doc_pdf.extract_image(img[0])["image"])
        except: pass
        
        final_d = {"pac":p_nom,"ed":p_eda,"fy":p_fey,"dv":p_dvi,"dr":dt['dr'],"si":p_siv,"ai":dt['ai'],"fecha":p_fec}
        doc_file = generar_docx(texto_ia, final_d, imgs)
        st.download_button("📥 DESCARGAR WORD", doc_file, f"Informe_{p_nom}.docx")
