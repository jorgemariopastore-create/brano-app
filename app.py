
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- PARSER DE GRADO INDUSTRIAL ---

class SonoscapeParser:
    @staticmethod
    def extraer_datos(texto):
        # Mapeo de etiquetas técnicas del TXT de Alicia a nombres internos
        mapeo = {
            'LVID(d)': 'ddvi', 'LVIDd': 'ddvi', 'DDVI': 'ddvi',
            'LVID(s)': 'dsvi', 'LVIDs': 'dsvi', 'DSVI': 'dsvi',
            'IVS(d)': 'septum', 'IVSd': 'septum', 'DDSIV': 'septum',
            'LVPW(d)': 'pared', 'LVPWd': 'pared', 'DDPP': 'pared',
            'EF(Teich)': 'fey', 'EF': 'fey', 'LVEF': 'fey',
            'FS(Teich)': 'fa', 'FS': 'fa', 'FA': 'fa'
        }
        
        resultados = {k: "No evaluado" for k in ['ddvi', 'dsvi', 'septum', 'pared', 'fey', 'fa']}
        
        # Dividimos el archivo en los bloques [MEASUREMENT] que vimos en el TXT de Alicia
        bloques = texto.split('[MEASUREMENT]')
        
        for bloque in bloques:
            match_item = re.search(r'item\s*=\s*([^\r\n]+)', bloque, re.I)
            match_val = re.search(r'value\s*=\s*([\d\.,]+)', bloque, re.I)
            
            if match_item and match_val:
                item_nombre = match_item.group(1).strip()
                valor_str = match_val.group(1).replace(',', '.')
                
                # Verificamos si este ítem nos interesa
                for clave_tec, clave_interna in mapeo.items():
                    if clave_tec.lower() == item_nombre.lower():
                        try:
                            val_f = float(valor_str)
                            # Solo guardamos si el valor es lógicamente posible (filtro médico)
                            if (clave_interna in ['fey', 'fa'] and 10 < val_f < 95) or \
                               (clave_interna not in ['fey', 'fa'] and 0.5 < val_f < 85):
                                resultados[clave_interna] = f"{val_f:.1f}"
                        except ValueError:
                            continue
        return resultados

# --- GENERADOR DE WORD ---

def crear_informe_word(texto_ia, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)

    # Título
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Contenido
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea or "proporcionan" in linea.lower(): continue
        para = doc.add_paragraph()
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            para.add_run(linea.replace("**", "")).bold = True
        else:
            para.add_run(linea.replace("**", ""))

    # Firma
    doc.add_paragraph("\n")
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True

    # Imágenes
    if pdf_bytes:
        doc.add_page_break()
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
        if imgs:
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, img_data in enumerate(imgs):
                run = tabla.cell(i//2, i%2).paragraphs[0].add_run()
                run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf.close()

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- APP ---

st.set_page_config(page_title="CardioReport Pro Senior", layout="centered")
st.title("❤️ Generador de Informes Médicos")

u_txt = st.file_uploader("1. TXT de Datos", type=["txt"])
u_pdf = st.file_uploader("2. PDF de Imágenes", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY")

if u_txt and u_pdf and key:
    if st.button("🚀 GENERAR INFORME FINAL"):
        try:
            content = u_txt.read().decode("latin-1", errors="ignore")
            datos = SonoscapeParser.extraer_datos(content)
            
            # Extraer BSA y Datos Personales del bloque [PATINET INFO]
            bsa_match = re.search(r'BSA\s*=\s*([\d\.]+)', content)
            bsa = bsa_match.group(1) if bsa_match else "No calculado"
            
            client = Groq(api_key=key)
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE.
            Redacta el informe para ALICIA ALBORNOZ usando estos valores:
            DDVI: {datos['ddvi']} mm, DSVI: {datos['dsvi']} mm, Septum: {datos['septum']} mm, Pared: {datos['pared']} mm.
            FEy: {datos['fey']} %, FA: {datos['fa']} %, BSA: {bsa}.
            
            Usa el texto para nombre y edad: {content[:1000]}
            
            ESTRUCTURA: DATOS PACIENTE, I. ANATÓMICA, II. FUNCIÓN, III. HEMODINÁMICA (Sin particularidades), IV. CONCLUSIÓN.
            REGLA: Si FEy >= 55%: 'Función ventricular izquierda conservada'.
            """
            
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
            informe = res.choices[0].message.content
            st.info(informe)
            
            st.download_button("📥 Descargar Word", crear_informe_word(informe, u_pdf.getvalue()), "Informe.docx")
        except Exception as e:
            st.error(f"Error: {e}")
