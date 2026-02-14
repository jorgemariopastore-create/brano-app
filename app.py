
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de página
st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Sistema Flexible")

# --- MANEJO DE CLAVE ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key:", type="password")

def limpiar_texto(t):
    return t.encode("ascii", "ignore").decode("ascii")

def generar_docx(texto_ia, imagenes):
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
    
    if imagenes:
        doc.add_page_break()
        for img in imagenes:
            doc.add_picture(io.BytesIO(img), width=Inches(3))
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir PDF", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext, fotos = "", []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_ext += pag.get_text() + "\n"
                        for img in pag.get_images(full=True):
                            fotos.append(d.extract_image(img[0])["image"])
            else:
                fotos.append(a.read())

        if st.button("Generar Informe"):
            with st.spinner("Analizando datos..."):
                texto_limpio = limpiar_texto(texto_ext)
                
                # INSTRUCCIONES CORREGIDAS (SIN NÚMEROS FIJOS)
                prompt = f"""
                Actúa como un cardiólogo. Analiza estos datos: {texto_limpio}

                REGLAS:
                1. Extrae los valores REALES de este texto (DDVI, FEy, etc.).
                2. Si la FEy es > 55%, la función es normal.
                3. Si la FEy es < 40%, reporta deterioro severo.
                4. NO uses datos de pacientes anteriores. Cíñete a este texto.

                ESTRUCTURA:
                DATOS DEL PACIENTE: Nombre, Edad, Fecha.
                I. EVALUACIÓN ANATÓMICA: Diámetros reales.
                II. FUNCIÓN VENTRICULAR: FEy real y motilidad.
                III. EVALUACIÓN HEMODINÁMICA: Doppler (E/A).
                CONCLUSIÓN: Diagnóstico técnico basado en los números.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
                st.download_button("Descargar Word", generar_docx(respuesta, fotos), "Informe.docx")
