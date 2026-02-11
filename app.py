import streamlit as st
from PIL import Image
import pytesseract
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# CONFIGURACIÓN TÉCNICA (Ajustá esta ruta si instalaste Tesseract en otro lado)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="CardioReport AI Pro", layout="wide")

st.title("🩺 CardioReport AI: Generador de Informes")
st.markdown("---")

# 1. Carga de archivos
archivos = st.file_uploader("Subí todas las capturas del estudio (JPG/PNG)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

if archivos:
    col_pre, col_form = st.columns([1, 1.2])
    
    with col_pre:
        st.subheader("🖼️ Vista Previa")
        for arc in archivos:
            st.image(arc, width=180)

    with col_form:
        st.subheader("📝 Datos del Informe")
        nombre = st.text_input("Nombre del Paciente", "NILDA RODRIGUEZ")
        
        # Intentamos extraer datos de la PRIMERA imagen subida como prueba
        if st.button("Sugerir datos de la 1er imagen"):
            texto = pytesseract.image_to_string(Image.open(archivos[0]))
            fe_match = re.search(r"(FE|EF)[\s:]+(\d+\.?\d*)", texto, re.I)
            st.session_state['fe_val'] = fe_match.group(2) if fe_match else "---"
        
        fe = st.text_input("Fracción de Eyección (%)", st.session_state.get('fe_val', ""))
        conclusion = st.text_area("Conclusión Diagnóstica", "Función sistólica conservada. Ver detalles en anexo de imágenes.")

        if st.button("🚀 GENERAR INFORME DEFINITIVO (WORD)"):
            doc = Document()
            
            # Estilo del Título
            encabezado = doc.add_heading('INFORME DE ECOCARDIOGRAMA', 0)
            encabezado.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Datos Principales
            p = doc.add_paragraph()
            p.add_run("Paciente: ").bold = True
            p.add_run(nombre)
            p.add_run(f"\nFecha del estudio: 09/02/2026")

            doc.add_heading('Resultados y Parámetros', level=1)
            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            table.rows[0].cells[0].text = 'Parámetro'
            table.rows[0].cells[1].text = 'Valor'
            row = table.add_row().cells
            row[0].text = 'Fracción de Eyección (FEy)'
            row[1].text = f"{fe}%"

            doc.add_heading('Conclusión', level=1)
            doc.add_paragraph(conclusion)

            # ANEXO DE IMÁGENES EN GRILLA
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            num_fotos = len(archivos)
            rows = (num_fotos + 1) // 2 
            tabla_fotos = doc.add_table(rows=rows, cols=2)
            
            for i, arc in enumerate(archivos):
                row_idx = i // 2
                col_idx = i % 2
                cell = tabla_fotos.rows[row_idx].cells[col_idx]
                
                # Insertar Imagen
                img_pil = Image.open(arc)
                temp_img = io.BytesIO()
                img_pil.save(temp_img, format='PNG')
                temp_img.seek(0)
                
                paragraph = cell.paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(temp_img, width=Inches(2.8)) 
                
                # Etiqueta (Figura X)
                etiqueta = cell.add_paragraph(f"Figura {i+1}")
                etiqueta.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_et = etiqueta.runs[0]
                run_et.font.size = Pt(9)
                run_et.italic = True

            # Guardar y Descargar
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(
                label="📥 DESCARGAR ARCHIVO WORD",
                data=bio.getvalue(),
                file_name=f"Informe_{nombre.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )