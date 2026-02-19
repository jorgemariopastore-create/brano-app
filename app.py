
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# --- 2. MOTOR DE EXTRACCIÓN (CALIBRADO) ---
def motor_pastore_extractor(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    t = " ".join(texto.split())
    
    # Búsqueda de datos (Nombre y Fecha funcionan bien en su equipo)
    res = {
        "pac": re.search(r"Nombre pac\.:\s*([A-Z\s]+)", t, re.I),
        "fec": re.search(r"Fec\. exam\.:\s*(\d{2}/\d{2}/\d{4})", t, re.I),
        "ddvi": re.search(r"LVIDd\s*(\d+\.?\d*)", t, re.I),
        "fey": re.search(r"EF\s*(\d+\.?\d*)", t, re.I)
    }
    
    datos = {
        "pac": res["pac"].group(1).strip() if res["pac"] else "",
        "fec": res["fec"].group(1).strip() if res["fec"] else "",
        "ddvi": res["ddvi"].group(1).strip() if res["ddvi"] else "",
        "fey": res["fey"].group(1).strip() if res["fey"] else ""
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000: # Filtro de calidad
                fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return datos, fotos

# --- 3. INTERFAZ Y FORMULARIO ---
archivo = st.file_uploader("1. Suba el PDF del Ecógrafo aquí", type=["pdf"])

if archivo:
    # Extraemos automáticamente lo que el equipo entrega
    datos_auto, lista_fotos = motor_pastore_extractor(archivo)
    
    st.success(f"Estudio detectado: {datos_auto['pac']}")

    # Formulario para que el doctor complete lo esencial
    with st.form("panel_control"):
        st.subheader("2. Complete los datos esenciales")
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Paciente", value=datos_auto["pac"])
        fecha = c2.text_input("Fecha", value=datos_auto["fec"])
        
        st.markdown("---")
        
        c3, c4, c5, c6 = st.columns(4)
        v_ddvi = c3.text_input("DDVI (mm)", value=datos_auto["ddvi"])
        v_siv = c4.text_input("SIV (mm)")
        v_pp = c5.text_input("PP (mm)")
        v_fey = c6.text_input("FEy (%)", value=datos_auto["fey"])
        
        st.info("💡 Al generar el Word, podrá escribir su conclusión y diagnóstico final en el documento.")
        
        btn_preparar = st.form_submit_button("🚀 PREPARAR INFORME WORD")

    # --- 4. GENERACIÓN DEL WORD (FUERA DEL FORMULARIO) ---
    if btn_preparar:
        doc = Document()
        doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        
        # Datos Principales
        p_datos = doc.add_paragraph()
        p_datos.add_run(f"Paciente: {nombre}\n").bold = True
        p_datos.add_run(f"Fecha: {fecha}\n")
        p_datos.add_run(f"DDVI: {v_ddvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FEy: {v_fey} %")
        
        # Espacio para Conclusión (Usted la escribe en el Word)
        doc.add_heading('HALLAZGOS Y CONCLUSIÓN', 2)
        p_conc = doc.add_paragraph("\n\n(Escriba aquí su conclusión médica...)\n\n")
        p_conc.alignment = 3 # Justificado
        
        # Grilla de Imágenes 2x4
        if lista_fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla = doc.add_table(rows=(len(lista_fotos) + 1) // 2, cols=2)
            for i, f_img in enumerate(lista_fotos):
                celda = tabla.rows[i // 2].cells[i % 2]
                celda.paragraphs[0].add_run().add_picture(f_img, width=Inches(3.0))
        
        # Guardar y habilitar descarga
        buffer = io.BytesIO()
        doc.save(buffer)
        st.session_state.archivo_descarga = buffer.getvalue()
        st.session_state.nombre_pac = nombre

# --- 5. BOTÓN DE DESCARGA (SIEMPRE VISIBLE CUANDO ESTÁ LISTO) ---
if "archivo_descarga" in st.session_state and st.session_state.archivo_descarga:
    st.markdown("---")
    st.download_button(
        label=f"⬇️ DESCARGAR INFORME DE {st.session_state.nombre_pac}",
        data=st.session_state.archivo_descarga,
        file_name=f"Informe_{st.session_state.nombre_pac}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
