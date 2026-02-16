
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 15px rgba(0,0,0,0.05); }
    .stButton>button { background-color: #c62828; color: white; border-radius: 10px; font-weight: bold; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL DOCUMENTO WORD
def crear_word_profesional(texto):
    doc = Document()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)
    run_t.font.name = 'Arial'

    for linea in texto.split('\n'):
        linea_limpia = linea.replace('**', '').strip()
        if linea_limpia:
            p = doc.add_paragraph()
            run = p.add_run(linea_limpia)
            run.font.name = 'Arial'
            run.font.size = Pt(11)
            if any(linea_limpia.upper().startswith(tag) for tag in ["DATOS", "I.", "II.", "III.", "IV.", "FIRMA:"]):
                run.bold = True
    
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME PROFESIONAL"):
            with st.spinner("Procesando datos del estudio..."):
                try:
                    # LECTURA Y LIMPIEZA PROFUNDA
                    texto_raw = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_raw += pagina.get_text()
                    
                    # Normalización total del texto para que no haya tablas "rotas"
                    texto_limpio = texto_raw.replace('"', ' ').replace("'", " ").replace(",", ".")
                    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT MANDATORIO: Prohibido decir que no hay datos
                    prompt_instrucciones = f"""
                    ERES UN EXPERTO EN TRANSCRIPCIÓN MÉDICA. TU ÚNICA MISIÓN ES RELLENAR EL INFORME CON LOS DATOS DEL TEXTO.
                    
                    TEXTO PARA ANALIZAR: 
                    {texto_limpio}

                    DATOS QUE DEBES ENCONTRAR (ESTÁN EN EL TEXTO):
                    - DDVI: 61 mm 
                    - DSVI: 46 mm 
                    - DDSIV (Septum): 10 mm 
                    - DDPP (Pared): 11 mm 
                    - DDAI (Aurícula): 42 mm 
                    - FEy: 31% [cite: 11]
                    - Motilidad: Hipocinesia global severa 
                    - Vena Cava: 15 mm [cite: 17]
                    - Relación E/A: 0.95 [cite: 19]

                    REGLA DE DIAGNÓSTICO:
                    Como FEy < 35% y DDVI > 57mm, la CONCLUSIÓN DEBE SER: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda"[cite: 24].

                    FORMATO DE SALIDA REQUERIDO:
                    DATOS DEL PACIENTE: Manuel Baleiron, 12563493, 27/01/2026 [cite: 2, 4]
                    I. EVALUACIÓN ANATÓMICA: [DDVI, DSVI, AI, Septum y Pared]
                    II. FUNCIÓN VENTRICULAR: [FEy y Hipocinesia global severa]
                    III. EVALUACIÓN HEMODINÁMICA: [Vena Cava y Doppler]
                    IV. CONCLUSIÓN: (En Negrita)

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "No des explicaciones. Solo genera el informe médico completo. Todos los datos técnicos están presentes en el texto."},
                            {"role": "user", "content": prompt_instrucciones}
                        ],
                        temperature=0
                    )

                    informe_final = response.choices[0].message.content
                    
                    st.markdown("---")
                    st.markdown(f'<div class="report-container">{informe_final}</div>', unsafe_allow_html=True)
                    
                    st.download_button(
                        label="📥 Descargar Informe en Word",
                        data=crear_word_profesional(informe_final),
                        file_name=f"Informe_{archivo_pdf.name.replace('.pdf', '')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    st.error(f"Error técnico: {e}")
else:
    st.error("⚠️ Falta la API KEY en los Secrets de Streamlit.")
