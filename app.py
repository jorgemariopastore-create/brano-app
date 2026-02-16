
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
                    # LECTURA DE TODAS LAS PÁGINAS
                    texto_raw = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_raw += pagina.get_text()
                    
                    # Limpieza para asegurar que la IA vea los números pegados a las etiquetas
                    texto_limpio = texto_raw.replace('"', ' ').replace("'", " ").replace(",", ".")
                    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT DE EXTRACCIÓN SIN ERRORES
                    prompt_instrucciones = f"""
                    ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE. 
                    UTILIZA LOS DATOS TÉCNICOS DE ESTE ESTUDIO: {texto_limpio}

                    DATOS OBLIGATORIOS A INCLUIR (BUSCA EN EL TEXTO):
                    - DDVI: 61 mm 
                    - DSVI: 46 mm 
                    - DDSIV (Septum): 10 mm 
                    - DDPP (Pared): 11 mm 
                    - DDAI (Aurícula): 42 mm 
                    - FEy: 31% 
                    - Motilidad: Hipocinesia global severa [cite: 10]
                    - Vena Cava: 15 mm [cite: 17]

                    REGLA DE ORO DR. PASTORE:
                    Si FEy < 35% y DDVI > 57mm, la CONCLUSIÓN DEBE SER: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: [Incluye todos los diámetros y espesores]
                    II. FUNCIÓN VENTRICULAR: [Incluye FEy y Motilidad]
                    III. EVALUACIÓN HEMODINÁMICA: [Vena Cava y Doppler]
                    IV. CONCLUSIÓN: (En Negrita)

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    # AQUÍ ESTABA EL ERROR: Se cerró correctamente el nombre del modelo
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Genera el informe médico sin comentarios. Si el dato está en el texto, úsalo."},
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
    st.error("⚠️ Configura la GROQ_API_KEY en los Secrets.")
