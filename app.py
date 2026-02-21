
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import fitz
from io import BytesIO
import os

st.set_page_config(page_title="Informe Ecocardiograma")

st.title("Generador Profesional de Informe Ecocardiográfico")

excel_file = st.file_uploader("Subir Excel", type=["xlsx"])
pdf_file = st.file_uploader("Subir PDF con imágenes", type=["pdf"])

def limpio(v):
    if pd.isna(v):
        return None
    v = str(v).strip()
    if v == "" or v.lower() == "nan":
        return None
    return v

if excel_file and pdf_file:

    eco = pd.read_excel(excel_file, sheet_name="Ecodato", header=None)
    doppler = pd.read_excel(excel_file, sheet_name="Doppler", header=None)

    # ---------------- DATOS CORRECTOS ----------------
    paciente = limpio(eco.iloc[0,1])
    fecha = limpio(eco.iloc[1,1])

    # Peso y altura correctos (los que están abajo)
    peso = limpio(eco.iloc[14,1])
    altura = limpio(eco.iloc[15,1])

    # ---------------- CREAR DOCUMENTO ----------------
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

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

    # ---------------- ECOCARDIOGRAMA ----------------
    doc.add_heading("ECOCARDIOGRAMA BIDIMENSIONAL Y MODO M", level=2)

    tabla = eco.iloc[4:14, 0:3]
    tabla.columns = ["Parametro","Valor","Unidad"]

    datos = {}
    for _, row in tabla.iterrows():
        p = limpio(row["Parametro"])
        v = limpio(row["Valor"])
        u = limpio(row["Unidad"])
        if p and v:
            datos[p] = f"{v} {u}" if u else v

    # Cavidades
    if "DDVI" in datos:
        doc.add_paragraph(f"Diámetro diastólico VI: {datos['DDVI']}")
    if "DSVI" in datos:
        doc.add_paragraph(f"Diámetro sistólico VI: {datos['DSVI']}")
    if "DDVD" in datos:
        doc.add_paragraph(f"Diámetro VD: {datos['DDVD']}")
    if "DDAI" in datos:
        doc.add_paragraph(f"Aurícula izquierda: {datos['DDAI']}")
    if "DRAO" in datos:
        doc.add_paragraph(f"Raíz aórtica: {datos['DRAO']}")

    # Función
    if "FA" in datos:
        doc.add_paragraph(f"Fracción de acortamiento: {datos['FA']}")
    if "Masa" in datos:
        doc.add_paragraph(f"Masa ventricular izquierda: {datos['Masa']}")

    doc.add_paragraph("")

    # ---------------- DOPPLER ----------------
    doc.add_heading("DOPPLER COLOR", level=2)

    dop = doppler.iloc[2:8, 0:5]
    dop.columns = ["Valvula","Vel","GradP","GradM","Insuf"]

    for _, row in dop.iterrows():
        valvula = limpio(row["Valvula"])
        vel = limpio(row["Vel"])
        if valvula and vel:
            doc.add_paragraph(f"{valvula}: velocidad máxima {vel}")

    doc.add_paragraph("")

    # ---------------- CONCLUSIÓN TÉCNICA ----------------
    doc.add_heading("CONCLUSIÓN", level=2)
    doc.add_paragraph(
        "Estudio ecocardiográfico bidimensional y Doppler realizado. "
        "Mediciones consignadas según valores obtenidos."
    )

    doc.add_paragraph("")

    # ---------------- IMÁGENES 4 FILAS x 2 COLUMNAS ----------------
    doc.add_heading("REGISTRO DE IMÁGENES", level=2)

    pdf_bytes = pdf_file.read()
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    imagenes = []
    for page in pdf_doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base = pdf_doc.extract_image(xref)
            imagenes.append(base["image"])

    imagenes = imagenes[:8]

    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    idx = 0
    for fila in table.rows:
        for celda in fila.cells:
            if idx < len(imagenes):
                celda.paragraphs[0].add_run().add_picture(
                    BytesIO(imagenes[idx]),
                    width=Inches(2.5)
                )
                idx += 1

    doc.add_paragraph("")

    # ---------------- FIRMA ----------------
    try:
        doc.add_picture("firma.png", width=Inches(2))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    except:
        pass

    # ---------------- GUARDAR ----------------
    output = "Informe_Ecocardiograma.docx"
    doc.save(output)

    with open(output, "rb") as f:
        st.download_button(
            "Descargar Informe",
            f,
            file_name=output,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
