
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Final", layout="wide")
st.title("❤️ CardioReport AI - Formato Único Dr. Pastore")

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key:", type="password")

def crear_word_profesional(texto):
    doc = Document()
    # Encabezado Único
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run.bold = True
    run.font.size = Pt(14)
    
    for linea in texto.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        parrafo = doc.add_paragraph()
        if any(linea.startswith(x) for x in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            parrafo.add_run(linea).bold = True
        else:
            parrafo.add_run(linea)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir Reporte del Ecógrafo (PDF/JPG)", accept_multiple_files=True)

    if archivos and st.button("GENERAR INFORME FINAL"):
        with st.spinner("Analizando según patrón de 10 casos registrados..."):
            texto_crudo = ""
            for a in archivos:
                if a.type == "application/pdf":
                    with fitz.open(stream=a.read(), filetype="pdf") as d:
                        for pag in d: texto_crudo += pag.get_text()
                else: texto_crudo += " [Imagen detectada] "

            prompt = f"""
            Actúa como el Dr. Francisco Alberto Pastore. Analiza: {texto_crudo[:7000]}
            
            REGLAS DE ORO BASADAS EN 10 CASOS REALES:
            1. CONVERSIÓN: Si el ecógrafo da cm (ej: 4.5cm), escribe mm (45mm).
            2. PRIORIDAD FEy: Busca 'EF (Simpson)'. Si no está, usa 'EF (Teich)'.
            3. ANATOMÍA: Reporta DDVI, DSVI, AI, Septum y Pared Posterior.
            4. ESTILO: Redacción médica sobria. No inventes párrafos largos si el estudio es normal.
            
            ESTRUCTURA OBLIGATORIA:
            DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
            I. EVALUACIÓN ANATÓMICA: (Diámetros en mm y descripción de cavidades).
            II. FUNCIÓN VENTRICULAR: (Mencionar FEy % y motilidad).
            III. EVALUACIÓN HEMODINÁMICA: (Hallazgos Doppler relevantes).
            IV. CONCLUSIÓN: (Diagnóstico principal en negrita).
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
            """
            
            try:
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                res = chat.choices[0].message.content
                st.markdown(res)
                st.download_button("📥 Descargar Word", crear_word_profesional(res), "Informe_Cardio.docx")
            except Exception as e:
                st.error(f"Error: {e}")
