
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

st.title("Generador Profesional de Informe Ecocardiográfico con IA")

excel_file = st.file_uploader("Subir Excel", type=["xlsx"])
pdf_file = st.file_uploader("Subir PDF con imágenes", type=["pdf"])


# ---------------- FUNCION PARA BUSCAR VALORES POR ETIQUETA ----------------

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


if excel_file and pdf_file:

    # ---------------- LEER EXCEL ----------------

    eco = pd.read_excel(excel_file, sheet_name="Ecodato", header=None)
    doppler = pd.read_excel(excel_file, sheet_name="Doppler", header=None)

    # ---------------- EXTRAER DATOS SEGUROS ----------------

    paciente = buscar_valor(eco, "Paciente")
    fecha = buscar_valor(eco, "Fecha")
    edad = buscar_valor(eco, "Edad")
    sexo = buscar_valor(eco, "Sexo")
    peso = buscar_valor(eco, "Peso")
    altura = buscar_valor(eco, "Altura")

    # ---------------- EXTRAER MEDICIONES ECO ----------------

    mediciones = []
    tabla = eco.iloc[4:25, 0:3]

    for _, row in tabla.iterrows():
        p = str(row[0]).strip()
        v = str(row[1]).strip()
        u = str(row[2]).strip()

        if p and p.lower() != "nan" and v and v.lower() != "nan":
            mediciones.append({
                "parametro": p,
                "valor": v,
                "unidad": u if u.lower() != "nan" else ""
            })

    # ---------------- EXTRAER DOPPLER ----------------

    doppler_lista = []
    dop = doppler.iloc[2:15, 0:5]

    for _, row in dop.iterrows():
        valvula = str(row[0]).strip()
        vel = str(row[1]).strip()

        if valvula and valvula.lower() != "nan" and vel and vel.lower() != "nan":
            doppler_lista.append({
                "valvula": valvula,
                "velocidad": vel
            })

    datos_clinicos = {
        "paciente": paciente,
        "fecha": fecha,
        "edad": edad,
        "sexo": sexo,
        "peso": peso,
        "altura": altura,
        "ecocardiograma": mediciones,
        "doppler": doppler_lista
    }

    # ---------------- GROQ IA ----------------

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])

        prompt = f"""
Actúa como cardiólogo.

Redacta un informe médico formal de ecocardiograma.

Reglas estrictas:
- No inventar ningún dato.
- Si peso o altura no son coherentes, omitirlos.
- No incluir recomendaciones.
- No explicar nada al paciente.
- Estilo hospitalario profesional.
- Estructura:
    INFORME ECOCARDIOGRAMA DOPPLER COLOR
    Datos del paciente
    Ecocardiograma bidimensional
    Doppler
    Conclusión técnica breve

Datos clínicos en JSON:
{json.dumps(datos_clinicos, indent=2)}
"""

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Eres un cardiologo que redacta informes medicos formales."},
                {"role": "user", "content": prompt[:6000]}
            ],
            temperature=0.1,
            max_tokens=1500
        )

        informe = response.choices[0].message.content

    except Exception as e:
        st.error("Error en Groq. Revisar API Key o tamaño del prompt.")
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
                        width=Inches(2.5)
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
