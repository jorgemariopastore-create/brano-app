
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
            # Resaltar encabezados de sección en negrita
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
            with st.spinner("Analizando estudio y redactando informe..."):
                try:
                    # Lectura de TODAS las páginas del PDF
                    texto_completo = ""
                    # CORRECCIÓN: Se añadió el ':' al final de la línea del 'with'
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_completo += pagina.get_text()
                    
                    # Limpieza para que la IA no se confunda con caracteres de tablas
                    texto_limpio = texto_completo.replace('"', ' ').replace("'", " ").replace(",", " ")
                    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT UNIVERSAL (Válido para cualquier paciente)
                    prompt_universal = f"""
                    ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES REDACTAR UN INFORME MÉDICO PROFESIONAL.
                    
                    TEXTO DEL ESTUDIO A ANALIZAR: 
                    {texto_limpio}

                    INSTRUCCIONES DE EXTRACCIÓN:
                    1. DATOS: Identifica Nombre, ID y Fecha de estudio.
                    2. SECCIÓN I: Busca diámetros de VI (DDVI/LVIDd, DSVI/LVIDs), Aurícula (AI/DDAI), Septum (DDSIV) y Pared (DDPP).
                    3. SECCIÓN II: Busca la FEy (%) y describe la motilidad (busca palabras como Hipocinesia, Aquinesia, Disquinesia o Normal).
                    4. SECCIÓN III: Busca datos de Vena Cava y hallazgos del Doppler (E/A, E/e, presiones).
                    5. SECCIÓN IV (CONCLUSIÓN): 
                       - REGLA: Si FEy < 35% y DDVI > 57mm -> "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".
                       - Si no cumple, redacta una conclusión profesional basada en los hallazgos técnicos.

                    FORMATO DE SALIDA (ESTRICTO):
                    DATOS DEL PACIENTE:
                    I. EVALUACIÓN ANATÓMICA:
                    II. FUNCIÓN VENTRICULAR:
                    III. EVALUACIÓN HEMODINÁMICA:
                    IV. CONCLUSIÓN: (En negrita)

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Eres un transcriptor médico experto. Extrae los valores numéricos con precisión ignorando ruidos de formato."},
                            {"role": "user", "content": prompt_universal}
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
                    st.error(f"Error al procesar el archivo: {e}")
else:
    st.error("⚠️ No se encontró la API KEY en los Secrets de Streamlit.")
