
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
            with st.spinner("Extrayendo datos técnicos de todas las páginas..."):
                try:
                    # Lectura y limpieza profunda del PDF
                    texto_raw = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_raw += pagina.get_text("text")
                    
                    # Limpieza para unir números con sus etiquetas (ej: DDVI 61)
                    texto_procesado = texto_raw.replace('"', ' ').replace("'", " ")
                    texto_procesado = re.sub(r'\s+', ' ', texto_procesado)

                    client = Groq(api_key=api_key)

                    # PROMPT DE EXTRACCIÓN TÉCNICA (Sin excusas)
                    prompt_final = f"""
                    ACTÚA COMO UN ANALISTA DE DATOS MÉDICOS. 
                    TU MISIÓN: Extraer valores numéricos de este texto: {texto_procesado}

                    BUSCA ESTAS ETIQUETAS Y SUS VALORES:
                    - DDVI / LVIDd: (ej. 61)
                    - DSVI / LVIDs: (ej. 46)
                    - FEy / EF / Fracción de eyección: (ej. 31%)
                    - AI / DDAI / LA: (ej. 42)
                    - Septum / DDSIV: (ej. 10)
                    - Pared / DDPP: (ej. 11)
                    - Vena Cava: (ej. 15)
                    - Doppler E/A: (ej. 0,95)

                    INSTRUCCIÓN DE DIAGNÓSTICO (CRITERIO PASTORE):
                    - Si FEy < 35% y DDVI > 57mm -> CONCLUSIÓN: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: [Valores de diámetros y espesores]
                    II. FUNCIÓN VENTRICULAR: [FEy y descripción de Motilidad como 'Hipocinesia global']
                    III. EVALUACIÓN HEMODINÁMICA: [Vena Cava y Doppler]
                    IV. CONCLUSIÓN: [Diagnóstico en Negrita]

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Eres un transcriptor experto. Tu única tarea es encontrar los números en el texto y completar el informe. Los datos SIEMPRE están presentes en el texto proporcionado."},
                            {"role": "user", "content": prompt_final}
                        ],
                        temperature=0
                    )

                    informe_final = response.choices[0].message.content
                    st.markdown("---")
                    st.markdown(informe_final)
                    
                    st.download_button(
                        label="📥 Descargar Informe en Word",
                        data=crear_word_profesional(informe_final),
                        file_name=f"Informe_{archivo_pdf.name.replace('.pdf', '')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.error("⚠️ Configura la GROQ_API_KEY en Secrets.")
