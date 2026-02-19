
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
            doc.add_paragraph("Función sistólica global conservada.")
        else:
            doc.add_paragraph("Función sistólica global disminuida.")
    except:
        doc.add_paragraph("Función sistólica: No evaluable.")

    try:
        siv = float(datos["si"])
        if siv >= 11:
            doc.add_paragraph("Remodelado concéntrico.")
    except:
        pass

    # ANEXO DE IMÁGENES
    images = extract_images_from_pdf(pdf_bytes, tmpdir)

    if images:
        doc.add_page_break()
        doc.add_heading("ANEXO DE IMÁGENES", level=2)

        table = doc.add_table(rows=4, cols=2)

        img_index = 0
        for row in table.rows:
            for cell in row.cells:
                if img_index < len(images):
                    paragraph = cell.paragraphs[0]
                    run = paragraph.add_run()
                    run.add_picture(images[img_index], width=Inches(2.5))
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    img_index += 1

    doc.save(output_path)


# ------------------------------
# STREAMLIT APP
# ------------------------------

st.set_page_config(page_title="CardioReport Master", layout="wide")
st.title("🏥 Generador de Informe Ecocardiográfico")

if "datos" not in st.session_state:
    st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}

with st.sidebar:
    st.header("Carga de Archivos")
    arc_txt = st.file_uploader("Archivo TXT", type=["txt"])
    arc_pdf = st.file_uploader("Archivo PDF", type=["pdf"])

    if st.button("Nuevo Paciente"):
        st.session_state.datos = {"pac": "", "dv": "", "si": "", "fy": ""}
        st.rerun()


if arc_txt and arc_pdf:

    if st.session_state.datos["pac"] == "":
        with st.spinner("Procesando archivos..."):

            t_raw = arc_txt.read().decode("latin-1", errors="ignore")

            p_bytes = arc_pdf.read()
            texto_pdf = ""
            with fitz.open(stream=p_bytes, filetype="pdf") as doc:
                texto_pdf = "".join([pag.get_text() for pag in doc])

            texto_total = t_raw + "\n" + texto_pdf

            n_m = re.search(r"(?:Paciente|Nombre pac\.|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)

            ddvi = extraer_dato_universal(texto_total, "DDVI")
            siv = extraer_dato_universal(texto_total, "DDSIV")

            fey = extraer_dato_universal(texto_total, "FE") or extraer_dato_universal(texto_total, "EF")

            st.session_state.datos = {
                "pac": n_m.group(1).strip().upper() if n_m else "DESCONOCIDO",
                "dv": ddvi,
                "si": siv,
                "fy": fey
            }


if st.session_state.datos["pac"] != "":

    with st.form("validador"):
        st.subheader("Validar Datos Extraídos")

        c1, c2, c3, c4 = st.columns(4)

        pac_edit = c1.text_input("Paciente", st.session_state.datos["pac"])
        fey_edit = c2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi_edit = c3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv_edit = c4.text_input("SIV mm", st.session_state.datos["si"])

        submit = st.form_submit_button("Generar Informe Word")

    if submit:

        st.session_state.datos.update({
            "pac": pac_edit,
            "fy": fey_edit,
            "dv": ddvi_edit,
            "si": siv_edit
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = f"{tmpdir}/Informe_Ecocardiograma.docx"

            build_word_report(
                st.session_state.datos,
                arc_pdf.getvalue(),
                output_path,
                tmpdir
            )

            with open(output_path, "rb") as f:
                st.download_button(
                    "📄 Descargar Informe en Word",
                    f,
                    file_name="Informe_Ecocardiograma.docx"
                )

else:
    st.info("Carga el TXT y el PDF para comenzar.")
