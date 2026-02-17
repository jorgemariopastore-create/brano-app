
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
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Soporte SonoScape E3")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def crear_word(texto_final, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    for linea in texto_final.split('\n'):
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
        try: doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run("ANEXO DE IMÁGENES").bold = True
        for img in imagenes[:2]: # Máximo 2 imágenes para evitar el botón rojo
            try:
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.add_run().add_picture(io.BytesIO(img), width=Inches(4.5))
            except: continue
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    if "raw_text" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        with st.spinner("Mapeando datos del ecógrafo..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Extraemos texto preservando los espacios en blanco (Layout)
            # Esto ayuda a que los números se queden cerca de sus etiquetas
            texto_layout = ""
            for pagina in pdf:
                texto_layout += pagina.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) + "\n"
            
            st.session_state.raw_text = texto_layout
            st.session_state.last_file = archivo.name
            
            # Guardamos imágenes en baja resolución para no saturar memoria (Adiós botón rojo)
            imgs = []
            for p in pdf:
                for img_info in p.get_images():
                    if len(imgs) < 2:
                        pix = fitz.Pixmap(pdf, img_info[0])
                        imgs.append(pix.tobytes("jpg"))
            st.session_state.raw_imgs = imgs
            pdf.close()

    if st.button("🚀 GENERAR INFORME"):
        try:
            client = Groq(api_key=api_key)
            # Prompt de "Búsqueda Visual"
            prompt = f"""
            ERES EL DR. PASTORE. USA EL TEXTO PARA COMPLETAR EL INFORME.
            BUSCA VALORES NUMÉRICOS CERCA DE: DDVI, DSVI, DDSIV, DDPP, DDAI, FEy, Vena Cava.
            SI DICE 'DDVI 61', el valor es 61.

            ESTRUCTURA:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Valores encontrados en mm)
            II. FUNCIÓN VENTRICULAR: (FEy %, FA %, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (E/A, E/e', Vena Cava)
            IV. CONCLUSIÓN: (Resumen médico)

            FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL PDF:
            {st.session_state.raw_text}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            informe_texto = resp.choices[0].message.content
            st.session_state.informe_ok = informe_texto
            st.markdown(f'<div class="report-container">{informe_texto}</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {e}")

    if "informe_ok" in st.session_state:
        st.download_button(
            label="📥 Descargar Word",
            data=crear_word(st.session_state.informe_ok, st.session_state.raw_imgs),
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
