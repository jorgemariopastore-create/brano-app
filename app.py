
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")

# Estilo visual
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #d32f2f; color: white; font-weight: bold; border-radius: 8px; }
    .report-box { background-color: white; padding: 20px; border: 1px solid #d1d1d1; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Dr. Pastore - v4.0")
st.info("Esta versión fuerza la extracción de datos de tablas técnicas (Caso Baleiron corregido).")

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key:", type="password")

def crear_word(texto):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run.bold = True
    run.font.size = Pt(14)
    for linea in texto.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        parrafo = doc.add_paragraph()
        run_l = parrafo.add_run(linea)
        if any(linea.startswith(x) for x in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run_l.bold = True
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivo_subido = st.file_uploader("Cargar PDF del Estudio", type=["pdf"])

    if archivo_subido and st.button("PROCESAR ESTUDIO MÉDICO"):
        with st.spinner("Analizando datos..."):
            texto_extraido = ""
            with fitz.open(stream=archivo_subido.read(), filetype="pdf") as doc:
                for pagina in doc:
                    texto_extraido += pagina.get_text()

            # PROMPT REFORZADO PARA EVITAR EL "NO DISPONIBLE"
            prompt = f"""
            Eres el Dr. Francisco Alberto Pastore. Debes generar un informe basado en el texto adjunto. 
            IMPORTANTE: Los datos están presentes en tablas. No ignores los números.
            
            TEXTO CRUDO:
            {texto_extraido}

            INSTRUCCIONES DE EXTRACCIÓN:
            - DDVI: Búscalo como 'DDVI' o 'LVIDd'. Si está en cm (6.1), conviértelo a mm (61 mm).
            - DSVI: Búscalo como 'DSVI' o 'LVIDs'.
            - FEy: Búscalo como 'FEy', 'EF', 'Simpson' o 'Teich'.
            - AI: Búscalo como 'AI', 'Aurícula Izq' o 'LA'.
            
            CRITERIOS MÉDICOS OBLIGATORIOS:
            - Si FEy < 35% y DDVI > 57 mm (como en el caso de Baleiron): La CONCLUSIÓN debe ser "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica".
            - No uses la frase "No disponible" si ves números en el texto. Haz tu mejor esfuerzo médico por transcribir lo que ves.

            ESTRUCTURA:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, AI, Septum, Pared)
            II. FUNCIÓN VENTRICULAR: (FEy y motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Valvular y Doppler)
            IV. CONCLUSIÓN: (Diagnóstico final en negrita)

            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            """

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Eres un cardiólogo experto. Tu prioridad es extraer valores numéricos de los informes técnicos."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0 # Temperatura 0 para evitar que invente o se rinda
                )
                
                resultado = response.choices[0].message.content
                st.markdown(f'<div class="report-box">{resultado}</div>', unsafe_allow_html=True)
                st.download_button("📥 Descargar Word", crear_word(resultado), f"Informe_{archivo_subido.name}.docx")
            except Exception as e:
                st.error(f"Error: {e}")
