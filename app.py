
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 25px; border-radius: 10px; border: 1px solid #ddd; }
    .stButton>button { background-color: #c62828; color: white; width: 100%; height: 3em; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL WORD
def crear_word_final(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    # Procesar líneas y aplicar lógica de salto de página
    secciones = texto.split('\n')
    for linea in secciones:
        linea = linea.strip()
        if not linea or "[No especificada]" in linea: # Omitir datos vacíos
            continue
        
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        
        if any(tag in linea.upper() for tag in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Anexo de Imágenes
    if imagenes:
        doc.add_page_break()
        p_anexo = doc.add_paragraph()
        p_anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_an = p_anexo.add_run("ANEXO DE IMÁGENES")
        run_an.bold = True
        
        table = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_data in enumerate(imagenes):
            row, col = i // 2, i % 2
            paragraph = table.cell(row, col).paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(3.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. LÓGICA PRINCIPAL
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                # Extraer datos e imágenes una sola vez
                doc_pdf = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
                texto_raw = ""
                imgs = []
                for pagina in doc_pdf:
                    texto_raw += pagina.get_text()
                    for img in pagina.get_images():
                        imgs.append(doc_pdf.extract_image(img[0])["image"])
                doc_pdf.close()

                # Prompt mejorado para omitir lo que no existe
                texto_limpio = re.sub(r'\s+', ' ', texto_raw.replace('"', ' '))
                client = Groq(api_key=api_key)
                
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. UTILIZA ESTO: {texto_limpio}
                
                INSTRUCCIONES:
                1. Extrae DDVI (61), DSVI (46), DDSIV (10), DDPP (11), DDAI (42), FEy (31%), Motilidad (Hipocinesia global severa) y Vena Cava (15).
                2. SI UN DATO NO ESTÁ (como FC o Presión), NO LO INCLUYAS, no pongas 'No especificada'.
                3. CONCLUSIÓN: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".
                
                FORMATO: DATOS DEL PACIENTE, I. EVALUACIÓN ANATÓMICA, II. FUNCIÓN VENTRICULAR, III. EVALUACIÓN HEMODINÁMICA, IV. CONCLUSIÓN, FIRMA.
                """

                chat_completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                resultado = chat_completion.choices[0].message.content
                st.markdown(f'<div class="report-container">{resultado}</div>', unsafe_allow_html=True)

                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=crear_word_final(resultado, imgs),
                    file_name=f"Informe_{archivo_pdf.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.error("Falta API KEY.")
