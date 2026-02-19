
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def buscador_avanzado(texto_txt, sinonimos):
    """
    Busca el valor numérico en el bloque técnico del ecógrafo.
    Busca la etiqueta (ej. LVIDd) y luego captura el primer 'value =' que aparezca.
    """
    for s in sinonimos:
        # El parámetro (?s) permite que el '.' incluya saltos de línea para buscar en el bloque
        patron = rf"{s}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto_txt, re.S | re.I)
        if match:
            try:
                # Convertimos 40.0 a 40 para formato médico
                return str(int(float(match.group(1))))
            except:
                return match.group(1)
    return ""

def motor_hibrido_v41(txt_raw, pdf_bytes):
    # Diccionario de seguridad para evitar errores de la app
    d = {"pac": "PACIENTE", "ed": "--", "fy": "60", "dv": "--", "dr": "--", "ai": "--", "si": "--", "fecha": "--"}
    
    # 1. DATOS DEL PDF (Nombre y Fecha)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_p = doc[0].get_text()
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_p)
            if f_m: d["fecha"] = f_m.group(1)
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_p, re.I)
            if n_m: d["pac"] = n_m.group(1).strip().upper()
    except: pass

    # 2. DATOS DEL TXT (Medidas con búsqueda por bloques)
    if txt_raw:
        # Edad
        e_m = re.search(r"Age\s*=\s*(\d+)", txt_raw, re.I)
        if e_m: d["ed"] = e_m.group(1)

        # Mapeo Técnico (Sinónimos exactos de tus archivos)
        d["dv"] = buscador_avanzado(txt_raw, ["LVIDd", "VId d", "DDVI"])
        d["si"] = buscador_avanzado(txt_raw, ["IVSd", "DDSIV", "Septum"])
        d["dr"] = buscador_avanzado(txt_raw, ["AORootDiam", "Ao Root", "DRAO"])
        d["ai"] = buscador_avanzado(txt_raw, ["LADiam", "LA Diam", "DDAI"])
        
        # FEy (Buscamos EF o Teich que usa tu máquina)
        fey_val = buscador_avanzado(txt_raw, ["EF", "LVEF", "FA", "Teich"])
        if fey_val: d["fy"] = fey_val

    return d

def crear_word(reporte, dt, fotos):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Título centrado
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla 1: Datos Personales
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, txt in enumerate(l1): t1.cell(i//3, i%3).text = txt
    
    doc.add_paragraph("\n")
    # Tabla 2: Medidas
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    # Cuerpo del informe
    for linea in reporte.split('\n'):
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
        for i, img in enumerate(fotos):
            c = tf.cell(i//2, i%2).paragraphs[0]
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.add_run().add_picture(io.BytesIO(img), width=Inches(2.5))
            
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- STREAMLIT UI ---
st.set_page_config(page_title="CardioPro 41.2", layout="wide")
st.title("🏥 CardioReport Pro v41.2")

u1 = st.file_uploader("1. Archivo TXT (Medidas)", type=["txt"])
u2 = st.file_uploader("2. Archivo PDF (Fotos y Nombre)", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u1 and u2 and key:
    txt_data = u1.read().decode("latin-1", errors="ignore")
    datos = motor_hibrido_v41(txt_data, u2.getvalue())
    
    st.subheader("🔍 VALIDACIÓN DE DATOS")
    c1, c2, c3 = st.columns(3)
    v_pac = c1.text_input("Paciente", datos["pac"])
    v_fey = c1.text_input("FEy (%)", datos["fy"])
    v_eda = c2.text_input("Edad", datos["ed"])
    v_dvi = c2.text_input("DDVI (mm)", datos["dv"])
    v_fec = c3.text_input("Fecha", datos["fecha"])
    v_siv = c3.text_input("SIV (mm)", datos["si"])

    if st.button("🚀 GENERAR"):
        try:
            client = Groq(api_key=key)
            # Diccionario final para el Word basado en lo que el usuario validó/editó
            d_final = {"pac":v_pac, "ed":v_eda, "fy":v_fey, "dv":v_dvi, "si":v_siv, "dr":datos["dr"], "ai":datos["ai"], "fecha":v_fec}
            
            pxt = f"Redacta un informe médico de ecocardiograma. Secciones: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS, IV. CONCLUSIÓN. Datos: DDVI {v_dvi}mm, SIV {v_siv}mm, FEy {v_fey}%. Estilo formal."
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":pxt}], temperature=0)
            texto_ia = res.choices[0].message.content
            
            # Imágenes
            img_list = []
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as pdf_doc:
                for pag in pdf_doc:
                    for img in pag.get_images():
                        img_list.append(pdf_doc.extract_image(img[0])["image"])
            
            doc_out = crear_word(texto_ia, d_final, img_list)
            st.download_button("📥 DESCARGAR INFORME", doc_out, f"Informe_{v_pac}.docx")
            st.success("¡Informe generado exitosamente!")
        except Exception as e:
            st.error(f"Error: {e}")
