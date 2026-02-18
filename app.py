
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. LÓGICA DEL SABUESO (EXTRACCIÓN DE DATOS) ---

def sabueso_parser(texto_sucio, etiqueta):
    """
    Busca la etiqueta y captura el primer valor numérico real en un radio de 400 caracteres.
    Diseñado para saltar los '******' del SonoScape E3.
    """
    # Usamos re.escape para que caracteres como '(' no rompan el regex
    patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,400}}?value\s*=\s*([\d\.,]+)", re.I)
    match = patron.search(texto_sucio)
    
    if match:
        valor_str = match.group(1).replace(',', '.')
        try:
            valor = float(valor_str)
            # Filtros de rango médico para validación
            if "EF" in etiqueta.upper() or "FE" in etiqueta.upper() or "FS" in etiqueta.upper():
                if 10 <= valor <= 95: return f"{valor:.1f}"
            elif any(x in etiqueta.upper() for x in ["LVID", "DDVI", "DSVI"]):
                if 15 <= valor <= 85: return f"{valor:.1f}"
            elif any(x in etiqueta.upper() for x in ["IVS", "LVPW", "SEPTUM", "PARED"]):
                if 0.4 <= valor <= 30: return f"{valor:.1f}"
            else:
                return f"{valor:.1f}"
        except ValueError:
            pass
            
    return "No evaluado"

# --- 2. GENERADOR DE DOCUMENTO WORD ---

def generar_word(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)

    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Contenido filtrando textos innecesarios de la IA
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea or "proporcionan" in linea.lower(): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Firma
    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    # Procesamiento de Imágenes del PDF
    if pdf_bytes:
        doc.add_page_break()
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = []
        for page in pdf:
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                base_image = pdf.extract_image(xref)
                imgs.append(base_image["image"])
        
        if imgs:
            doc.add_paragraph("ANEXO DE IMÁGENES").alignment = WD_ALIGN_PARAGRAPH.CENTER
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, img_data in enumerate(imgs):
                cell_p = tabla.cell(i//2, i%2).paragraphs[0]
                cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell_p.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ DE USUARIO (STREAMLIT) ---

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ CardioReport Pro: Dr. Pastore")
st.markdown("---")

u_txt = st.file_uploader("1. Subir Reporte de Texto (TXT)", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Capturas", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and api_key:
    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            with st.spinner("El Sabueso está rastreando los datos..."):
                contenido = u_txt.read().decode("latin-1", errors="ignore")
                
                # EJECUCIÓN DEL SABUESO CON LAS ETIQUETAS DEL SONOSCAPE E3
                datos = {
                    "ddvi": sabueso_parser(contenido, "LVID d"),
                    "dsvi": sabueso_parser(contenido, "LVID s"),
                    "sep":  sabueso_parser(contenido, "IVS d"),
                    "par":  sabueso_parser(contenido, "LVPW d"),
                    "fey":  sabueso_parser(contenido, "EF"),
                    "fa":   sabueso_parser(contenido, "FS")
                }

                # LLAMADA A GROQ
                client = Groq(api_key=api_key)
                prompt = f"""
                ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE.
                Redacta el informe para el paciente: ALICIA ALBORNOZ (o el nombre que figure en el texto).
                
                DATOS TÉCNICOS EXTRAÍDOS (USAR ESTOS VALORES):
                - DDVI: {datos['ddvi']} mm
                - DSVI: {datos['dsvi']} mm
                - Septum: {datos['sep']} mm
                - Pared: {datos['par']} mm
                - FEy: {datos['fey']} %
                - FA: {datos['fa']} %
                
                TEXTO COMPLETO PARA ANTECEDENTES: {contenido[:2000]}
                
                ESTRUCTURA OBLIGATORIA:
                DATOS DEL PACIENTE
                I. EVALUACIÓN ANATÓMICA
                II. FUNCIÓN VENTRICULAR (Si FEy < 55%: indicar disfunción)
                III. EVALUACIÓN HEMODINÁMICA (Sin particularidades si no hay datos)
                IV. CONCLUSIÓN
                """
                
                chat_completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado_texto = chat_completion.choices[0].message.content
                st.success("¡Informe redactado con éxito!")
                st.info(resultado_texto)
                
                # Botón de Descarga
                doc_bytes = generar_word(resultado_texto, u_pdf.getvalue())
                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=doc_bytes,
                    file_name=f"Informe_Ecocardiograma_{u_txt.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
        except Exception as e:
            st.error(f"Se produjo un error en el sistema: {e}")
