
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def extraer_con_sinonimos(texto_txt, lista_sinonimos):
    """
    Busca el valor numérico que sigue a cualquiera de los sinónimos.
    Estructura del ecógrafo: Parámetro ... value = 40.0
    """
    for s in lista_sinonimos:
        # Buscamos el sinónimo y capturamos el valor después de 'value =' 
        # aunque haya saltos de línea (re.S)
        patron = rf"{s}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto_txt, re.S | re.I)
        if match:
            try:
                # Limpiamos el decimal (de 40.0 a 40)
                valor = match.group(1)
                return str(int(float(valor)))
            except:
                return match.group(1)
    return ""

def procesar_archivos(txt_content, pdf_bytes):
    # Diccionario inicial con valores por defecto para evitar que la app se rompa
    res = {
        "paciente": "No encontrado", "edad": "--", "fecha": "--",
        "ddvi": "--", "siv": "--", "fey": "60", "ao": "--", "ai": "--"
    }
    
    # 1. LEER PDF (Prioridad para Datos Personales)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_pdf = doc[0].get_text()
            # Fecha de estudio
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_pdf)
            if f_m: res["fecha"] = f_m.group(1)
            # Nombre del paciente
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
            if n_m: res["paciente"] = n_m.group(1).strip().upper()
    except: pass

    # 2. LEER TXT (Prioridad para Medidas con Sinónimos)
    if txt_content:
        # Edad
        e_m = re.search(r"Age\s*=\s*(\d+)", txt_content, re.I)
        if e_m: res["edad"] = e_m.group(1)

        # MAPEO TÉCNICO DE TU ECÓGRAFO
        res["ddvi"] = extraer_con_sinonimos(txt_content, ["LVIDd", "DDVI", "VId d"])
        res["siv"] = extraer_con_sinonimos(txt_content, ["IVSd", "DDSIV", "Septum", "SIVd"])
        res["ao"] = extraer_con_sinonimos(txt_content, ["AORootDiam", "DRAO", "Ao Root"])
        res["ai"] = extraer_con_sinonimos(txt_content, ["LADiam", "DDAI", "LA Diam"])
        
        # FEy (Fracción de eyección)
        fey_val = extraer_con_sinonimos(txt_content, ["LVEF", "EF", "FA"])
        if fey_val: res["fey"] = fey_val

    return res

def generar_word_final(reporte, d, fotos):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Encabezado
    t_par = doc.add_paragraph()
    t_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_par.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    d_list = [f"PACIENTE: {d['paciente']}", f"EDAD: {d['edad']} años", f"FECHA: {d['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, texto in enumerate(d_list): t1.cell(i//3, i%3).text = texto
    
    doc.add_paragraph("\n")
    # Tabla Medidas
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    m_list = [("DDVI", f"{d['ddvi']} mm"), ("Raíz Aórtica", f"{d['ao']} mm"), ("Aurícula Izq.", f"{d['ai']} mm"), ("Septum", f"{d['siv']} mm"), ("FEy", f"{d['fey']} %")]
    for i, (n, v) in enumerate(m_list):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    # Redacción Médica
    for line in reporte.split('\n'):
        line = line.strip().replace('*', '')
        if not line or any(x in line.lower() for x in ["paciente", "dr.", "mn "]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(line.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]):
            p.add_run(line).bold = True
        else:
            p.add_run(line)
            
    # Firma
    f_p = doc.add_paragraph(); f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_p.add_run("\n\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    # Fotos
    if fotos:
        doc.add_page_break()
        tf = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
        for i, img in enumerate(fotos):
            c = tf.cell(i//2, i%2).paragraphs[0]
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.add_run().add_picture(io.BytesIO(img), width=Inches(2.5))
            
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- INTERFAZ ---
st.set_page_config(page_title="CardioPro 41.0", layout="wide")
st.title("🏥 CardioReport Pro v41.0")

col_a, col_b = st.columns(2)
u_txt = col_a.file_uploader("1. Archivo de Texto (TXT)", type=["txt"])
u_pdf = col_b.file_uploader("2. Archivo PDF", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    raw_txt = u_txt.read().decode("latin-1", errors="ignore")
    datos = procesar_archivos(raw_txt, u_pdf.getvalue())
    
    st.subheader("🔍 Validar datos antes de generar")
    c1, c2, c3 = st.columns(3)
    # Permite edición manual si algún dato no se levantó
    v_pac = c1.text_input("Paciente", datos["paciente"])
    v_fey = c1.text_input("FEy (%)", datos["fey"])
    v_eda = c2.text_input("Edad", datos["edad"])
    v_dvi = c2.text_input("DDVI (mm)", datos["ddvi"])
    v_fec = c3.text_input("Fecha", datos["fecha"])
    v_siv = c3.text_input("Septum (mm)", datos["siv"])

    if st.button("🚀 GENERAR INFORME"):
        with st.spinner("Redactando informe..."):
            try:
                client = Groq(api_key=api_key)
                # Creamos el diccionario final con lo que hay en pantalla
                d_final = {"paciente":v_pac, "edad":v_eda, "fecha":v_fec, "fey":v_fey, "ddvi":v_dvi, "siv":v_siv, "ao":datos["ao"], "ai":datos["ai"]}
                
                # Prompt para la IA
                prompt = f"Escribe un informe de ecocardiograma. Secciones: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS Y DOPPLER, IV. CONCLUSIÓN. Datos técnicos: DDVI {v_dvi}mm, SIV {v_siv}mm, FEy {v_fey}%. Estilo formal médico."
                
                comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], temperature=0)
                texto_ia = comp.choices[0].message.content
                
                # Extraer fotos
                fotos = []
                with fitz.open(stream=u_pdf.getvalue(), filetype="pdf") as pdf:
                    for pag in pdf:
                        for img_index in pag.get_images():
                            fotos.append(pdf.extract_image(img_index[0])["image"])
                
                doc_bytes = generar_word_final(texto_ia, d_final, fotos)
                st.download_button("📥 DESCARGAR WORD", doc_bytes, f"Informe_{v_pac}.docx")
                st.success("¡Informe listo!")
            except Exception as e:
                st.error(f"Error en el proceso: {e}")
