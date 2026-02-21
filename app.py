
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import fitz
from io import BytesIO
from groq import Groq
import json
import os

st.set_page_config(page_title="Informe Ecocardiograma IA")
st.title("Generador Profesional de Informe Ecocardiográfico")

excel_file = st.file_uploader("Subir Excel", type=["xlsx"])
pdf_file = st.file_uploader("Subir PDF con imágenes", type=["pdf"])

# ---------------- BUSCADOR UNIVERSAL ----------------

def buscar_valor(df, palabra):
    for i in range(len(df)):
        for j in range(len(df.columns)):
            celda = str(df.iloc[i, j])
            if palabra.lower() in celda.lower():
                if j + 1 < len(df.columns):
                    valor = str(df.iloc[i, j + 1])
                    if valor and valor.lower() != "nan":
                        return valor.strip()
    return None

# ---------------- PROCESAMIENTO ----------------

if excel_file and pdf_file:

    eco = pd.read_excel(excel_file, sheet_name="Ecodato", header=None)
    doppler = pd.read_excel(excel_file, sheet_name="Doppler", header=None)

    # DATOS GENERALES
    paciente = buscar_valor(eco, "Paciente")
    fecha = buscar_valor(eco, "Fecha")
    edad = buscar_valor(eco, "Edad")
    sexo = buscar_valor(eco, "Sexo")
    peso = buscar_valor(eco, "Peso")
    altura = buscar_valor(eco, "Altura")

    # MEDICIONES ECO
    mediciones = []
    tabla = eco.iloc[4:40, 0:3]

    for _, row in tabla.iterrows():
        parametro = str(row[0]).strip()
        valor = str(row[1]).strip()
        unidad = str(row[2]).strip()

        if parametro.lower() != "nan" and valor.lower() != "nan":
            mediciones.append({
                "parametro": parametro,
                "valor": valor,
                "unidad": unidad if unidad.lower() != "nan" else ""
            })

    # DOPPLER
    doppler_lista = []
    dop = doppler.iloc[2:25, 0:5]

    for _, row in dop.iterrows():
        valvula = str(row[0]).strip()
        velocidad = str(row[1]).strip()

        if valvula.lower() != "nan" and velocidad.lower() != "nan":
            doppler_lista.append({
                "valvula": valvula,
                "velocidad": velocidad
            })

    datos_json = {
        "paciente": paciente,
        "fecha": fecha,
        "edad": edad,
        "sexo": sexo,
        "peso": peso,
        "altura": altura,
        "ecocardiograma": mediciones,
        "doppler": doppler_lista
    }

    # ---------------- IA GROQ ----------------

    try:
        api_key = st.secrets["GROQ_API_KEY"]

        client = Groq(api_key=api_key)

        prompt = f"""
Actúa como cardiólogo clínico.

Redacta un INFORME ECOCARDIOGRAMA DOPPLER COLOR formal hospitalario.

Reglas:
- No inventar datos.
- Si peso o altura no son coherentes, omitirlos.
- No agregar recomendaciones.
- No explicar al paciente.
- No repetir JSON.
- Usar solo los datos proporcionados.
- Si falta un dato, simplemente omitirlo.

Datos:
{json.dumps(datos_json, indent=2)}
"""

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Eres un cardiologo experto en informes ecocardiograficos hospitalarios."},
                {"role": "user", "content": prompt[:5000]}
            ],
            temperature=0.1,
            max_tokens=1200
        )

        informe = response.choices[0].message.content

    except Exception as e:
        st.error(f"Error Groq: {str(e)}")
        st.stop()

    # ---------------- CREAR WORD ----------------

    doc = Document()
    doc.add_paragraph(informe)

    # ---------------- IMÁGENES 4 FILAS x 2 COLUMNAS ----------------

    pdf_bytes = pdf_file.read()
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    imagenes = []
    for page in pdf_doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base = pdf_doc.extract_image(xref)
            imagenes.append(base["image"])

    imagenes = imagenes[:8]

    if imagenes:
        table = doc.add_table(rows=4, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        idx = 0
        for fila in table.rows:
            for celda in fila.cells:
                if idx < len(imagenes):
                    celda.paragraphs[0].add_run().add_picture(
                        BytesIO(imagenes[idx]),
                        width=Inches(2.4)
                    )
                    idx += 1

    # ---------------- FIRMA ----------------

    if os.path.exists("firma.png"):
        doc.add_picture("firma.png", width=Inches(2))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # ---------------- DESCARGA ----------------

    output = "Informe_Ecocardiograma.docx"
    doc.save(output)

    with open(output, "rb") as f:
        st.download_button(
            "Descargar Informe",
            f,
            file_name=output,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
