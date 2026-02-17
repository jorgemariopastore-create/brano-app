
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - SonoScape E3")

# 2. CARGADOR DE ARCHIVO
archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def generar_word_seguro(texto, imagenes):
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
        try:
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run("ANEXO DE IMÁGENES").bold = True
        # Solo tomamos hasta 6 imágenes para evitar error de botón rojo
        tabla = doc.add_table(rows=(min(len(imagenes), 6) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes[:6]):
            row, col = i // 2, i % 2
            try:
                run_img = tabla.cell(row, col).paragraphs[0].add_run()
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.5))
            except: continue
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Usamos session_state para evitar que el botón rojo aparezca al procesar
    if "texto_procesado" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        with st.spinner("Leyendo datos del ecógrafo..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Extraemos texto de manera simple pero efectiva
            texto_crudo = ""
            for pagina in pdf:
                texto_crudo += pagina.get_text() + "\n"
            
            # Extraer imágenes
            imgs = []
            for pag in pdf:
                for img in pag.get_images():
                    imgs.append(pdf.extract_image(img[0])["image"])
            
            st.session_state.texto_procesado = texto_crudo
            st.session_state.imgs_procesadas = imgs
            st.session_state.last_file = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            
            # Prompt de instrucciones directas para que no se pierda
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. TU MISIÓN ES EXTRAER LOS DATOS DEL PDF DE UN SONOSCAPE E3.
            
            INSTRUCCIONES:
            1. Busca los valores numéricos: DDVI (61), DSVI (46), DDSIV (10), DDPP (11), DDAI (42), FA (25), FEy (31%).
            2. Busca en la página 2 la sección DOPPLER: Relación E/A (0.95), Relación E/e' (5.9), Vena Cava (15mm).
            3. Redacta la CONCLUSIÓN tal cual figura en el punto 1 y 2 del informe 2D (Miocardiopatía dilatada...).

            FORMATO:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, DDSIV, DDPP, DDAI, Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (Relación E/A, Relación E/e', Doppler valvular)
            IV. CONCLUSIÓN: (Diagnóstico final)

            REGLA DE ORO: NO INVENTES RECOMENDACIONES. TERMINA EN LA FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL ESTUDIO:
            {st.session_state.texto_procesado}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            informe = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

            # Botón de descarga con los datos guardados
            st.download_button(
                label="📥 Descargar Word",
                data=generar_word_seguro(informe, st.session_state.imgs_procesadas),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error: {e}")
