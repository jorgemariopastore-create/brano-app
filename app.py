
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIONES DE APOYO (Word y Limpieza)
def crear_word_profesional(texto):
    doc = Document()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)
    
    for linea in texto.split('\n'):
        linea_limpia = linea.replace('**', '').strip()
        if linea_limpia:
            p = doc.add_paragraph()
            run = p.add_run(linea_limpia)
            if any(linea_limpia.startswith(tag) for tag in ["DATOS", "I.", "II.", "III.", "IV.", "Firma:"]):
                run.bold = True
    
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. INTERFAZ DE CARGA (Esto debe aparecer siempre)
api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ Error: No se encontró la GROQ_API_KEY en los Secrets de Streamlit.")
else:
    # EL BOTÓN DE CARGA DEBE ESTAR AQUÍ, SIN ESPACIOS DE MÁS
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        st.success(f"Archivo cargado: {archivo_pdf.name}")
        
        if st.button("GENERAR INFORME DEL PACIENTE"):
            with st.spinner("Procesando datos..."):
                try:
                    # Lectura
                    texto_completo = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_completo += pagina.get_text()
                    
                    # Limpieza básica
                    texto_limpio = texto_completo.replace('"', '').replace("'", "")
                    texto_limpio = re.sub(r'\n+', ' ', texto_limpio)

                    client = Groq(api_key=api_key)
                    
                    prompt = f"""
                    ERES UN TRANSCRIPTOR MÉDICO. EXTRAE LOS SIGUIENTES DATOS DEL TEXTO: {texto_limpio}
                    DATOS: DDVI (61), DSVI (46), AI (42), Septum (10), Pared (11), FEy (31%), Vena Cava (15), Doppler (E/A 0.95).
                    REGLA: FEy < 35% y DDVI > 57mm -> Miocardiopatía Dilatada Deterioro SEVERO.
                    FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )

                    informe_texto = response.choices[0].message.content
                    st.markdown("---")
                    st.write(informe_texto)
                    
                    # Botón de Word
                    st.download_button(
                        label="📥 Descargar Informe en Word",
                        data=crear_word_profesional(informe_texto),
                        file_name=f"Informe_{archivo_pdf.name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    st.error(f"Error al procesar: {e}")
