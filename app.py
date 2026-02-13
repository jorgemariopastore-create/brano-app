
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI", layout="wide")
st.title("❤️ CardioReport AI - Formato Profesional")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx_inteligente(texto_ia, imagenes):
    doc = Document()
    
    # Márgenes equilibrados para aprovechar espacio
    section = doc.sections[0]
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)

    # Título Principal
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)
    p_tit.paragraph_format.space_after = Pt(10)

    # Procesar líneas
    lineas = texto_ia.split('\n')
    for i, linea in enumerate(lineas):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        # Lógica de formato
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold = True
            run.underline = True
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True 
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(4)
            
            # Si estamos en la parte final (Conclusión o Firma), evitamos que se separen
            if "CONCLUSIÓN" in texto_ia.split('\n')[max(0, i-5):i+1] or "DR." in linea.upper():
                p.paragraph_format.keep_with_next = True

    # ANEXO: SIEMPRE EMPIEZA EN HOJA NUEVA
    if imagenes:
        doc.add_page_break() 
        p_an = doc.add_paragraph()
        r_an = p_an.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_an.bold = True
        r_an.underline = True
        p_an.paragraph_format.space_after = Pt(10)
        
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_i = cell_p.add_run()
                    # Tamaño para asegurar 4 filas por página
                    run_i.add_picture(io.BytesIO(img_data), width=Inches(2.45))
                    cell_p.add_run(f"\nFig. {i + j + 1}")
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir archivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        fotos = []
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
            with st.spinner("Procesando..."):
                prompt = f"Actúa como cardiólogo. Redacta el informe basado en: {texto_ext}. Estructura: DATOS DEL PACIENTE, I. EVALUACIÓN ANATÓMICA, II. FUNCIÓN VENTRICULAR, III. EVALUACIÓN HEMODINÁMICA, IV. HALLAZGOS EXTRACARDÍACOS y CONCLUSIÓN FINAL. Firma al final como Dr. FRANCISCO ALBERTO PASTORE MN 74144."
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                texto_final = res.choices[0].message.content
                st.markdown(texto_final)
                
                wb = generar_docx_inteligente(texto_final, fotos)
                st.download_button("📥 DESCARGAR WORD", wb, "Informe_Cardio_Final.docx")
