
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
            if any(linea_limpia.startswith(tag) for tag in ["DATOS", "I.", "II.", "III.", "IV.", "Firma:"]):
                run.bold = True
    
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. LÓGICA DE LA APLICACIÓN
api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ Error: Configura la GROQ_API_KEY en los Secrets de Streamlit.")
else:
    # EL CARGADOR DEBE ESTAR AL RAS DEL MARGEN (SIN ESPACIOS ADICIONALES)
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME PROFESIONAL"):
            with st.spinner("Redactando informe médico..."):
                try:
                    # Lectura completa de páginas
                    texto_completo = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_completo += pagina.get_text()
                    
                    # Limpieza de caracteres de tabla
                    texto_limpio = texto_completo.replace('"', '').replace("'", "")
                    texto_limpio = re.sub(r'\n+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)

                    # PROMPT PARA REDACCIÓN FORMAL
                    prompt_pastore = f"""
                    ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES REDACTAR EL INFORME FORMAL.
                    TEXTO EXTRAÍDO: {texto_limpio}

                    INSTRUCCIONES:
                    1. Usa los datos reales: DDVI 61mm, DSVI 46mm, AI 42mm, Septum 10mm, Pared 11mm, FEy 31%, Vena Cava 15mm, Doppler E/A 0.95.
                    2. Aplica tu criterio: Como FEy < 35% y DDVI > 57mm, la conclusión DEBE SER "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".
                    3. Mantén un tono médico serio.

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: [Redactar diámetros y espesores]
                    II. FUNCIÓN VENTRICULAR: [Redactar FEy y Motilidad]
                    III. EVALUACIÓN HEMODINÁMICA: [Redactar Vena Cava y Doppler]
                    IV. CONCLUSIÓN: [Diagnóstico en Negrita]

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt_pastore}],
                        temperature=0
                    )

                    informe_final = response.choices[0].message.content
                    
                    # Mostrar resultado en pantalla
                    st.markdown("---")
                    st.info("Informe generado con éxito. Revise los detalles debajo.")
                    st.markdown(informe_final)
                    
                    # Botón de Descarga
                    st.download_button(
                        label="📥 Descargar Informe en Word",
                        data=crear_word_profesional(informe_final),
                        file_name=f"Informe_{archivo_pdf.name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    st.error(f"Error en el proceso: {e}")
