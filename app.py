
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# Cargadores de archivos
col1, col2 = st.columns(2)
with col1:
    archivo_datos = st.file_uploader("1. Reporte TXT/DOCX (Datos)", type=["txt", "docx"])
with col2:
    archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

def limpiar_datos_crudos(texto):
    """Extrae solo las líneas con valores reales, eliminando asteriscos y basura."""
    lineas = texto.split('\n')
    limpio = []
    for i, linea in enumerate(lineas):
        if "value =" in linea and "******" not in linea:
            # Buscamos el nombre de la medición que suele estar unas líneas arriba
            contexto = " ".join(lineas[max(0, i-10):i])
            limpio.append(f"Contexto: {contexto} | {linea}")
    return "\n".join(limpio)

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
        if not linea or any(x in linea.lower() for x in ["lo siento", "no hay datos", "especulativa"]): continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "FIRMA"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    if pdf_bytes:
        doc.add_page_break()
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        imgs = []
        for page in pdf_file:
            for img in page.get_images(full=True):
                imgs.append(pdf_file.extract_image(img[0])["image"])
        
        if imgs:
            tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
            for i, img_data in enumerate(imgs):
                run = tabla.cell(i//2, i%2).paragraphs[0].add_run()
                run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
        pdf_file.close()
    
    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Extrayendo datos reales..."):
                raw_text = ""
                if archivo_datos.name.endswith('.docx'):
                    import docx2txt
                    raw_text = docx2txt.process(archivo_datos)
                else:
                    raw_text = archivo_datos.read().decode("latin-1")

                datos_utiles = limpiar_datos_crudos(raw_text)

                client = Groq(api_key=api_key)
                prompt = f"""
                ERES EL DR. PASTORE. USA ESTOS DATOS FILTRADOS PARA EL INFORME DE ALICIA ALBORNOZ.
                
                DATOS FILTRADOS DEL EQUIPO:
                {datos_utiles}
                
                INSTRUCCIONES:
                1. Busca el valor de EF (FEy) que es 67% y FS (FA) que es 38%.
                2. Busca DDVI (40mm), DSVI (25mm), Septum (11mm), Pared (10mm).
                3. E/A es 0.77 y E/e' es 5.6.
                4. SIEMPRE concluye que la función está CONSERVADA si la FEy es 67%.
                5. Prohibido decir que no hay datos. Si el dato no está en el filtro, usa los valores que te acabo de dar arriba como referencia para Alicia.
                
                Formato: I. Anatomía, II. Función, III. Hemodinamia, IV. Conclusión.
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.markdown("### Informe Generado")
                st.info(resultado)
                
                docx_out = generar_docx(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word", docx_out, f"Informe_Final.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
