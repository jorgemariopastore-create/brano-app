
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
            with st.spinner("Analizando estudio médico detalladamente..."):
                try:
                    # Lectura completa de todas las páginas del PDF
                    texto_raw = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_raw += pagina.get_text()
                    
                    # Limpieza para que la IA lea bien los números de las tablas
                    texto_limpio = texto_raw.replace('"', ' ').replace("'", " ").replace(",", " ")
                    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT REFORZADO: Ahora busca explícitamente DDSIV y DDPP
                    prompt_final = f"""
                    ERES EL DR. FRANCISCO ALBERTO PASTORE. REDACTA EL INFORME BASADO EN ESTE TEXTO:
                    {texto_limpio}

                    INSTRUCCIONES DE EXTRACCIÓN OBLIGATORIAS:
                    1. DATOS: Nombre, ID y Fecha.
                    2. ANATOMÍA: 
                       - DDVI (LVIDd): [Busca el número cerca de DDVI]
                       - DSVI (LVIDs): [Busca el número cerca de DSVI]
                       - Septum: [Busca el número cerca de 'DDSIV' o 'Septum']
                       - Pared: [Busca el número cerca de 'DDPP' o 'Pared posterior']
                       - Aurícula Izquierda: [Busca el número cerca de 'DDAI' o 'DAI']
                    3. FUNCIÓN: FEy (EF) y descripción de Motilidad (Busca 'Hipocinesia' o 'Aquinesia').
                    4. HEMODINAMIA: Vena Cava y Doppler (Relación E/A, Relación E/e').

                    REGLA MÉDICA DR. PASTORE:
                    Si FEy < 35% y DDVI > 57mm -> CONCLUSIÓN: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE:
                    I. EVALUACIÓN ANATÓMICA: (Incluir todos los diámetros y espesores de septum/pared)
                    II. FUNCIÓN VENTRICULAR: (Incluir FEy y detalle de motilidad)
                    III. EVALUACIÓN HEMODINÁMICA: (Vena Cava y hallazgos Doppler)
                    IV. CONCLUSIÓN: (En Negrita)

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Eres un cardiólogo experto. No omitas datos de la tabla como Septum (DDSIV) o Pared (DDPP)."},
                            {"role": "user", "content": prompt_final}
                        ],
                        temperature=0
                    )

                    informe_texto = response.choices[0].message.content
                    
                    st.markdown("---")
                    st.markdown(informe_texto)
                    
                    st.download_button(
                        label="📥 Descargar Informe en Word",
                        data=crear_word_profesional(informe_texto),
                        file_name=f"Informe_{archivo_pdf.name.replace('.pdf', '')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    st.error(f"Error técnico: {e}")
else:
    st.error("⚠️ Configura la GROQ_API_KEY en los Secrets.")
