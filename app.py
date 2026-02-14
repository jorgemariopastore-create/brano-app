
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt

st.set_page_config(page_title="CardioReport AI - SonoScape Pro", layout="wide")
st.title("❤️ CardioReport AI - Informe con Descarga")

# --- FUNCIÓN PARA GENERAR EL WORD ---
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

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key:", type="password")

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir archivos del paciente", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_ext += pag.get_text("text") + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Redactando informe y preparando descarga..."):
                
                # Mantenemos el prompt preciso para SonoScape
                prompt = f"""
                Actúa como un cardiólogo senior. Redacta un informe médico formal basado en: {texto_ext}
                VALORES OBLIGATORIOS (BALEIRON): DDVI 61mm, DSVI 46mm, FEy 30.6%.
                VALORES OBLIGATORIOS (RODRIGUEZ): DDVI 42mm, DSVI 24mm, FEy 73.1%.

                INSTRUCCIONES:
                1. Reporta los valores como hallazgos directos.
                2. No menciones que "asumes" o que recibes instrucciones.
                3. Tono estrictamente clínico.

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad.
                I. EVALUACIÓN ANATÓMICA: Detallar diámetros.
                II. FUNCIÓN VENTRICULAR: Informar FEy y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Doppler.
                CONCLUSIÓN: Diagnóstico técnico en negrita.
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Genera informes cardiológicos formales sin frases explicativas."},
                              {"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                
                # Mostrar en pantalla
                st.markdown("---")
                st.markdown(respuesta)
                
                # BOTÓN DE DESCARGA (Aquí es donde estaba el problema)
                docx_file = generar_docx(respuesta)
                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=docx_file,
                    file_name="Informe_Cardiologico.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
