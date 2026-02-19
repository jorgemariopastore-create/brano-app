
import streamlit as st
from groq import Groq
import fitz
import re
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURACIÓN DE ESTADO ---
# Usamos un hash del archivo para saber si cambió
if "file_hash" not in st.session_state: st.session_state.file_hash = None
if "datos_extraidos" not in st.session_state: st.session_state.datos_extraidos = {}
if "informe_ia" not in st.session_state: st.session_state.informe_ia = ""

def extraer_datos_limpios(doc_pdf):
    texto = ""
    for pag in doc_pdf: texto += pag.get_text()
    # Limpieza profunda de ruidos del PDF (comas, comillas, saltos de línea)
    t = re.sub(r'[\"\'\r\t]', '', texto)
    t = re.sub(r'\n+', ' ', t)
    
    # Buscamos valores reales del PDF actual
    d = {"pac": "NO DETECTADO", "fec": "", "edad": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": "", "ai": ""}
    
    # Regex específicas para la estructura del ecógrafo del Dr.
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|DNI|$)", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    m_fec = re.search(r"Fecha(?:\s*de\s*estudio)?:\s*(\d{2}/\d{2}/\d{4})", t, re.I)
    if m_fec: d["fec"] = m_fec.group(1)

    # Patrones numéricos precisos
    reg = {
        "ddvi": r"DDVI\s+(\d+)", 
        "dsvi": r"DSVI\s+(\d+)", 
        "siv": r"(?:DDSIV|SIV)\s+(\d+)", 
        "pp": r"(?:DDPP|PP)\s+(\d+)", 
        "fey": r"(?:eyección\s+del\s+VI|FA)\s+(\d+)", 
        "ai": r"(?:DDAI|AI)\s+(\d+)"
    }
    
    for k, v in reg.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
    
    # Ajuste de FEy si es FA (Fórmula de Teichholz simplificada si solo hay FA)
    if d["fey"] and int(d["fey"]) < 45: # Probablemente es FA, convertir a FEy
        d["fey"] = str(round(int(d["fey"]) * 1.76))
        
    return d

# --- INTERFAZ ---
st.title("🏥 CardioReport Senior - Dr. Pastore")

with st.sidebar:
    archivo = st.file_uploader("Subir PDF del Paciente", type=["pdf"])
    if archivo:
        # Si el archivo es nuevo, reseteamos todo
        nuevo_hash = archivo.name + str(archivo.size)
        if st.session_state.file_hash != nuevo_hash:
            st.session_state.file_hash = nuevo_hash
            st.session_state.datos_extraidos = {}
            st.session_state.informe_ia = ""
            st.session_state.word_doc = None

if archivo:
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    
    # Extraer datos solo una vez por archivo
    if not st.session_state.datos_extraidos:
        st.session_state.datos_extraidos = extraer_datos_limpios(pdf)
    
    d = st.session_state.datos_extraidos

    with st.form("validador_principal"):
        st.subheader("Validación de Datos del Paciente")
        c1, c2, c3 = st.columns([2,1,1])
        pac = c1.text_input("Paciente", d["pac"])
        fec = c2.text_input("Fecha", d["fec"])
        edad = c3.text_input("Edad", d["edad"])
        
        c4, c5 = st.columns(2)
        peso = c4.text_input("Peso (kg)", "")
        alt = c5.text_input("Altura (cm)", "")
        
        st.write("**Parámetros Técnicos**")
        c6, c7, c8, c9, c10 = st.columns(5)
        ddvi = c6.text_input("DDVI", d["ddvi"])
        dsvi = c7.text_input("DSVI", d["dsvi"])
        siv = c8.text_input("SIV", d["siv"])
        pp = c9.text_input("PP", d["pp"])
        fey = c10.text_input("FEy %", d["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME MÉDICO"):
            if not pac or pac == "NO DETECTADO":
                st.error("Por favor, verifique el nombre del paciente.")
            else:
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                prompt = f"""Actúa como el Dr. Pastore. Redacta un informe ecocardiográfico.
                DATOS: DDVI {ddvi}mm, DSVI {dsvi}mm, SIV {siv}mm, PP {pp}mm, FEy {fey}%.
                ESTRUCTURA: HALLAZGOS (con espesores y motilidad), VALVULAS y CONCLUSION técnica.
                REGLAS: Justificado, letra Arial 12, sin repetir nombre en el cuerpo, estilo seco."""
                
                with st.spinner("Procesando informe técnico..."):
                    res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
                    st.session_state.informe_ia = res.choices[0].message.content
                    # Aquí llamaríamos a la función crear_word_profesional (incluida en el backend)
                    # st.session_state.word_doc = crear_word_profesional(...)

    if st.session_state.informe_ia:
        st.markdown("---")
        st.subheader("Vista Previa")
        st.info(st.session_state.informe_ia)
        # El botón de descarga aparecería aquí
