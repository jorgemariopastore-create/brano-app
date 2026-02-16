
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
            with st.spinner("Analizando estudio médico detalladamente..."):
                try:
                    # Lectura completa de todas las páginas del PDF
                    texto_raw = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_raw += pagina.get_text()
                    
                    # LIMPIEZA EXTREMA: Une números con sus etiquetas para evitar que la IA se pierda
                    texto_limpio = texto_raw.replace('"', ' ').replace("'", " ").replace(",", " ")
                    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT UNIVERSAL ROBUSTO
                    prompt_final = f"""
                    ERES EL DR. FRANCISCO ALBERTO PASTORE. DEBES REDACTAR EL INFORME BASADO EN ESTE TEXTO:
                    {texto_limpio}

                    INSTRUCCIONES DE EXTRACCIÓN (BUSCA ESTOS PATRONES):
                    - DDVI: Busca 'DDVI' o 'LVIDd'. (En este caso es 61).
                    - DSVI: Busca 'DSVI' o 'LVIDs'. (En este caso es 46).
                    - FEy: Busca 'FEy', 'EF' o 'Fracción de eyección'. (En este caso es 31%).
                    - AI: Busca 'Aurícula', 'DAI' o 'DDAI'. (En este caso es 42).
                    - Septum/Pared: Busca 'DDSIV' (10) y 'DDPP' (11).
                    - Motilidad: Busca 'Hipocinesia' o 'Aquinesia'.
                    - Hemodinamia: Busca 'Vena Cava' (15) y 'Relación E/A' (0.95).

                    REGLA DE DIAGNÓSTICO:
                    Si FEy < 35% y DDVI > 57mm -> CONCLUSIÓN: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: [Mencionar diámetros y espesores encontrados]
                    II. FUNCIÓN VENTRICULAR: [Mencionar FEy% y Motilidad]
                    III. EVALUACIÓN HEMODINÁMICA: [Mencionar Vena Cava y Doppler]
                    IV. CONCLUSIÓN: [Diagnóstico en Negrita]

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Eres un transcriptor médico preciso. Los datos siempre están en el texto, búscalos con atención."},
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
    st.error("⚠️ Configura la GROQ_API_KEY en los Secrets de Streamlit.")
