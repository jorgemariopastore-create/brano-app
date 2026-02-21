
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import RGBColor
import fitz
from io import BytesIO
import os

st.set_page_config(page_title="Informe Ecocardiograma")

st.title("Generador Profesional de Informe Ecocardiográfico")

excel_file = st.file_uploader("Subir Excel", type=["xlsx"])
pdf_file = st.file_uploader("Subir PDF con imágenes", type=["pdf"])

def limpio(valor):
    if pd.isna(valor):
        return None
    valor = str(valor).strip()
    if valor == "" or valor.lower() == "nan":
        return None
    return valor

if excel_file and pdf_file:

    eco = pd.read_excel(excel_file, sheet_name="Ecodato", header=None)
    doppler = pd.read_excel(excel_file, sheet_name="Doppler", header=None)

    # ---------- DATOS PACIENTE ----------
    paciente = limpio(eco.iloc[0,1])
    fecha = limpio(eco.iloc[1,1])
    peso = limpio(eco.iloc[12,1])
    altura = limpio(eco.iloc[13,1])

    # ---------- CREAR DOCUMENTO ----------
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    doc.add_heading("INFORME ECOCARDIOGRAMA DOPPLER COLOR", level=1)

    if paciente:
        doc.add_paragraph(f"Paciente: {paciente}")
    if fecha:
        doc.add_paragraph(f"Fecha: {fecha}")
    if peso:
        doc.add_paragraph(f"Peso: {peso} Kg")
    if altura:
        doc.add_paragraph(f"Altura: {altura} cm")

    doc.add_paragraph("")

    # ---------- ECO 2D / MODO M ----------
    doc.add_heading("ECOCARDIOGRAMA", level=2)

    tabla_eco = eco.iloc[4:20, 0:3]
    tabla_eco.columns = ["Parametro","Valor","Unidad"]

    for _, row in tabla_eco.iterrows():
        parametro = limpio(row["Parametro"])
        valor = limpio(row["Valor"])
        unidad = limpio(row["Unidad"])

        if parametro and valor:
            if unidad:
                doc.add_paragraph(f"{parametro}: {valor} {unidad}")
            else:
                doc.add_paragraph(f"{parametro}: {valor}")

    doc.add_paragraph("")

    # ---------- DOPPLER ----------
    doc.add_heading("DOPPLER", level=2)

    doppler_tabla = doppler.iloc[2:10, 0:5]
    doppler_tabla.columns = ["Valvula","Vel","GradP","GradM","Insuf"]

    for _, row in doppler_tabla.iterrows():
        valvula = limpio(row["Valvula"])
        vel = limpio(row["Vel"])
        gradp = limpio(row["GradP"])
        gradm = limpio(row["GradM"])
        insuf = limpio(row["Insuf"])

        if valvula:
            linea = valvula

            datos = []
            if vel:
                datos.append(f"Vel: {vel}")
            if gradp:
                datos.append(f"Grad Pico: {gradp}")
            if gradm:
                datos.append(f"Grad Medio: {gradm}")
            if insuf:
                datos.append(f"Insuf: {insuf}")

            if datos:
                linea += " – " + " | ".join(datos)

            doc.add_paragraph(linea)

    doc.add_paragraph("")

    # ---------- IMÁGENES 4x2 ----------
    doc.add_heading("REGISTRO DE IMÁGENES", level=2)

    pdf_bytes = pdf_file.read()
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    imagenes = []
    for page in pdf_doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base = pdf_doc.extract_image(xref)
            imagenes.append(base["image"])

    imagenes = imagenes[:8]  # máximo 8

    table = doc.add_table(rows=2, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    index = 0
    for fila in table.rows:
        for celda in fila.cells:
            if index < len(imagenes):
                celda.paragraphs[0].add_run().add_picture(
                    BytesIO(imagenes[index]),
                    width=Inches(1.5)
                )
                index += 1

    doc.add_paragraph("")

    # ---------- FIRMA ----------
    if os.path.exists("firma.png"):
        firma = doc.add_picture("firma.png", width=Inches(2))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # ---------- GUARDAR ----------
    output = "Informe_Ecocardiograma.docx"
    doc.save(output)

    with open(output, "rb") as f:
        st.download_button(
            "Descargar Informe",
            f,
            file_name=output,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
