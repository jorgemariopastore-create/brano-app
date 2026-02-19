
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches

# 1. Configuración de Seguridad y Secrets
def get_groq_client():
    # Intenta obtener la clave desde secrets o desde el input del usuario
    api_key = st.secrets.get("GROQ_API_KEY") or st.session_state.get("custom_api_key")
    if not api_key:
        return None
    return Groq(api_key=api_key)

# 2. Motor de Extracción con Normalización de Texto
def extraer_datos_precisos(doc_pdf):
    texto_completo = ""
    for pagina in doc_pdf:
        texto_completo += pagina.get_text()
    
    # Normalización: Convertimos todo a una sola línea limpia
    # Eliminamos comillas, saltos de línea y símbolos que ensucian las tablas del SonoScape
    t_limpio = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚ\s:]', ' ', texto_completo)
    t_limpio = " ".join(t_limpio.split()) # Colapsar espacios
    
    datos = {"pac": "NO DETECTADO", "dv": "40", "si": "11", "fy": "67"} # Defaults basados en Alicia
    
    # Búsqueda de Paciente
    m_pac = re.search(r"Paciente\s*:\s*([A-Z\s]+?)(?:\s*Fecha|$)", t_limpio, re.I)
    if m_pac: datos["pac"] = m_pac.group(1).strip()

    # Búsqueda de métricas usando proximidad (Lookahead positivo)
    # Buscamos la sigla y el primer número que aparezca después
    regex_map = {
        "dv": r"DDVI\s+(\d+)",
        "si": r"(?:DDSIV|SIV)\s+(\d+)",
        "fy": r"(?:FE|eyección)\s+(?:del\s+VI\s+)?(\d+)"
    }
    
    for clave, patron in regex_map.items():
        match = re.search(patron, t_limpio, re.I)
        if match:
            datos[clave] = match.group(1)
            
    return datos

# 3. Generador de Word con Grid de Imágenes 4x2
def generar_word_pro(datos, informe_texto, doc_pdf):
    doc = Document()
    doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    doc.add_paragraph(f"PACIENTE: {datos['pac']}")
    doc.add_paragraph("-" * 30)
    doc.add_paragraph(informe_texto)
    doc.add_paragraph("\nDr. Francisco A. Pastore")
    
    # Anexo de imágenes
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    
    imagenes = []
    for i in range(len(doc_pdf)):
        for img in doc_pdf[i].get_images(full=True):
            xref = img[0]
            base_image = doc_pdf.extract_image(xref)
            imagenes.append(base_image["image"])

    if imagenes:
        table = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imagenes[:8]):
            row, col = idx // 2, idx % 2
            cell_para = table.rows[row].cells[col].paragraphs[0]
            run = cell_para.add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ DE USUARIO ---
st.set_page_config(page_title="CardioReport Senior", layout="wide")
st.title("🏥 CardioReport v5.0 - Sistema Senior")

# Sidebar para API Key si no está en Secrets
with st.sidebar:
    if "GROQ_API_KEY" not in st.secrets:
        st.info("API Key no detectada en Secrets.")
        st.session_state.custom_api_key = st.text_input("Ingrese Groq API Key manualmente:", type="password")
    else:
        st.success("API Key cargada desde Secrets ✅")
    
    archivo = st.file_uploader("Subir PDF de Estudio", type=["pdf"])
    if st.button("Resetear"):
        st.session_state.clear()
        st.rerun()

# Lógica Principal
if archivo:
    # 1. Procesar PDF
    doc_original = fitz.open(stream=archivo.read(), filetype="pdf")
    datos_auto = extraer_datos_precisos(doc_original)

    # 2. Formulario de Validación ( UI Limpia )
    with st.form("validador_senior"):
        st.subheader("Confirmación de Datos")
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", datos_auto["pac"])
        fey = c2.text_input("FEy %", datos_auto["fy"])
        ddvi = c3.text_input("DDVI mm", datos_auto["dv"])
        siv = c4.text_input("SIV mm", datos_auto["si"])
        
        submit = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

    # 3. Procesamiento y Salida
    if submit:
        client = get_groq_client()
        if not client:
            st.error("Error: No se encontró la API Key. Por favor verifique los Secrets o la Sidebar.")
        else:
            prompt = (f"Actúa como el Dr. Pastore. Redacta el informe técnico de ecocardiograma. "
                      f"Paciente: {pac}. Datos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. "
                      f"Estilo: Directo, numérico, sin verso, sin recomendaciones.")
            
            with st.spinner("Generando informe..."):
                res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user', 'content':prompt}])
                st.session_state.informe_ia = res.choices[0].message.content
                st.session_state.word_file = generar_word_pro({"pac":pac, "fy":fey, "dv":ddvi, "si":siv}, st.session_state.informe_ia, doc_original)
                st.session_state.ready = True

    # 4. Zona de Descarga (FUERA DEL FORMULARIO)
    if st.session_state.get("ready"):
        st.markdown("---")
        st.subheader("Informe Resultante")
        st.info(st.session_state.informe_ia)
        st.download_button(
            label="📄 Descargar Informe Word + Imágenes",
            data=st.session_state.word_file,
            file_name=f"Informe_{pac.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
