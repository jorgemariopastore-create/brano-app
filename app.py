
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN VISUAL
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Soporte SonoScape E3")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

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
        try:
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run("ANEXO DE IMÁGENES").bold = True
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            try:
                paragraph = tabla.cell(row, col).paragraphs[0]
                run_img = paragraph.add_run()
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.8))
            except: continue
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    if "texto_eco" not in st.session_state or st.session_state.get("nombre_doc") != archivo.name:
        with st.spinner("Leyendo datos del SonoScape E3..."):
            doc_pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            texto_acumulado = []
            for pagina in doc_pdf:
                # CORRECCIÓN AQUÍ: Iteramos sobre los bloques y extraemos el texto (índice 4)
                bloques = pagina.get_text("blocks")
                for b in bloques:
                    texto_acumulado.append(b[4]) 
            
            st.session_state.imgs_eco = [doc_pdf.extract_image(img[0])["image"] for p in doc_pdf for img in p.get_images()]
            st.session_state.texto_eco = "\n".join(texto_acumulado)
            st.session_state.nombre_doc = archivo.name
            doc_pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. ANALIZA EL TEXTO DEL ECOGRAFO SONOSCAPE E3.
            
            DATOS A IDENTIFICAR (BUSCA VALORES NUMÉRICOS CERCA DE ESTAS ETIQUETAS):
            - DDVI (ej: 61), DSVI (ej: 46), DDSIV (ej: 10), DDPP (ej: 11), DDAI (ej: 42).
            - FEy (ej: 31%), Vena Cava (ej: 15mm).
            - Relación E/A, Relación E/e' (ej: 5.9).

            ESTRUCTURA DEL INFORME:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Detalla DDVI, DSVI, Septum, Pared, Aurícula e incluye la Vena Cava aquí).
            II. FUNCIÓN VENTRICULAR: (Detalla FEy y describe la Motilidad/Hipertrofia).
            III. EVALUACIÓN HEMODINÁMICA: (Relación E/A, E/e' y Valvulopatías).
            IV. CONCLUSIÓN: (Diagnóstico médico final coherente).

            REGLA: NO agregues recomendaciones. Termina en: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO EXTRAÍDO:
            {st.session_state.texto_eco}
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
                data=generar_word(resultado, st.session_state.imgs_eco),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error en la IA: {e}")
