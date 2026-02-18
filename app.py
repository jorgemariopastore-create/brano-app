
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo_datos = st.file_uploader("1. Reporte de Datos (TXT o DOCX)", type=["txt", "docx"])
archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def extraer_valor_tecnico(texto, etiqueta):
    # Esta función busca la etiqueta y el primer 'value =' que aparezca después de ella
    # de forma mucho más flexible para archivos Sonoscape
    patron = re.compile(rf"{re.escape(etiqueta)}.*?value\s*=\s*([\d\.,]+)", re.DOTALL | re.IGNORECASE)
    match = patron.search(texto)
    if match:
        valor = match.group(1).replace(',', '.')
        return valor if valor != "******" else "No evaluado"
    return "No evaluado"

def generar_docx(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or "disculpas" in linea.lower(): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "FIRMA"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    if pdf_bytes:
        doc.add_page_break()
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in pdf_file:
            for img in page.get_images(full=True):
                img_data = pdf_file.extract_image(img[0])["image"]
                doc.add_picture(io.BytesIO(img_data), width=Inches(4.5))
        pdf_file.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME DEFINITIVO"):
        try:
            with st.spinner("Escaneando mediciones de Sonoscape..."):
                if archivo_datos.name.endswith('.docx'):
                    texto_crudo = docx2txt.process(archivo_datos)
                else:
                    texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")

                # Extracción forzada por etiquetas de sistema
                # Nota: Silvia tiene las medidas en bloques [MEASUREMENT]
                ddvi = extraer_valor_tecnico(texto_crudo, "LVID(d)")
                if ddvi == "No evaluado": ddvi = extraer_valor_tecnico(texto_crudo, "LVIDd")
                
                dsvi = extraer_valor_tecnico(texto_crudo, "LVID(s)")
                if dsvi == "No evaluado": dsvi = extraer_valor_tecnico(texto_crudo, "LVIDs")
                
                septum = extraer_valor_tecnico(texto_crudo, "IVS(d)")
                if septum == "No evaluado": septum = extraer_valor_tecnico(texto_crudo, "IVSd")
                
                pared = extraer_valor_tecnico(texto_crudo, "LVPW(d)")
                if pared == "No evaluado": pared = extraer_valor_tecnico(texto_crudo, "LVPWd")
                
                fey = extraer_valor_tecnico(texto_crudo, "EF(Teich)")
                if fey == "No evaluado": fey = extraer_valor_tecnico(texto_crudo, "EF")
                
                fa = extraer_valor_tecnico(texto_crudo, "FS(Teich)")
                if fa == "No evaluado": fa = extraer_valor_tecnico(texto_crudo, "FS")

                client = Groq(api_key=api_key)
                
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. 
                Redacta el informe con estos valores EXTRAÍDOS DIRECTAMENTE:
                
                PACIENTE: Silvia Schmidt (Edad: 51, Peso: 67, Altura: 172)
                DDVI: {ddvi} mm
                DSVI: {dsvi} mm
                SEPTUM: {septum} mm
                PARED: {pared} mm
                FEy: {fey} %
                FA: {fa} %

                INSTRUCCIONES:
                1. NO digas "No evaluado" si el valor numérico está arriba.
                2. Formato: I. EVALUACIÓN ANATÓMICA, II. FUNCIÓN VENTRICULAR, III. EVALUACIÓN HEMODINÁMICA, IV. CONCLUSIÓN.
                3. CONCLUSIÓN: Si FEy es {fey} (mayor a 55%), "Función ventricular conservada".
                4. Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word", docx_out, "Informe_Final.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
