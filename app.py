
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def extraer_valor_ecografo(texto, etiqueta_buscada):
    # Esta función busca el valor numérico en el bloque de medición del ecógrafo
    patron = rf"{etiqueta_buscada}.*?value\s*=\s*([\d.]+)"
    match = re.search(patron, texto, re.S | re.I)
    if match:
        try:
            return str(int(float(match.group(1))))
        except:
            return match.group(1)
    return ""

def motor_universal(txt, pdf_bytes):
    d = {"pac": "", "ed": "", "fy": "60", "dv": "", "dr": "", "ai": "", "si": "", "fecha": ""}
    
    # 1. Prioridad: Datos del PDF (Nombre y Fecha)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_p = doc[0].get_text()
            f_pdf = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_p)
            if f_pdf: d["fecha"] = f_pdf.group(1)
            n_pdf = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_p, re.I)
            if n_pdf: d["pac"] = n_pdf.group(1).strip().upper()
    except: pass

    # 2. Datos del TXT (Medidas y Edad)
    if txt:
        # Nombre y Edad si no estaban en el PDF
        if not d["pac"]:
            n_txt = re.search(r"PatientName\s*=\s*([^|\r\n]*)", txt, re.I)
            if n_txt: d["pac"] = n_txt.group(1).strip().upper()
        
        e_txt = re.search(r"Age\s*=\s*(\d+)", txt, re.I)
        if e_txt: d["ed"] = e_txt.group(1)

        # Mapeo de medidas según el formato de los 3 archivos analizados
        d["dv"] = extraer_valor_ecografo(txt, "DDVI")
        d["dr"] = extraer_valor_ecografo(txt, "DRAO")
        d["ai"] = extraer_valor_ecografo(txt, "DDAI")
        d["si"] = extraer_valor_ecografo(txt, "DDSIV")
        d["fy"] = extraer_valor_ecografo(txt, "FA") or "60"

    return d

def generar_docx(reporte, dt, imagenes):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Encabezado
    tit = doc.add_paragraph()
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tit.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de datos personales
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    datos = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, texto in enumerate(datos): t1.cell(i//3, i%3).text = texto
    
    doc.add_paragraph("\n")
    
    # Tabla de mediciones
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    medidas = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(medidas):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    
    # Cuerpo del informe (formateado por la IA)
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
    
    # Imágenes si existen
    if imagenes:
        doc.add_page_break()
        t_img = doc.add_table(rows=(len(imagenes)+1)//2, cols=2)
        for i, img_data in enumerate(imagenes):
            celda = t_img.cell(i//2, i%2).paragraphs[0]
            celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            celda.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.5))
            
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioPro Final", layout="wide")
st.title("🏥 CardioReport Pro v40.4")

c_up1, c_up2 = st.columns(2)
u1 = c_up1.file_uploader("Archivo TXT/HTML del Ecógrafo", type=["txt", "html"])
u2 = c_up2.file_uploader("Archivo PDF (Imágenes)", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u1 and u2 and key:
    txt_content = u1.read().decode("latin-1", errors="ignore")
    datos_extraidos = motor_universal(txt_content, u2.getvalue())
    
    st.subheader("📋 Validación de Datos del Paciente")
    col1, col2, col3 = st.columns(3)
    p_nom = col1.text_input("Nombre", datos_extraidos["pac"])
    p_fey = col1.text_input("FEy (%)", datos_extraidos["fy"])
    p_eda = col2.text_input("Edad", datos_extraidos["ed"])
    p_dvi = col2.text_input("DDVI (mm)", datos_extraidos["dv"])
    p_fec = col3.text_input("Fecha", datos_extraidos["fecha"])
    p_siv = col3.text_input("SIV (mm)", datos_extraidos["si"])

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        client = Groq(api_key=key)
        # Prompt optimizado para evitar repeticiones y mantener estructura técnica
        prompt = f"""Escribe un informe de ecocardiograma. 
        ESTRUCTURA OBLIGATORIA: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS Y DOPPLER, IV. CONCLUSIÓN.
        DATOS: DDVI {p_dvi}mm, SIV {p_siv}mm, FEy {p_fey}%. 
        REGLAS: Solo lenguaje médico. No menciones el nombre del paciente. No saludes. Sé muy breve."""
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], temperature=0)
        texto_ia = res.choices[0].message.content
        
        # Extraer imágenes del PDF
        imgs = []
        try:
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as doc_pdf:
                for pagina in doc_pdf:
                    for img in pagina.get_images():
                        imgs.append(doc_pdf.extract_image(img[0])["image"])
        except: pass
        
        st.markdown("---")
        st.write(texto_ia)
        
        dict_final = {"pac":p_nom,"ed":p_eda,"fy":p_fey,"dv":p_dvi,"dr":datos_extraidos['dr'],"si":p_siv,"ai":datos_extraidos['ai'],"fecha":p_fec}
        archivo_word = generar_docx(texto_ia, dict_final, imgs)
        st.download_button("📥 DESCARGAR INFORME EN WORD", archivo_word, f"Informe_{p_nom}.docx")
