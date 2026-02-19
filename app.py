
import streamlit as st
from groq import Groq
import fitz
import re
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURACIÓN DE ESTADO INICIAL ---
if "id_archivo" not in st.session_state: st.session_state.id_archivo = ""
if "datos" not in st.session_state: st.session_state.datos = {}
if "informe_ia" not in st.session_state: st.session_state.informe_ia = ""

def extraer_datos_fieles(doc_pdf):
    texto = ""
    for pag in doc_pdf: texto += pag.get_text()
    # Limpieza extrema de caracteres invisibles y ruidos de tabla
    t = re.sub(r'[^a-zA-Z0-9\s:/,.-]', ' ', texto)
    t = " ".join(t.split()) 
    
    # Inicialización limpia
    d = {"pac": "NO DETECTADO", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": "", "ai": ""}
    
    # Detección de Nombre
    m_pac = re.search(r"Paciente\s*:\s*([A-Z\s]+?)(?:\s*Fecha|Edad|DNI|$)", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    # Detección de Fecha
    m_fec = re.search(r"Fecha\s*:\s*(\d{2}/\d{2}/\d{4})", t, re.I)
    if m_fec: d["fec"] = m_fec.group(1)

    # Diccionario de búsqueda de métricas
    patterns = {
        "ddvi": r"DDVI\s*(\d+)", 
        "dsvi": r"DSVI\s*(\d+)", 
        "siv": r"SIV\s*(\d+)", 
        "pp": r"PP\s*(\d+)", 
        "ai": r"AI\s*(\d+)",
        "fey": r"eyección\s*del\s*VI\s*(\d+)"
    }
    
    for k, v in patterns.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
            
    return d

# --- INTERFAZ ---
st.title("🏥 CardioReport Senior v14.0")

archivo = st.file_uploader("Subir PDF del Estudio", type=["pdf"])

if archivo:
    # CLAVE SENIOR: Si el nombre o tamaño cambia, FORZAMOS el reset
    nuevo_id = f"{archivo.name}_{archivo.size}"
    
    if st.session_state.id_archivo != nuevo_id:
        st.session_state.id_archivo = nuevo_id
        # Abrimos y extraemos de inmediato para el nuevo paciente
        pdf_tmp = fitz.open(stream=archivo.read(), filetype="pdf")
        st.session_state.datos = extraer_datos_fieles(pdf_tmp)
        st.session_state.informe_ia = "" # Limpia el texto de Alicia
        st.rerun() # Reinicia la app con los nuevos datos cargados

    d = st.session_state.datos

    # FORMULARIO DE VALIDACIÓN
    with st.form("validador_estricto"):
        st.subheader(f"Paciente: {d['pac']}")
        c1, c2, c3 = st.columns([2,1,1])
        pac = c1.text_input("Nombre completo", d["pac"])
        fec = c2.text_input("Fecha", d["fec"])
        edad = c3.text_input("Edad", d["edad"])
        
        c4, c5 = st.columns(2)
        peso = c4.text_input("Peso (kg)", "")
        alt = c5.text_input("Altura (cm)", "")
        
        st.markdown("**Valores Técnicos Detectados**")
        c6, c7, c8, c9, c10 = st.columns(5)
        ddvi = c6.text_input("DDVI", d["ddvi"])
        dsvi = c7.text_input("DSVI", d["dsvi"])
        siv = c8.text_input("SIV", d["siv"])
        pp = c9.text_input("PP", d["pp"])
        fey = c10.text_input("FEy %", d["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL"):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            prompt = f"""Actúa como el Dr. Pastore. Redacta el cuerpo de un informe detallado.
            DATOS: DDVI {ddvi}mm, DSVI {dsvi}mm, SIV {siv}mm, PP {pp}mm, FEy {fey}%.
            REGLAS: Justificado, sin repetir nombre, secciones: HALLAZGOS, VALVULAS, CONCLUSION técnico."""
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.informe_ia = res.choices[0].message.content
            # Aquí iría la función de Word con justificado y letra 12pt

    if st.session_state.informe_ia:
        st.markdown("---")
        st.info(st.session_state.informe_ia)
        # Botón de descarga...
