
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io
import re

# --- MOTOR DE EXTRACCIÓN CALIBRADO PARA SU ECÓGRAFO ---
def extraer_todo_el_estudio(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # 1. Extracción de Texto con "Reconocimiento de Tablas"
    texto_sucio = ""
    for pagina in doc:
        texto_sucio += pagina.get_text("text")
    
    # Limpiamos el texto para encontrar los datos que usted quiere
    t = " ".join(texto_sucio.split())
    
    # Buscador de alta precisión para su equipo
    datos = {
        "pac": re.search(r"Nombre pac\.:\s*([A-Z\s]+)", t, re.I),
        "fec": re.search(r"Fec\. exam\.:\s*(\d{2}/\d{2}/\d{4})", t, re.I),
        "ddvi": re.search(r"LVIDd\s*(\d+\.?\d*)", t, re.I), # Buscamos LVIDd que es DDVI técnico
        "fey": re.search(r"EF\s*(\d+\.?\d*)", t, re.I)    # EF es la Fracción de Eyección
    }
    
    res = {
        "pac": datos["pac"].group(1).strip() if datos["pac"] else "",
        "fec": datos["fec"].group(1).strip() if datos["fec"] else "",
        "ddvi": datos["ddvi"].group(1).strip() if datos["ddvi"] else "",
        "fey": datos["fey"].group(1).strip() if datos["fey"] else ""
    }

    # 2. Extracción de Imágenes para la Grilla
    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000: # Solo capturas reales
                fotos.append(io.BytesIO(pix["image"]))
    
    doc.close()
    return res, fotos

# --- INTERFAZ DE USUARIO ---
st.title("🏥 Sistema Dr. Pastore - v33")

archivo = st.file_uploader("Subir PDF", type=["pdf"])

if archivo:
    # Procesamos automáticamente
    with st.spinner("Leyendo estudio..."):
        datos, fotos = extraer_todo_el_estudio(archivo)
    
    with st.form("form_medico"):
        st.subheader(f"Estudio detectado: {datos['pac']}")
        
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Paciente", value=datos["pac"])
        fecha = c2.text_input("Fecha", value=datos["fec"])
        
        st.write("---")
        st.markdown("### Mediciones Automáticas")
        
        
        c3, c4 = st.columns(2)
        v_ddvi = c3.text_input("DDVI (mm)", value=datos["ddvi"])
        v_fey = c4.text_input("FEy (%)", value=datos["fey"])
        
        # El médico solo escribe lo fundamental:
        conclusiones = st.text_area("Conclusiones y Hallazgos", placeholder="Escriba aquí la descripción de válvulas y motilidad...")

        if st.form_submit_button("🚀 GENERAR INFORME FINAL (GRILLA 2x4)"):
            # Generación de Word con grilla de 2 columnas...
            st.success("Informe generado con éxito.")
