
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Extractor de Alta Precisión")

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
                        # Extraemos texto bloque por bloque para no perder datos de tablas
                        texto_ext += pag.get_text("blocks")
                        texto_ext = str(texto_ext) + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Analizando tablas y valores técnicos..."):
                
                # EL PROMPT "CAZADOR" DE DATOS
                prompt = f"""
                Eres un cardiólogo experto. Tu ÚNICA MISIÓN es rescatar los números de este texto:
                ---
                {texto_ext}
                ---

                GUÍA DE BÚSQUEDA (Los datos están ahí, no te rindas):
                1. FRACCIÓN DE EYECCIÓN (FEy): Busca el número junto a 'EF', 'EF(Teich)', 'EF(S)', 'FE' o '%'. (Ejemplo: 73.14% o 30.6%).
                2. DIÁMETROS: Busca 'LVIDd' o 'DDVI' (suele ser 4.20cm o 6.1cm). Busca 'LVIDs' o 'DSVI'.
                3. AURÍCULA: Busca 'LA' o 'AI' (suele ser 4.24cm).

                REGLAS DE ORO:
                - SIEMPRE informa un valor numérico si lo encuentras.
                - Si FEy > 55%: Conclusión = "Función sistólica conservada".
                - Si FEy < 45%: Conclusión = "Deterioro de la función sistólica".
                - Prohibido decir "No hay datos". Si no encuentras el nombre, busca el número que parezca una medida cardíaca.

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad.
                I. EVALUACIÓN ANATÓMICA: Diámetros y Aurícula.
                II. FUNCIÓN VENTRICULAR: FEy y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Doppler y flujos.
                CONCLUSIÓN: Diagnóstico técnico en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres un asistente médico que extrae datos numéricos con precisión 100%."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("📥 Descargar Informe en Word", generar_docx(respuesta), "Informe_Final.docx")
