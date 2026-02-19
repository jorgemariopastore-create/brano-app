
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

# Intentar cargar la API Key de secrets
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

# --- FUNCIONES DE EXTRACCIÓN Y PROCESAMIENTO ---

def extraer_datos_pdf(doc_pdf):
    """Extrae texto y busca patrones de datos del SonoScape."""
    texto_total = ""
    for pagina in doc_pdf:
        texto_total += pagina.get_text()
    
    # Limpieza para que las tablas no interfieran
    t = texto_total.replace('"', '').replace('\n', ' ').replace('\r', ' ')
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # 1. Nombre del Paciente (Busca patrón 'Paciente: NOMBRE')
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:\s*Fecha|\s*Estudio|$)", t, re.I)
    if m_pac:
        datos["pac"] = m_pac.group(1).strip()
    
    # 2. DDVI (Busca DDVI seguido de número)
    m_dv = re.search(r"DDVI\s*(\d+)", t)
    if m_dv: datos["dv"] = m_dv.group(1)
    
    # 3. SIV / DDSIV
    m_si = re.search(r"(?:DDSIV|SIV)\s*(\d+)", t)
    if m_si: datos["si"] = m_si.group(1)
    
    # 4. FEy (Prioriza el texto del informe: 'eyección del VI X%')
    m_fe = re.search(r"eyección del VI\s*(\d+)", t)
    if m_fe:
        datos["fy"] = m_fe.group(1)
    else:
        # Respaldo: busca FA (Fracción de acortamiento)
        m_fa = re.search(r"FA\s*(\d+)", t)
        if m_fa: datos["fy"] = str(round(float(m_fa.group(1)) * 1.76))
        
    return datos

def crear_docx_pastore(datos, texto_informe, doc_pdf):
    """Genera el Word con el informe y el anexo de imágenes 4x2."""
    doc = Document()
    doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    
    doc.add_paragraph(f"PACIENTE: {datos['pac']}")
    doc.add_paragraph("-" * 40)
    
    # Informe de la IA
    doc.add_paragraph(texto_informe)
    
    doc.add_paragraph("\n" + "-" * 20)
    doc.add_paragraph("Dr. Francisco A. Pastore")

    # ANEXO DE IMÁGENES
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    
    # Recolectar imágenes del PDF (Suelen estar al final)
    imagenes = []
    for i in range(len(doc_pdf)):
        page = doc_pdf[i]
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc_pdf.extract_image(xref)
            imagenes.append(base_image["image"])

    if imagenes:
        # Crear tabla de 4 filas x 2 columnas
        tabla = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imagenes[:8]): # Máximo 8 fotos
            fila = idx // 2
            col = idx % 2
            celda = tabla.rows[fila].cells[col]
            parrafo = celda.paragraphs[0]
            run = parrafo.add_run()
            # Ajustamos el ancho a 3 pulgadas para que quepan 2 por fila
            run.add_picture(io.BytesIO(img_data), width=Inches(3.0))

    target = io.BytesIO()
    doc.save(target)
    target.seek(0)
    return target

# --- INTERFAZ STREAMLIT ---

st.title("🏥 Asistente Cardio v3.5 (Solo PDF)")

# Inicializar estados
if "datos_validados" not in st.session_state:
    st.session_state.datos_validados = None
    st.session_state.informe_ia = ""
    st.session_state.word_ready = None

with st.sidebar:
    st.header("Carga de Estudio")
    archivo_pdf = st.file_uploader("Subir PDF del paciente", type=["pdf"])
    if st.button("🔄 Reiniciar"):
        st.session_state.clear()
        st.rerun()

if archivo_pdf and GROQ_KEY:
    # Procesar PDF solo una vez
    if st.session_state.datos_validados is None:
        doc = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
        st.session_state.doc_original = doc
        st.session_state.datos_validados = extraer_datos_pdf(doc)

    # 1. Formulario de Validación
    with st.form("editor_datos"):
        st.subheader("🔍 Validar Datos Extraídos")
        d = st.session_state.datos_validados
        c1, c2, c3, c4 = st.columns(4)
        
        pac_edit = c1.text_input("Paciente", d["pac"])
        fey_edit = c2.text_input("FEy %", d["fy"])
        ddvi_edit = c3.text_input("DDVI mm", d["dv"])
        siv_edit = c4.text_input("SIV mm", d["si"])
        
        submit = st.form_submit_button("🚀 GENERAR INFORME")

    # 2. Lógica al presionar Generar
    if submit:
        # Actualizar sesión con ediciones del médico
        st.session_state.datos_validados.update({
            "pac": pac_edit, "fy": fey_edit, "dv": ddvi_edit, "si": siv_edit
        })
        
        client = Groq(api_key=GROQ_KEY)
        
        # PROMPT "ANTI-VERSO" ESTILO PASTORE
        prompt = (f"Actúa como el Dr. Pastore. Redacta las conclusiones del ecocardiograma. "
                  f"Paciente: {pac_edit}. Hallazgos: DDVI {ddvi_edit}mm, SIV {siv_edit}mm, FEy {fey_edit}%. "
                  f"Instrucciones: Estilo seco, clínico y puramente numérico. "
                  f"No incluyas introducciones, ni saludos, ni recomendaciones al paciente. "
                  f"Escribe solo los hallazgos técnicos.")
        
        with st.spinner("IA redactando informe técnico..."):
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', 
                                               messages=[{'role':'user', 'content':prompt}])
            st.session_state.informe_ia = res.choices[0].message.content
            
            # Crear el archivo Word
            st.session_state.word_ready = crear_docx_pastore(
                st.session_state.datos_validados, 
                st.session_state.informe_ia, 
                st.session_state.doc_original
            )

    # 3. Mostrar resultado y descarga (FUERA DEL FORMULARIO)
    if st.session_state.informe_ia:
        st.markdown("---")
        st.subheader("Informe Sugerido")
        st.info(st.session_state.informe_ia)
        
        st.download_button(
            label="📥 DESCARGAR INFORME EN WORD (CON IMÁGENES)",
            data=st.session_state.word_ready,
            file_name=f"Informe_{pac_edit.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

elif not GROQ_KEY:
    st.error("Falta la API Key de Groq en los Secrets de Streamlit.")
else:
    st.info("Por favor, sube el PDF del estudio para comenzar.")
