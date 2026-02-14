
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI - SonoScape E3 Pro", layout="wide")
st.title("❤️ CardioReport AI - Extractor SonoScape E3")

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx(texto_ia):
    doc = Document()
    for linea in texto_ia.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        p = doc.add_paragraph()
        if any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run = p.add_run(linea.upper())
            run.bold = True
        else:
            p.add_run(linea)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir reportes del SonoScape E3", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        # CORRECCIÓN DEL ERROR: Extraemos palabras y las unimos en un string
                        palabras = pag.get_text("words")
                        # Cada 'p' es una tupla, el texto está en p[4]
                        texto_pag = " ".join([p[4] for p in palabras])
                        texto_ext += texto_pag + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Analizando datos del SonoScape E3..."):
                
                prompt = f"""
                Actúa como un cardiólogo experto. Analiza este texto extraído de un ecógrafo SonoScape E3:
                ---
                {texto_ext}
                ---

                MISION DE EXTRACCION (Busca estos términos del SonoScape):
                - 'EF(Teich)' o 'EF' -> Fracción de Eyección (Ej: 73.14%).
                - 'LVIDd' -> Diámetro Diastólico (Ej: 4.20 cm).
                - 'LVIDs' -> Diámetro Sistólico (Ej: 2.42 cm).
                - 'LA Diam' o 'LA' -> Aurícula Izquierda (Ej: 4.24 cm).

                REGLAS DE NEGOCIO:
                1. Si la FEy/EF es > 55%: Conclusión = "Función sistólica conservada".
                2. Si la FEy/EF es < 45%: Conclusión = "Deterioro de la función sistólica".
                3. No inventes datos. Si no encuentras el valor, busca el número más cercano a las etiquetas mencionadas.

                ESTRUCTURA DEL INFORME:
                DATOS DEL PACIENTE: Nombre, Edad, ID.
                I. EVALUACIÓN ANATÓMICA: Reportar DDVI (LVIDd), DSVI (LVIDs) y Aurícula Izquierda (LA).
                II. FUNCIÓN VENTRICULAR: Mencionar FEy (EF) y técnica utilizada (Teichholz).
                III. EVALUACIÓN HEMODINÁMICA: Hallazgos del Doppler.
                CONCLUSIÓN: Diagnóstico final técnico en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un cardiólogo que extrae medidas precisas de tablas técnicas."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("📥 Descargar Word", generar_docx(respuesta), "Informe_Cardio.docx")
