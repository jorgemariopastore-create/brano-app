
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

# Estilo para evitar el "Botón Rojo"
st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 25px; border-radius: 10px; border: 1px solid #ddd; }
    .stButton>button { background-color: #c62828; color: white; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA CREAR EL WORD CON ANEXO DE IMÁGENES
def crear_word_con_imagenes(texto, imagenes_bytes):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    # Cuerpo del Informe
    for linea in texto.split('\n'):
        linea_limpia = linea.replace('**', '').strip()
        if linea_limpia:
            p = doc.add_paragraph()
            run = p.add_run(linea_limpia)
            if any(tag in linea_limpia.upper() for tag in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
                run.bold = True

    # ANEXO DE IMÁGENES (4 líneas de a dos)
    if imagenes_bytes:
        doc.add_page_break()
        doc.add_heading('ANEXO DE IMÁGENES', level=1)
        
        # Crear tabla de 2 columnas
        num_imgs = len(imagenes_bytes)
        rows = (num_imgs + 1) // 2
        table = doc.add_table(rows=rows, cols=2)
        
        for i, img_data in enumerate(imagenes_bytes):
            row = i // 2
            col = i % 2
            paragraph = table.cell(row, col).paragraphs[0]
            run = paragraph.add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(3.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                # Extraer Texto e Imágenes
                texto_raw = ""
                imagenes_bytes = []
                
                with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc_pdf:
                    for pagina in doc_pdf:
                        texto_raw += pagina.get_text()
                        # Extraer imágenes
                        for img in pagina.get_images(full=True):
                            xref = img[0]
                            base_image = doc_pdf.extract_image(xref)
                            imagenes_bytes.append(base_image["image"])

                # Limpieza de texto
                texto_limpio = re.sub(r'\s+', ' ', texto_raw.replace('"', ' ').replace("'", " "))

                client = Groq(api_key=api_key)
                
                # PROMPT PARA CORREGIR NOMBRES TÉCNICOS
                prompt = f"""
                ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE.
                TEXTO: {texto_limpio}
                
                REGLAS DE NOMENCLATURA:
                - DDSIV es 'Septum Interventricular'.
                - DDPP es 'Pared Posterior'.
                - DDAI es 'Aurícula Izquierda'.
                - FEy es 'Fracción de Eyección'.
                - BUSCA: Hipocinesia global severa.

                FORMATO:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, Septum, Pared, AI)
                II. FUNCIÓN VENTRICULAR: (FEy y Motilidad)
                III. EVALUACIÓN HEMODINÁMICA: (Vena Cava y Doppler)
                IV. CONCLUSIÓN: (En negrita)
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe_final = response.choices[0].message.content
                st.markdown(f'<div class="report-container">{informe_final}</div>', unsafe_allow_html=True)

                st.download_button(
                    label="📥 Descargar Word con Imágenes",
                    data=crear_word_con_imagenes(informe_final, imagenes_bytes),
                    file_name="Informe_Final.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.error("Falta API KEY.")
