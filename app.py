
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #ccc; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL WORD (ESTRUCTURA MÉDICA)
def generar_word_estable(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título Principal
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    lineas = texto.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        
        # Salto de página antes de Conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        # Espacio para firma (si existe firma.jpg la pone arriba del nombre)
        if "DR. FRANCISCO" in linea.upper() and os.path.exists("firma.jpg"):
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
            
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        
        # Negritas en encabezados
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "PACIENTE", "FIRMA"]):
            run.bold = True

    # Anexo de Imágenes
    if imagenes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_a = a.add_run("ANEXO DE IMÁGENES")
        run_a.bold = True
        
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            run_img = tabla.cell(row, col).paragraphs[0].add_run()
            try:
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.8))
            except:
                continue

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo = st.file_uploader("Subir PDF", type=["pdf"])
    
    if archivo:
        # Extraer solo una vez para evitar que el botón se ponga rojo
        if "pdf_data" not in st.session_state or st.session_state.get("pdf_name") != archivo.name:
            with st.spinner("Leyendo PDF..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                st.session_state.texto_raw = "".join([p.get_text() for p in pdf])
                st.session_state.imgs = [pdf.extract_image(img[0])["image"] for p in pdf for img in p.get_images()]
                st.session_state.pdf_name = archivo.name
                pdf.close()

        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                client = Groq(api_key=api_key)
                
                # Prompt con datos exactos del paciente MANUEL BALEIRON
                prompt = f"""
                ACTÚA COMO EL DR. PASTORE. USA ESTOS DATOS: {st.session_state.texto_raw}
                
                REGLAS:
                - DATOS: Nombre: MANUEL BALEIRON. Peso: 80 kg. Altura: 169 cm. BSA: 1.91 m2. Fecha: 27/01/2026.
                - I. ANATOMÍA: DDVI 61mm, DSVI 46mm, Septum 10mm, Pared 11mm, AI 42mm, Vena Cava 15mm.
                - II. FUNCIÓN: FEy 31%. Hipocinesia global severa. Hipertrofia excéntrica.
                - III. HEMODINAMIA: Relación E/A 0.95. Relación E/e' 5.9 (Presión de llenado normal). Insuficiencia Mitral leve.
                - IV. CONCLUSIÓN: Miocardiopatía dilatada con deterioro severo de fracción de eyección del VI.
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
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
                    data=generar_word_estable(informe, st.session_state.imgs),
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.error("Configura la API KEY.")
