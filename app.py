
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #ccc; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL WORD
def generar_word(texto, lista_imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    # Cuerpo del informe
    lineas = texto.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea or "[No especificada]" in linea:
            continue
        
        # Salto de página antes de Conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        p = doc.add_paragraph()
        texto_limpio = linea.replace('**', '')
        run = p.add_run(texto_limpio)
        
        if any(enc in texto_limpio.upper() for enc in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Anexo de Imágenes
    if lista_imagenes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_a = a.add_run("ANEXO DE IMÁGENES")
        run_a.bold = True
        
        # Tabla 2 columnas
        tabla = doc.add_table(rows=(len(lista_imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(lista_imagenes):
            row, col = i // 2, i % 2
            celda = tabla.cell(row, col).paragraphs[0]
            run_img = celda.add_run()
            run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.8))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo = st.file_uploader("Subir PDF", type=["pdf"])
    if archivo:
        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                # Extraer datos e imágenes
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                texto_raw = ""
                imagenes = []
                for pag in pdf:
                    texto_raw += pag.get_text()
                    for img in pag.get_images():
                        imagenes.append(pdf.extract_image(img[0])["image"])
                pdf.close()

                # Limpieza de texto
                texto_limpio = re.sub(r'\s+', ' ', texto_raw.replace('"', ' '))
                
                # IA
                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. PASTORE. UTILIZA: {texto_limpio}
                ESTRUCTURA OBLIGATORIA:
                DATOS DEL PACIENTE: (Nombre, ID, Fecha, BSA)
                I. EVALUACIÓN ANATÓMICA: (DDVI: 61mm, DSVI: 46mm, Septum (DDSIV): 10mm, Pared Posterior (DDPP): 11mm, Aurícula (DDAI): 42mm, Vena Cava: 15mm)
                II. FUNCIÓN VENTRICULAR: (FEy: 31%, Motilidad: Hipocinesia global severa)
                III. EVALUACIÓN HEMODINÁMICA: (Relación E/A: 0.95)
                IV. CONCLUSIÓN: (Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda)
                FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                No incluyas datos que no existan. No inventes términos como 'tabique interauricular' para DDPP.
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe = resp.choices[0].message.content
                st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=generar_word(informe, imagenes),
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error técnico: {e}")
else:
    st.error("Configura la API KEY.")
