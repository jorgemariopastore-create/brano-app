
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de página
st.set_page_config(page_title="CardioReport AI Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #d32f2f; color: white; font-weight: bold; border-radius: 8px; }
    .report-text { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ CardioReport AI - Formato Dr. Pastore")
st.info("Esta versión incluye lógica de extracción profunda para casos complejos como Baleiron.")

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key:", type="password")

def crear_word_profesional(texto):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run.bold = True
    run.font.size = Pt(14)
    
    for linea in texto.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        parrafo = doc.add_paragraph()
        run_l = parrafo.add_run(linea)
        if any(linea.startswith(x) for x in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run_l.bold = True
    
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir PDF del Ecógrafo", accept_multiple_files=True)

    if archivos and st.button("GENERAR INFORME MÉDICO"):
        with st.spinner("Analizando coordenadas y valores..."):
            texto_crudo = ""
            for a in archivos:
                if a.type == "application/pdf":
                    with fitz.open(stream=a.read(), filetype="pdf") as d:
                        for pag in d: texto_crudo += pag.get_text()

            # PROMPT DE EXTRACCIÓN FORZADA
            prompt = f"""
            Eres el Dr. Francisco Alberto Pastore. Debes generar un informe médico BASADO EXCLUSIVAMENTE en estos datos crudos: 
            ---
            {texto_crudo}
            ---

            INSTRUCCIONES CRÍTICAS:
            1. No digas "No disponible". Los datos están en el texto, búscalos por sus siglas en inglés o español:
               - DDVI es LVIDd o Diastolic.
               - DSVI es LVIDs o Systolic.
               - FEy es EF, Simpson o Teich.
               - AI es LA, Left Atrium o Aurícula Izq.
            2. Si la FEy es < 35% (como el 31% de Baleiron), la conclusión DEBE ser: "Deterioro SEVERO de la función sistólica".
            3. Si el DDVI es > 57mm (como el 61mm de Baleiron), debe decir "Dilatación del ventrículo izquierdo".
            4. Menciona siempre la Motilidad (ej: "Hipocinesia global" si aparece en el texto).
            5. Convierte CM a MM (6.1 cm -> 61 mm).

            FORMATO REQUERIDO:
            DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, AI, Septum, Pared en mm).
            II. FUNCIÓN VENTRICULAR: (FEy % y descripción de motilidad).
            III. EVALUACIÓN HEMODINÁMICA: (Doppler y Vena Cava).
            IV. CONCLUSIÓN: (Diagnóstico en negrita y contundente).
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            """

            try:
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un cardiólogo experto que nunca omite datos."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                res = chat.choices[0].message.content
                st.subheader("Informe Generado:")
                st.markdown(f'<div class="report-text">{res}</div>', unsafe_allow_html=True)
                st.download_button("📥 Descargar Word", crear_word_profesional(res), "Informe_Final.docx")
            except Exception as e:
                st.error(f"Error: {e}")
