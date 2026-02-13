
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI", layout="wide")
st.title("❤️ CardioReport AI - Edición Final")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx_perfecto(texto_ia, imagenes):
    doc = Document()
    
    # Configuración de márgenes profesionales
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
    p_tit.paragraph_format.space_after = Pt(12)

    # Procesar líneas y evitar cortes de hoja malos
    lineas = texto_ia.split('\n')
    for linea in lineas:
        linea = linea.replace('**', '').strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Detección estricta de títulos médicos
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold = True
            run.underline = True
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True # OBLIGA al título a estar con su texto
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.widow_control = True # Evita líneas sueltas

    # ANEXO: 8 IMÁGENES (Control de salto de página)
    if imagenes:
        # Insertar salto solo si hay imágenes, pegado al texto
        doc.add_page_break() 
        p_an = doc.add_paragraph()
        r_an = p_an.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_an.bold = True
        r_an.underline = True
        p_an.paragraph_format.space_after = Pt(10)
        
        # Tabla optimizada para 2x4
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_i = cell_p.add_run()
                    # Ancho fijo para mantener la cuadrícula de 8 por página
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

        if st.button("Generar Informe Perfecto"):
            with st.spinner("Finalizando formato médico..."):
                prompt = f"Actúa como cardiólogo. Redacta el informe basado en: {texto_ext}. Usa el esquema: DATOS DEL PACIENTE, I. EVALUACIÓN ANATÓMICA, II. FUNCIÓN VENTRICULAR, III. EVALUACIÓN HEMODINÁMICA, IV. HALLAZGOS EXTRACARDÍACOS y CONCLUSIÓN FINAL. Firma como Dr. FRANCISCO ALBERTO PASTORE MN 74144."
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                texto_final = res.choices[0].message.content
                st.markdown(texto_final)
                
                wb = generar_docx_perfecto(texto_final, fotos)
                st.download_button("📥 DESCARGAR WORD FINAL", wb, "Informe_Medico_Final.docx")
