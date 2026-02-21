
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
from io import BytesIO
import os

st.set_page_config(page_title="Informe Ecocardiograma")

st.title("Generador Profesional de Informe Ecocardiográfico")

excel_file = st.file_uploader("Subir Excel", type=["xlsx"])
pdf_file = st.file_uploader("Subir PDF con imágenes", type=["pdf"])

def safe(val):
    if pd.isna(val):
        return "No evaluable"
    return str(val)

if excel_file and pdf_file:

    eco = pd.read_excel(excel_file, sheet_name="Ecodato", header=None)
    doppler = pd.read_excel(excel_file, sheet_name="Doppler", header=None)

    # -------- DATOS PACIENTE --------
    paciente = safe(eco.iloc[0,1])
    fecha = safe(eco.iloc[1,1])

    # -------- MEDICIONES ECO (tabla desde fila 4) --------
    mediciones = eco.iloc[4:20, 0:3]
    mediciones.columns = ["Parametro","Valor","Unidad"]

    # -------- CREAR DOCUMENTO --------
    doc = Document()
    doc.add_heading("INFORME ECOCARDIOGRAMA DOPPLER COLOR", level=1)

    doc.add_paragraph(f"Paciente: {paciente}")
    doc.add_paragraph(f"Fecha: {fecha}")
    doc.add_paragraph(" ")

    # -------- ECOCARDIOGRAMA --------
    doc.add_heading("ECOCARDIOGRAMA MODO M / 2D", level=2)

    for _, row in mediciones.iterrows():
        parametro = safe(row["Parametro"])
        valor = safe(row["Valor"])
        unidad = safe(row["Unidad"])
        if parametro != "No evaluable":
            doc.add_paragraph(f"{parametro}: {valor} {unidad}")

    doc.add_paragraph(" ")

    # -------- DOPPLER --------
    doc.add_heading("DOPPLER", level=2)

    doppler_tabla = doppler.iloc[2:10, 0:5]
    doppler_tabla.columns = ["Valvula","Velocidad","Grad_Pico","Grad_Medio","Insuf"]

    for _, row in doppler_tabla.iterrows():
        valvula = safe(row["Valvula"])
        if valvula != "No evaluable":
            doc.add_paragraph(
                f"{valvula} - Velocidad: {safe(row['Velocidad'])} cm/s | "
                f"Gradiente Pico: {safe(row['Grad_Pico'])} | "
                f"Gradiente Medio: {safe(row['Grad_Medio'])} | "
                f"Insuficiencia: {safe(row['Insuf'])}"
            )

    doc.add_paragraph(" ")

    # -------- IMÁGENES DESDE PDF --------
    doc.add_heading("REGISTRO DE IMÁGENES", level=2)

    pdf_bytes = pdf_file.read()
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    images = []
    for page in pdf_doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = pdf_doc.extract_image(xref)
            images.append(base_image["image"])

    table = doc.add_table(rows=2, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    img_index = 0
    for row in table.rows:
        for cell in row.cells:
            if img_index < len(images):
                cell.paragraphs[0].add_run().add_picture(
                    BytesIO(images[img_index]),
                    width=Inches(1.4)
                )
                img_index += 1

    doc.add_paragraph(" ")

    # -------- FIRMA --------
    if os.path.exists("firma.png"):
        doc.add_picture("firma.png", width=Inches(2))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # -------- GUARDAR --------
    output_path = "Informe_Ecocardiograma.docx"
    doc.save(output_path)

    with open(output_path, "rb") as f:
        st.download_button(
            "Descargar Informe Word",
            f,
            file_name=output_path,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
