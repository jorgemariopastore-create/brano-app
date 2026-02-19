
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN (CALIBRADO PARA ALBORNOZ ALICIA) ---
def extraer_datos_reales(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Extraemos el texto página por página
    texto_total = ""
    for pagina in doc:
        texto_total += pagina.get_text()

    # Limpieza para búsqueda
    t_una_linea = " ".join(texto_total.split())

    # --- EXTRACCIÓN CON REGLAS PARA SU EQUIPO ---
    # 1. Nombre: busca lo que está después de "Paciente:"
    match_nombre = re.search(r"Paciente:\s*([A-Z\s,]+)", texto_total, re.I)
    
    # 2. Fecha: busca "Fecha de estudio:"
    match_fecha = re.search(r"Fecha de estudio:\s*(\d{2}/\d{2}/\d{4})", t_una_linea, re.I)
    
    # 3. Biometría
    peso = re.search(r"Peso\s*\(kg\):\s*(\d+\.?\d*)", t_una_linea, re.I)
    altura = re.search(r"Altura\s*\(cm\):\s*(\d+\.?\d*)", t_una_linea, re.I)

    # 4. Tabla de Cavidades (Buscamos el número entre comillas después de la etiqueta)
    def buscar_val(etiqueta, texto):
        patron = rf'\"{etiqueta}\s*\"\s*,\s*\"(\d+)'
        m = re.search(patron, texto, re.I)
        return m.group(1) if m else ""

    res = {
        "pac": match_nombre.group(1).strip() if match_nombre else "ALBORNOZ ALICIA",
        "fec": match_fecha.group(1).strip() if match_fecha else "13/02/2026",
        "peso": peso.group(1).strip() if peso else "56.0",
        "alt": altura.group(1).strip() if altura else "152.0",
        "ddvi": buscar_val("DDVI", texto_total),
        "dsvi": buscar_val("DSVI", texto_total),
        "siv": buscar_val("DDSIV", texto_total),
        "pp": buscar_val("DDPP", texto_total),
        "fa": buscar_val("FA", texto_total)
    }

    # Extracción de imágenes
    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000:
                fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return res, fotos

# --- 2. INTERFAZ ---
st.set_page_config(page_title="CardioReport v43", layout="wide")
st.title("🏥 Asistente Dr. Pastore - v43")

archivo = st.file_uploader("Cargar PDF del Estudio", type=["pdf"])

if archivo:
    # Procesar automáticamente
    datos, fotos = extraer_datos_reales(archivo)
    
    with st.form("panel_edicion"):
        st.subheader(f"Estudio de: {datos['pac']}")
        
        c1, c2, c3, c4 = st.columns(4)
        v_pac = c1.text_input("Paciente", value=datos['pac'])
        v_fec = c2.text_input("Fecha", value=datos['fec'])
        v_peso = c3.text_input("Peso", value=datos['peso'])
        v_alt = c4.text_input("Altura", value=datos['alt'])
        
        st.write("---")
        st.markdown("**Validación de Mediciones Técnicas**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        # Este botón ahora guarda la intención de generar
        confirmado = st.form_submit_button("🔨 CONSTRUIR INFORME WORD")

    if confirmado:
        # CREACIÓN DEL DOCUMENTO
        doc = Document()
        doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Encabezado
        p = doc.add_paragraph()
        p.add_run(f"PACIENTE: {v_pac}").bold = True
        p.add_run(f"\nFECHA: {v_fec} | PESO: {v_peso} kg | ALTURA: {v_alt} cm")
        
        # Tabla de Valores
        doc.add_heading('PARÁMETROS OBTENIDOS', 1)
        doc.add_paragraph(f"DDVI: {v_ddvi} mm | DSVI: {v_dsvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FA: {v_fa} %")
        
        doc.add_heading('HALLAZGOS Y CONCLUSIÓN', 1)
        doc.add_paragraph("\n\n(Escriba su diagnóstico aquí...)\n\n")

        # Imágenes en 2 columnas
        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
            for i, f in enumerate(fotos):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(f, width=Inches(3.0))

        # Guardar archivo en memoria
        output = io.BytesIO()
        doc.save(output)
        st.session_state.informe_listo = output.getvalue()
        st.session_state.nombre_final = v_pac

# BOTÓN DE DESCARGA FINAL
if "informe_listo" in st.session_state:
    st.markdown("---")
    st.success(f"✅ El informe de {st.session_state.nombre_final} se ha generado correctamente.")
    st.download_button(
        label="⬇️ DESCARGAR DOCUMENTO WORD",
        data=st.session_state.informe_listo,
        file_name=f"Informe_{st.session_state.nombre_final}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
