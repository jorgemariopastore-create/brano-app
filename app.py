
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de interfaz
st.set_page_config(page_title="CardioReport AI Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #d32f2f; color: white; font-weight: bold; border-radius: 8px; height: 3em; }
    .report-box { background-color: #ffffff; padding: 25px; border-radius: 10px; border: 1px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Dr. Pastore")
st.write("Detección automática de valores críticos y diagnósticos de severidad.")

# API Key de Groq
api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key:", type="password")

def crear_word(texto):
    doc = Document()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run.bold = True
    run.font.size = Pt(14)
    
    for linea in texto.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        p = doc.add_paragraph()
        r = p.add_run(linea)
        if any(linea.startswith(x) for x in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            r.bold = True
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivo = st.file_uploader("Cargar PDF del Paciente", type=["pdf"])

    if archivo and st.button("PROCESAR ESTUDIO MÉDICO"):
        with st.spinner("Extrayendo datos y aplicando criterios de cardiología..."):
            # 1. Extracción de texto del PDF
            texto_pdf = ""
            with fitz.open(stream=archivo.read(), filetype="pdf") as doc:
                for pagina in doc:
                    texto_pdf += pagina.get_text()

            # 2. Prompt con Lógica Médica Estricta
            prompt_estricto = f"""
            Eres el Dr. Francisco Alberto Pastore. Tu misión es analizar el siguiente texto extraído de un ecógrafo y generar un informe impecable.
            
            TEXTO DEL ESTUDIO:
            {texto_pdf}

            INSTRUCCIONES DE EXTRACCIÓN (PROHIBIDO DECIR "NO DISPONIBLE"):
            - DDVI: Búscalo como 'DDVI', 'LVIDd' o 'Diastolic'. Si dice 6.1 cm, escribe 61 mm.
            - DSVI: Búscalo como 'DSVI', 'LVIDs' o 'Systolic'.
            - FEy: Búscalo como 'FEy', 'EF', 'Simpson' o 'Teich'.
            - MOTILIDAD: Si el texto menciona 'Hipocinesia global', inclúyelo.

            REGLAS DIAGNÓSTICAS (CRITERIO PASTORE):
            - Si FEy < 35%: La CONCLUSIÓN debe ser "Deterioro SEVERO de la función sistólica ventricular izquierda".
            - Si DDVI > 57 mm: Debes incluir "DILATACIÓN del ventrículo izquierdo".
            - Si hay ambos: "Miocardiopatía Dilatada con deterioro severo de la función sistólica".

            FORMATO DE SALIDA:
            DATOS DEL PACIENTE: (Nombre, Edad, ID, Fecha)
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, AI, Septum, Pared en mm)
            II. FUNCIÓN VENTRICULAR: (FEy % y motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Valvular y Doppler)
            IV. CONCLUSIÓN: (Diagnóstico final en NEGRITA)
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            """

            try:
                # Usamos Llama 3 para máxima precisión en tablas
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Eres un cardiólogo que extrae datos con precisión quirúrgica. No omites valores numéricos."},
                        {"role": "user", "content": prompt_estricto}
                    ],
                    temperature=0 # Cero creatividad, 100% precisión
                )
                
                informe = chat.choices[0].message.content
                
                st.markdown(f'<div class="report-box">{informe}</div>', unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=crear_word(informe),
                    file_name=f"Informe_Pastore.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error técnico: {e}")
else:
    st.warning("Introduce tu API Key para activar el sistema.")
