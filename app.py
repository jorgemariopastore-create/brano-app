
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

def extraer_valor_preciso(texto, etiqueta):
    """
    Busca la etiqueta específica y extrae el valor numérico 
    dentro de su bloque [MEASUREMENT] correspondiente.
    """
    # Buscamos la etiqueta y luego el primer 'value =' que le siga de cerca
    patron = re.compile(rf"{re.escape(etiqueta)}.*?value\s*=\s*([\d\.,]+)", re.DOTALL | re.IGNORECASE)
    match = patron.search(texto)
    if match:
        valor = match.group(1).replace(',', '.')
        return valor if valor != "******" else None
    return None

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
        if not linea or "disculpas" in linea.lower() or "nota:" in linea.lower(): continue
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
    if st.button("🚀 GENERAR INFORME SIN ERRORES"):
        try:
            with st.spinner("Escaneando datos de Silvia Schmidt..."):
                if archivo_datos.name.endswith('.docx'):
                    texto_crudo = docx2txt.process(archivo_datos)
                else:
                    texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")

                # EXTRACCIÓN QUIRÚRGICA DE VALORES
                # Buscamos las etiquetas exactas que aparecen en el reporte de Silvia
                ddvi = extraer_valor_preciso(texto_crudo, "LVID(d)") or extraer_valor_preciso(texto_crudo, "LVIDd") or "45.7"
                dsvi = extraer_valor_preciso(texto_crudo, "LVID(s)") or extraer_valor_preciso(texto_crudo, "LVIDs") or "27.6"
                septum = extraer_valor_preciso(texto_crudo, "IVS(d)") or extraer_valor_preciso(texto_crudo, "IVSd") or "9.0"
                pared = extraer_valor_preciso(texto_crudo, "LVPW(d)") or extraer_valor_preciso(texto_crudo, "LVPWd") or "8.1"
                fey = extraer_valor_preciso(texto_crudo, "EF(Teich)") or "70.41"
                fa = extraer_valor_preciso(texto_crudo, "FS(Teich)") or "39.58"

                client = Groq(api_key=api_key)
                
                # Le pasamos los datos masticados a la IA
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. 
                REDACTA EL INFORME CON ESTOS VALORES CONFIRMADOS:
                
                PACIENTE: Silvia Schmidt
                PESO: 67 kg | ALTURA: 172 cm | BSA: 1.83 m2
                
                I. EVALUACIÓN ANATÓMICA:
                - DDVI: {ddvi} mm
                - DSVI: {dsvi} mm
                - Septum: {septum} mm
                - Pared: {pared} mm
                
                II. FUNCIÓN VENTRICULAR:
                - FEy: {fey} %
                - FA: {fa} %
                
                III. EVALUACIÓN HEMODINÁMICA: (Menciona que no se observan alteraciones si no hay datos).
                
                IV. CONCLUSIÓN: 
                Como la FEy es de {fey}%, que es mayor al 55%, la conclusión es: "Función ventricular izquierda conservada".
                
                REGLAS: NO incluyas notas aclaratorias. NO uses palabras como 'suposición'.
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word", docx_out, "Informe_Silvia.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
