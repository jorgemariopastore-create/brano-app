
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - SonoScape E3")

archivo = st.file_uploader("📂 Subir PDF", type=["pdf"])

def crear_docx(texto, lista_imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea: continue
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Firma JPG
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        try:
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    # Anexo (Máximo 4 imágenes para evitar error)
    if lista_imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run("ANEXO DE IMÁGENES").bold = True
        tabla = doc.add_table(rows=(len(lista_imagenes) + 1) // 2, cols=2)
        for i, img_data in enumerate(lista_imagenes[:4]):
            row, col = i // 2, i % 2
            try:
                run_img = tabla.cell(row, col).paragraphs[0].add_run()
                run_img.add_picture(io.BytesIO(img_data), width=Inches(2.5))
            except: continue
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    if "cache_texto" not in st.session_state or st.session_state.get("file_id") != archivo.name:
        with st.spinner("Procesando PDF..."):
            doc_pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            st.session_state.cache_texto = "\n".join([p.get_text() for p in doc_pdf])
            # Solo guardamos los bytes de las imágenes para ahorrar memoria
            st.session_state.cache_imgs = [doc_pdf.extract_image(img[0])["image"] for p in doc_pdf for img in p.get_images()]
            st.session_state.file_id = archivo.name
            doc_pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. EXTRAE LOS DATOS DEL TEXTO DEL SONOSCAPE E3.
            
            DATOS OBLIGATORIOS (BÚSCALOS EN EL TEXTO):
            - Cavidades: DDVI, DSVI, DDSIV, DDPP, DDAI.
            - Función: FEy (ej. 31%), Motilidad (ej. Hipocinesia global severa), Hipertrofia (ej. excéntrica).
            - Doppler: Vena Cava (ej. 15mm), Relación E/A, Relación E/e'.
            - Conclusión: Copia los puntos 1 y 2 de la sección ECOCARDIOGRAMA 2D.

            FORMATO:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, DDSIV, DDPP, DDAI, Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (Relación E/A, Relación E/e', Doppler valvular)
            IV. CONCLUSIÓN: (Diagnóstico final)

            REGLA: NO INVENTES RECOMENDACIONES. TERMINA EN LA FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO: {st.session_state.cache_texto}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            informe_final = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{informe_final}</div>', unsafe_allow_html=True)

            st.download_button(
                label="📥 Descargar Word",
                data=crear_docx(informe_final, st.session_state.cache_imgs),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error: {e}")
