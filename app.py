
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Función de búsqueda mejorada para el formato específico de tu ecógrafo
def extraer_dato_ecografo(texto_completo, etiquetas):
    for etiqueta in etiquetas:
        # Buscamos el bloque que contiene la etiqueta y capturamos el siguiente 'value ='
        patron = rf"{etiqueta}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto_completo, re.S | re.I)
        if match:
            try:
                # Convertimos a entero para evitar el .0 innecesario
                return str(int(float(match.group(1))))
            except:
                return match.group(1)
    return ""

def motor_40_9(txt_raw, pdf_bytes):
    # Valores por defecto para evitar errores de aplicación
    d = {"pac": "PACIENTE", "ed": "--", "fy": "60", "dv": "--", "dr": "--", "ai": "--", "si": "--", "fecha": "--"}
    
    # 1. Prioridad PDF: Nombre y Fecha (Más limpios)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_pdf = doc[0].get_text()
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_pdf)
            if f_m: d["fecha"] = f_m.group(1)
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
            if n_m: d["pac"] = n_m.group(1).strip().upper()
    except: pass

    # 2. Prioridad TXT: Medidas Técnicas (Más precisas)
    if txt_raw:
        # Edad (Age = 86Y)
        e_m = re.search(r"Age\s*=\s*(\d+)", txt_raw, re.I)
        if e_m: d["ed"] = e_m.group(1)

        # Mapeo por bloques técnicos (Sinónimos detectados en tus archivos)
        d["dv"] = extraer_dato_ecografo(txt_raw, ["LVIDd", "DDVI", "VId d"])
        d["si"] = extraer_dato_ecografo(txt_raw, ["IVSd", "DDSIV", "Septum"])
        d["dr"] = extraer_dato_ecografo(txt_raw, ["AORootDiam", "DRAO", "Ao Root"])
        d["ai"] = extraer_dato_ecografo(txt_raw, ["LADiam", "DDAI", "LA Diam"])
        
        # FEy (Buscamos EF o FA)
        fey_val = extraer_dato_ecografo(txt_raw, ["EF", "LVEF", "FA"])
        if fey_val: d["fy"] = fey_val

    return d

def crear_informe_word(texto_ia, dt, fotos):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Título
    t_p = doc.add_paragraph()
    t_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos Personales
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, texto in enumerate(l1): t1.cell(i//3, i%3).text = texto
    
    doc.add_paragraph("\n")
    # Tabla Medidas
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    meds = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(meds):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    # Texto redactado
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('*', '')
        if not linea or any(x in linea.lower() for x in ["paciente", "dr.", "mn "]): continue
        par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(linea.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]):
            par.add_run(linea).bold = True
        else:
            par.add_run(linea)
    
    # Firma
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    if fotos:
        doc.add_page_break()
        tf = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
        for i, img_data in enumerate(fotos):
            celda = tf.cell(i//2, i%2).paragraphs[0]
            celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            celda.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.5))
            
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioPro 40.9", layout="wide")
st.title("🏥 CardioReport Pro v40.9")

u_txt = st.file_uploader("1. Archivo TXT", type=["txt"])
u_pdf = st.file_uploader("2. Archivo PDF", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u_txt and u_pdf and key:
    raw_txt = u_txt.read().decode("latin-1", errors="ignore")
    datos = motor_40_9(raw_txt, u_pdf.getvalue())
    
    st.subheader("📋 Validación de Datos")
    c1, c2, c3 = st.columns(3)
    # Estos inputs permiten corregir a mano si algo falla
    v_pac = c1.text_input("Paciente", datos["pac"])
    v_fey = c1.text_input("FEy %", datos["fy"])
    v_eda = c2.text_input("Edad", datos["ed"])
    v_dvi = c2.text_input("DDVI mm", datos["dv"])
    v_fec = c3.text_input("Fecha", datos["fecha"])
    v_siv = c3.text_input("SIV mm", datos["si"])

    if st.button("🚀 GENERAR INFORME FINAL"):
        client = Groq(api_key=key)
        px = f"Redacta un informe médico profesional. Estructura: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS, IV. CONCLUSIÓN. Datos: DDVI {v_dvi}mm, SIV {v_siv}mm, FEy {v_fey}%. Sin nombre de paciente."
        
        try:
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
            texto_ia = res.choices[0].message.content
            
            # Imágenes
            img_list = []
            with fitz.open(stream=u_pdf.getvalue(), filetype="pdf") as pdf_doc:
                for pagina in pdf_doc:
                    for img in pagina.get_images():
                        img_list.append(pdf_doc.extract_image(img[0])["image"])
            
            # Construir diccionario para el Word con lo validado en pantalla
            d_word = {"pac":v_pac, "ed":v_eda, "fy":v_fey, "dv":v_dvi, "si":v_siv, "dr":datos["dr"], "ai":datos["ai"], "fecha":v_fec}
            
            word_file = crear_informe_word(texto_ia, d_word, img_list)
            st.download_button("📥 DESCARGAR INFORME WORD", word_file, f"Informe_{v_pac}.docx")
            st.success("¡Informe generado con éxito!")
        except Exception as e:
            st.error(f"Error: {e}")
