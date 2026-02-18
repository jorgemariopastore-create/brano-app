
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- LÓGICA DE NEGOCIO (SENIOR LAYER) ---

class EcoParser:
    """Clase especializada en extraer datos técnicos de archivos Sonoscape."""
    
    # Mapeo de etiquetas técnicas a nombres entendibles
    MAPEO_ETIQUETAS = {
        'LVID(d)': 'ddvi', 'LVIDd': 'ddvi',
        'LVID(s)': 'dsvi', 'LVIDs': 'dsvi',
        'IVS(d)': 'septum', 'IVSd': 'septum', 'DDSIV': 'septum',
        'LVPW(d)': 'pared', 'LVPWd': 'pared', 'DDPP': 'pared',
        'EF(Teich)': 'fey', 'EF': 'fey',
        'FS(Teich)': 'fa', 'FS': 'fa'
    }

    @staticmethod
    def parsear_texto(texto):
        """Recorre el texto buscando bloques de mediciones."""
        resultados = {k: "No evaluado" for k in ['ddvi', 'dsvi', 'septum', 'pared', 'fey', 'fa']}
        
        # Dividimos por bloques [MEASUREMENT] para mayor precisión
        bloques = texto.split('[MEASUREMENT]')
        
        for bloque in bloques:
            # Buscamos el ítem y su valor dentro del mismo bloque
            match_item = re.search(r'item\s*=\s*([^\r\n]+)', bloque, re.I)
            match_val = re.search(r'value\s*=\s*([\d\.,]+)', bloque, re.I)
            
            if match_item and match_val:
                etiqueta_encontrada = match_item.group(1).strip()
                valor = match_val.group(1).replace(',', '.')
                
                # Si la etiqueta está en nuestro diccionario, guardamos el valor
                for clave_tec, clave_interna in EcoParser.MAPEO_ETIQUETAS.items():
                    if clave_tec.lower() == etiqueta_encontrada.lower():
                        # Validación de rango médico (Evita capturar IDs o fechas)
                        try:
                            val_f = float(valor)
                            if (clave_interna in ['fey', 'fa'] and 10 < val_f < 95) or \
                               (clave_interna not in ['fey', 'fa'] and 0.5 < val_f < 80):
                                resultados[clave_interna] = valor
                        except ValueError:
                            continue
        return resultados

# --- CAPA DE UI Y GENERACIÓN ---

def generar_word_senior(reporte_texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Encabezado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Procesar líneas de texto evitando redundancias de la IA
    for linea in reporte_texto.split('\n'):
        linea = linea.strip()
        if not linea or "proporcionan" in linea.lower(): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma profesional
    doc.add_paragraph("\n")
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_f = f_p.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    run_f.bold = True

    # Imágenes en tabla 2x2
    if pdf_bytes:
        doc.add_page_break()
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = []
        for page in pdf_file:
            for img in page.get_images(full=True):
                imgs.append(pdf_file.extract_image(img[0])["image"])
        
        if imgs:
            doc.add_paragraph("ANEXO DE IMÁGENES").alignment = WD_ALIGN_PARAGRAPH.CENTER
            table = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, data in enumerate(imgs):
                cell_p = table.cell(i//2, i%2).paragraphs[0]
                cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell_p.add_run().add_picture(io.BytesIO(data), width=Inches(2.8))
        pdf_file.close()

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- MAIN APP ---

st.set_page_config(page_title="CardioReport Pro Senior", layout="centered")
st.title("❤️ Sistema de Informes Médicos")

archivo_txt = st.file_uploader("1. Datos (TXT o DOCX)", type=["txt", "docx"])
archivo_pdf = st.file_uploader("2. PDF (Imágenes)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if archivo_txt and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            with st.spinner("Ejecutando Parser de alta precisión..."):
                raw_text = docx2txt.process(archivo_txt) if archivo_txt.name.endswith('.docx') \
                           else archivo_txt.read().decode("latin-1", errors="ignore")
                
                # Paso 1: Extracción de datos con lógica de código pura (no IA)
                datos = EcoParser.parsear_texto(raw_text)
                
                # Paso 2: Redacción con IA (solo para formato y estilo)
                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE.
                Escribe el informe médico basándote ESTRICTAMENTE en estos números:
                DDVI: {datos['ddvi']} mm | DSVI: {datos['dsvi']} mm | Septum: {datos['septum']} mm | Pared: {datos['pared']} mm.
                FEy: {datos['fey']} % | FA: {datos['fa']} %.
                
                Datos Paciente (busca Nombre y Edad aquí): {raw_text[:2000]}
                
                REGLAS:
                - Usa secciones I, II, III, IV.
                - Si FEy >= 55%: 'Función ventricular izquierda conservada'.
                - Si un dato dice 'No evaluado', aclara 'No se visualiza correctamente'.
                - NO digas 'no se proporcionan detalles'.
                """
                
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                final_text = chat.choices[0].message.content
                st.info(final_text)
                
                doc_bytes = generar_word_senior(final_text, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word", doc_bytes, f"Informe_{archivo_txt.name}.docx")
                
        except Exception as e:
            st.error(f"Error de sistema: {e}")
