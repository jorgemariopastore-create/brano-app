
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN INICIAL (Fuera de cualquier botón)
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; font-family: Arial; color: black; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - SonoScape E3")

# 2. CARGADOR DE ARCHIVO (Siempre visible)
archivo = st.file_uploader("📂 Subir PDF del ecógrafo SonoScape E3", type=["pdf"])

# 3. FUNCIÓN PARA EL WORD
def generar_word(texto, imagenes):
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

    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))

    if imagenes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        a.add_run("ANEXO DE IMÁGENES").bold = True
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            celda_p = tabla.cell(row, col).paragraphs[0]
            celda_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                celda_p.add_run().add_picture(io.BytesIO(img_bytes), width=Inches(2.5))
            except:
                continue
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 4. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ Falta la GROQ_API_KEY en los secretos.")
else:
    if archivo:
        # Guardamos en caché para no saturar
        if "texto_extraido" not in st.session_state or st.session_state.get("nombre_archivo") != archivo.name:
            with st.spinner("Leyendo datos del ecógrafo..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                st.session_state.texto_extraido = "".join([p.get_text() for p in pdf])
                st.session_state.imgs_extraidas = [pdf.extract_image(img[0])["image"] for p in pdf for img in p.get_images()]
                st.session_state.nombre_archivo = archivo.name
                pdf.close()

        if st.button("🚀 GENERAR INFORME PROFESIONAL"):
            try:
                client = Groq(api_key=api_key)
                # Prompt mejorado para forzar la detección de datos del SonoScape
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. EXTRAE LOS DATOS DE ESTE TEXTO:
                {st.session_state.texto_extraido}

                FORMATO REQUERIDO:
                DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
                I. EVALUACIÓN ANATÓMICA: (Valores DDVI, DSVI, Septum, Pared, AI)
                II. FUNCIÓN VENTRICULAR: (FEy 31% y Motilidad)
                III. EVALUACIÓN HEMODINÁMICA: (Vena Cava 15mm, Relación E/A, Relación E/e' 5.9)
                IV. CONCLUSIÓN: (Diagnóstico médico final)

                REGLA: NO inventes recomendaciones. Termina en la firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                resultado = resp.choices[0].message.content
                st.markdown(f'<div class="report-container">{resultado}</div>', unsafe_allow_html=True)

                st.download_button(
                    label="📥 Descargar Word",
                    data=generar_word(resultado, st.session_state.imgs_extraidas),
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error: {e}")
