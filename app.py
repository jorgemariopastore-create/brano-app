
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CardioReport Senior", layout="wide")

# --- 2. MOTOR DE EXTRACCIÓN MEJORADO ---
def extraer_datos_ecografo(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    texto = ""
    for pagina in doc:
        texto += pagina.get_text("text")
    t = " ".join(texto.split())
    
    # Buscamos con las etiquetas reales de su equipo (Mindray/GE)
    datos = {
        "pac": re.search(r"Nombre pac\.:\s*([A-Z\s]+)", t, re.I),
        "fec": re.search(r"Fec\. exam\.:\s*(\d{2}/\d{2}/\d{4})", t, re.I),
        "ddvi": re.search(r"LVIDd\s*(\d+\.?\d*)", t, re.I),
        "fey": re.search(r"EF\s*(\d+\.?\d*)", t, re.I)
    }
    
    res = {
        "pac": datos["pac"].group(1).strip() if datos["pac"] else "",
        "fec": datos["fec"].group(1).strip() if datos["fec"] else "",
        "ddvi": datos["ddvi"].group(1).strip() if datos["ddvi"] else "",
        "fey": datos["fey"].group(1).strip() if datos["fey"] else ""
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000:
                fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return res, fotos

# --- 3. LÓGICA DE LA APP ---
if "word_listo" not in st.session_state:
    st.session_state.word_listo = None

st.title("🏥 Generador de Informes Dr. Pastore")

archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if archivo:
    # Extraemos automáticamente
    datos, fotos = extraer_datos_ecografo(archivo)
    
    # FORMULARIO SIMPLIFICADO
    with st.form("informe_medico"):
        st.subheader("Datos Detectados (Verifique)")
        c1, c2, c3, c4 = st.columns(4)
        nom = c1.text_input("Paciente", value=datos["pac"])
        fec = c2.text_input("Fecha", value=datos["fec"])
        dvi = c3.text_input("DDVI", value=datos["ddvi"])
        fy = c4.text_input("FEy %", value=datos["fey"])
        
        st.write("---")
        # EL DOCTOR SOLO PONE ESTO (LO FUNDAMENTAL)
        conclusiones = st.text_area("Hallazgos y Conclusión Médica", 
                                   height=200,
                                   placeholder="Ej: Motilidad conservada. Válvulas normales...")
        
        boton_generar = st.form_submit_button("✅ PREPARAR DOCUMENTO")

    if boton_generar:
        # Generamos el Word
        doc = Document()
        doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        doc.add_paragraph(f"Paciente: {nom} | Fecha: {fec}")
        doc.add_paragraph(f"DDVI: {dvi} mm | FEy: {fy} %")
        
        # Agregamos la conclusión del médico (Justificada)
        p = doc.add_paragraph(conclusiones)
        p.alignment = 3 
        
        # Grilla de Imágenes 2x4
        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla = doc.add_table(rows=(len(fotos) + 1) // 2, cols=2)
            for i, f in enumerate(fotos):
                celda = tabla.rows[i // 2].cells[i % 2]
                celda.paragraphs[0].add_run().add_picture(f, width=Inches(3.0))
        
        # Guardar en sesión
        buf = io.BytesIO()
        doc.save(buf)
        st.session_state.word_listo = buf.getvalue()
        st.session_state.nombre_doc = nom

# --- 4. BOTÓN DE DESCARGA (FUERA DEL FORMULARIO PARA QUE NO FALLE) ---
if st.session_state.word_listo:
    st.markdown("---")
    st.success(f"¡Documento de {st.session_state.nombre_doc} listo!")
    st.download_button(
        label="⬇️ DESCARGAR INFORME EN WORD",
        data=st.session_state.word_listo,
        file_name=f"Informe_{st.session_state.nombre_doc}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
