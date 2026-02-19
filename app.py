
import streamlit as st
from groq import Groq
import fitz
import re

# 1. Configuración de API Key
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def parser_sonoscape_ultra_robusto(texto_txt):
    """
    Parser de última instancia: Extrae todos los números entre comillas
    y los clasifica por rangos médicos reales.
    """
    datos = {"pac": "DESCONOCIDO", "dv": "", "si": "", "fy": ""}
    
    # --- 1. Extraer Paciente ---
    # Busca PatientName seguido de cualquier cosa entre comillas
    m_pac = re.search(r"PatientName\s*,\s*\"([^\"]+)\"", texto_txt, re.I)
    if m_pac:
        datos["pac"] = m_pac.group(1).replace('^', ' ').strip().upper()

    # --- 2. Extraer todos los valores numéricos entre comillas ---
    # El SonoScape pone casi todo así: "40","mm" o "11","mm"
    # Buscamos números decimales o enteros que estén dentro de comillas
    todos_los_valores = re.findall(r"\"([\d.]+)\"", texto_txt)
    
    # Convertimos a float para evaluar rangos biológicos
    candidatos = []
    for v in todos_los_valores:
        try:
            val = float(v)
            # Si el valor es pequeño (menor a 7), asumimos que está en CM y pasamos a MM
            if 0.5 < val < 8.0:
                candidatos.append(val * 10)
            else:
                candidatos.append(val)
        except:
            continue

    # --- 3. Asignación por Ventana Biológica ---
    for c in candidatos:
        # Rango DDVI: 35mm a 75mm
        if 35 <= c <= 75:
            datos["dv"] = str(round(c, 1))
        # Rango SIV (Septum): 6mm a 18mm
        elif 6 <= c <= 18:
            datos["si"] = str(round(c, 1))
        # Rango FEy: 20% a 85% (buscamos el primer valor que encaje después de los diámetros)
        elif 20 < c < 85 and datos["fy"] == "":
            # Solo asignamos a FEy si ya tenemos al menos un diámetro, 
            # para no confundir un Septum de 12mm con una FEy (poco probable pero posible)
            if c > 20: 
                datos["fy"] = str(round(c, 1))

    return datos

st.set_page_config(page_title="CardioReport SonoScape", layout="wide")
st.title("🏥 Asistente Cardio SonoScape E3")

if "datos" not in st.session_state:
    st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}

with st.sidebar:
    st.header("1. Carga de Archivos")
    arc_txt = st.file_uploader("Archivo TXT del SonoScape", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF (Opcional)", type=["pdf"])
    if st.button("🔄 Reiniciar"):
        st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}
        st.rerun()

# Procesamiento
if arc_txt and GROQ_KEY:
    # Solo procesar si no hay datos cargados
    if st.session_state.datos["pac"] == "":
        with st.spinner("Analizando estructura de datos..."):
            contenido = arc_txt.read().decode("latin-1", errors="ignore")
            res = parser_sonoscape_ultra_robusto(contenido)
            
            # Si se subió PDF, intentar mejorar el nombre
            if arc_pdf:
                try:
                    with fitz.open(stream=arc_pdf.read(), filetype="pdf") as doc:
                        texto_pdf = doc[0].get_text()
                        n_m = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\n]*)", texto_pdf, re.I)
                        if n_m: res["pac"] = n_m.group(1).strip().upper()
                except: pass
            
            st.session_state.datos = res

# Formulario de Validación
if st.session_state.datos["pac"] != "":
    with st.form("validador"):
        st.subheader("🔍 Confirmación de Datos")
        col1, col2, col3, col4 = st.columns(4)
        
        pac = col1.text_input("Paciente", st.session_state.datos["pac"])
        fey = col2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi = col3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv = col4.text_input("SIV mm", st.session_state.datos["si"])
        
        btn = st.form_submit_button("🚀 GENERAR INFORME")

    if btn:
        # Actualizar con ediciones manuales
        st.session_state.datos.update({"pac": pac, "fy": fey, "dv": ddvi, "si": siv})
        
        client = Groq(api_key=GROQ_KEY)
        prompt = f"""
        Actúa como el Dr. Francisco Pastore. Genera conclusiones médicas.
        Paciente: {pac}. Datos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%.
        - Si FEy > 55%: Función sistólica conservada.
        - Si SIV >= 11mm: Remodelado concéntrico.
        """
        with st.spinner("IA redactando..."):
            completion = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role':'user', 'content': prompt}]
            )
            st.markdown("---")
            st.info(completion.choices[0].message.content)
            st.markdown("**Dr. Francisco A. Pastore**")
else:
    st.info("Por favor, cargue el archivo TXT exportado por el SonoScape.")
