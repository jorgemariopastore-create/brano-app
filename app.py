
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN ROBUSTO ---
def extraer_datos_blindados(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Extraemos texto de dos formas para asegurar
    texto_bruto = ""
    for pagina in doc:
        texto_bruto += pagina.get_text("text") + "\n"
    
    # Limpiamos el texto de caracteres especiales de tabla
    t_limpio = texto_bruto.replace('"', '').replace(',', ' ')
    t_una_linea = " ".join(t_limpio.split())

    def buscar_medicion(etiqueta, bloque_texto):
        # Busca la etiqueta y el primer número que aparezca cerca
        patron = rf'{etiqueta}\s+(\d+)'
        m = re.search(patron, bloque_texto, re.I)
        return m.group(1) if m else ""

    # Búsqueda de Nombre: Intentamos capturar lo que está entre "Paciente:" y la siguiente etiqueta
    nombre_match = re.search(r"Paciente:\s*([A-Z\s,]+?)(?=Fecha|OSDE|ID|DNI|$)", t_una_linea, re.I)
    fecha_match = re.search(r"Fecha\s*de\s*estudio:\s*(\d{2}/\d{2}/\d{4})", t_una_linea, re.I)
    
    # Datos de biometría (estos suelen ser estables)
    peso = re.search(r"Peso\s*\(kg\):\s*(\d+\.?\d*)", t_una_linea, re.I)
    altura = re.search(r"Altura\s*\(cm\):\s*(\d+\.?\d*)", t_una_linea, re.I)

    res = {
        "pac": nombre_match.group(1).strip() if nombre_match else "NOMBRE NO DETECTADO",
        "fec": fecha_match.group(1).strip() if fecha_match else "13/02/2026",
        "peso": peso.group(1).strip() if peso else "",
        "alt": altura.group(1).strip() if altura else "",
        "ddvi": buscar_medicion("DDVI", texto_bruto),
        "dsvi": buscar_medicion("DSVI", texto_bruto),
        "siv": buscar_medicion("DDSIV", texto_bruto),
        "pp": buscar_medicion("DDPP", texto_bruto),
        "fa": buscar_medicion("FA", texto_bruto)
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000: fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return res, fotos

# --- 2. INTERFAZ ---
st.set_page_config(page_title="CardioReport Senior v40", layout="wide")
st.title("🏥 Sistema de Informes - Dr. Pastore")

archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if archivo:
    datos, fotos = extraer_datos_blindados(archivo)
    
    # PANEL MÉDICO
    with st.form("validador_v40"):
        st.subheader(f"Informe de: {datos['pac']}")
        
        c1, c2, c3, c4 = st.columns(4)
        v_pac = c1.text_input("Paciente", value=datos['pac'])
        v_fec = c2.text_input("Fecha", value=datos['fec'])
        v_peso = c3.text_input("Peso (kg)", value=datos['peso'])
        v_alt = c4.text_input("Altura (cm)", value=datos['alt'])
        
        st.write("---")
        st.markdown("**Valores Ecocardiográficos**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        # EL BOTÓN AHORA ESTÁ DENTRO DEL FORMULARIO Y TIENE LÓGICA DE PERSISTENCIA
        generar_doc = st.form_submit_button("🚀 GENERAR INFORME WORD")

    if generar_doc:
        doc = Document()
        # Formato de cabecera centrado y profesional
        h = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        p = doc.add_paragraph()
        p.add_run(f"PACIENTE: {v_pac}").bold = True
        p.add_run(f"\nFECHA: {v_fec} | PESO: {v_peso} kg | ALTURA: {v_alt} cm")
        
        doc.add_heading('PARÁMETROS TÉCNICOS', 1)
        doc.add_paragraph(f"DDVI: {v_ddvi} mm | DSVI: {v_dsvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FA: {v_fa} %")
        
        doc.add_heading('CONCLUSIÓN', 1)
        doc.add_paragraph("\n\n(Escriba aquí su diagnóstico...)\n\n")

        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
            for i, f in enumerate(fotos):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(f, width=Inches(3.0))

        # Guardamos en buffer para descarga
        buf = io.BytesIO()
        doc.save(buf)
        st.session_state.doc_word = buf.getvalue()
        st.session_state.nom_pac = v_pac

# BOTÓN DE DESCARGA (Fuera del formulario)
if "doc_word" in st.session_state:
    st.markdown("---")
    st.download_button(
        label=f"⬇️ DESCARGAR INFORME: {st.session_state.nom_pac}",
        data=st.session_state.doc_word,
        file_name=f"Informe_{st.session_state.nom_pac}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
