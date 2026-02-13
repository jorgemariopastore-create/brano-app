
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de página
st.set_page_config(page_title="CardioReport AI", layout="wide")
st.title("❤️ CardioReport AI - Sistema Automático")

# --- MANEJO AUTOMÁTICO DE CLAVE (LOS "MISTERIOS") ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key (Manual):", type="password")

def limpiar_texto(t):
    return t.encode("ascii", "ignore").decode("ascii")

def generar_docx_profesional(texto_ia, imagenes):
    doc = Document()
    section = doc.sections[0]
    section.left_margin, section.right_margin = Inches(0.7), Inches(0.7)
    section.top_margin, section.bottom_margin = Inches(0.6), Inches(0.6)

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)

    lineas = texto_ia.split('\n')
    for i, linea in enumerate(lineas):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold, run.underline = True, True
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.keep_with_next = True 
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # Bloque de seguridad para que la firma no quede sola
            if i > len(lineas) - 8:
                p.paragraph_format.keep_with_next = True

    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run('ANEXO: IMÁGENES DEL ESTUDIO').bold = True
        table = doc.add_table(rows=0, cols=2)
        for idx in range(0, len(imagenes), 2):
            row = table.add_row().cells
            for j in range(2):
                if idx + j < len(imagenes):
                    cp = row[j].paragraphs[0]
                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cp.add_run().add_picture(io.BytesIO(imagenes[idx+j]), width=Inches(2.45))
                    cp.add_run(f"\nFig. {idx + j + 1}")
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf", "jpg", "png"], accept_multiple_files=True)

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

        if st.button("Generar Informe Médico"):
            with st.spinner("La IA está redactando el informe profesional..."):
                texto_limpio = limpiar_texto(texto_ext)
                prompt = f"Eres cardiólogo. Redacta un informe médico profesional basado en: {texto_limpio}. Esquema: DATOS DEL PACIENTE, I. EVALUACIÓN ANATÓMICA, II. FUNCIÓN VENTRICULAR, III. EVALUACIÓN HEMODINÁMICA, IV. HALLAZGOS EXTRACARDÍACOS y CONCLUSIÓN FINAL. Firma como Dr. FRANCISCO ALBERTO PASTORE MN 74144."
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                texto_final = res.choices[0].message.content
                st.markdown(texto_final)
                st.download_button("📥 DESCARGAR INFORME EN WORD", generar_docx_profesional(texto_final, fotos), "Informe_Cardiologia.docx")
