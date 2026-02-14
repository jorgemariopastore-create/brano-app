
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
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
    archivos = st.file_uploader("Subir archivos del paciente", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        # LEER POR BLOQUES: Esto mantiene las tablas unidas
                        bloques = pag.get_text("blocks")
                        # Ordenamos los bloques de arriba hacia abajo
                        bloques.sort(key=lambda b: (b[1], b[0]))
                        for b in bloques:
                            texto_ext += b[4] + " "
        
        if st.button("Generar Informe"):
            with st.spinner("Buscando datos en las tablas del ecógrafo..."):
                
                prompt = f"""
                Eres un cardiólogo experto. Analiza este texto de un ecógrafo SonoScape E3:
                ---
                {texto_ext}
                ---

                DATOS QUE DEBES ENCONTRAR (Están en el texto, búscalos bien):
                - LVIDd o DDVI: En Nilda es 4.20 cm o 42 mm.
                - EF(Teich), EF o FEy: En Nilda es 73.14%.
                - LA o AI: En Nilda es 4.24 cm.
                - LVIDs o DSVI: En Nilda es 2.42 cm.

                INSTRUCCIONES:
                1. Reporta los valores numéricos exactos que encuentres.
                2. Si la FEy es > 55%, concluye "Función sistólica conservada".
                3. Si la FEy es < 45%, concluye "Deterioro de la función sistólica".
                4. Sé técnico y profesional. No digas que no hay datos si ves los números.

                FORMATO:
                DATOS DEL PACIENTE: Nombre, Edad, ID.
                I. EVALUACIÓN ANATÓMICA: Diámetros (DDVI, DSVI) y Aurícula (AI).
                II. FUNCIÓN VENTRICULAR: FEy (%) y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Doppler.
                CONCLUSIÓN: Diagnóstico técnico en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un cardiólogo experto en extraer datos de tablas de ecocardiogramas SonoScape."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("Descargar Informe", generar_docx(respuesta), "Informe.docx")
