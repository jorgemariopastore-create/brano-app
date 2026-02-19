
import streamlit as st
import fitz  # PyMuPDF
import re
import tempfile
import os
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ------------------------------
# FUNCIONES AUXILIARES
# ------------------------------

def safe(val):
    if not val or str(val).strip() == "":
        return "No evaluable"
    return val


def extraer_dato_universal(texto, clave):
    patron_tabla = rf"\"{clave}\"\s*,\s*\"([\d.,]+)\""
    match_t = re.search(patron_tabla, texto, re.IGNORECASE)
    if match_t:
        return match_t.group(1).replace(',', '.')

    patron_txt = rf"{clave}.*?[:=\s]\s*([\d.,]+)"
    match_s = re.search(patron_txt, texto, re.IGNORECASE)
    if match_s:
        return match_s.group(1).replace(',', '.')

    return ""


def extract_images_from_pdf(pdf_bytes, output_dir):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        images = page.get_images(full=True)

        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            image_path = os.path.join(
                output_dir,
                f"img_{page_index}_{img_index}.{ext}"
            )

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            image_paths.append(image_path)

    return image_paths


def build_word_report(datos, pdf_bytes, output_path, tmpdir):

    doc = Document()

    doc.add_heading("Ecocardiograma 2D y Doppler Cardíaco Color", level=1)

    doc.add_paragraph(f"Paciente: {datos['pac']}")
    doc.add_paragraph("")

    doc.add_heading("MEDICIONES", level=2)
    doc.add_paragraph(f"DDVI: {safe(datos['dv'])} mm")
    doc.add_paragraph(f"SIV: {safe(datos['si'])} mm")
    doc.add_paragraph(f"Fracción de eyección: {safe(datos['fy'])} %")

    doc.add_heading("CONCLUSIÓN", level=2)

    try:
        fey = float(datos["fy"])
        if fey > 55:
            doc.add_parag_
