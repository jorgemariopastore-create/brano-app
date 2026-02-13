
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de página
st.set_page_config(page_title="CardioReport AI Pro", layout="wide")
st.title("❤️ CardioReport AI - Generador de Informes Técnicos")

# --- MANEJO AUTOMÁTICO DE CLAVE (LOS "MISTERIOS") ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key (Manual):", type="password")

def limpiar_texto(t):
    return t.encode("ascii", "ignore").decode("ascii")

def generar_docx_profesional(texto_ia, imagenes):
    doc = Document()
    section = doc.sections[0]
    section.left_margin, section.right_margin = Inches(0.7), Inches(0.7)
    section.top_margin, section.bottom_margin = Inches(0.6), Inches(0.6)

    # Título Principal
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)

    lineas = texto_ia.split('\n')
    for i, linea in enumerate(lineas):
        linea = linea.replace('**', '').strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Detectar si es un encabezado de sección
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea.upper())
            run.bold, run.underline = True, True
            p.paragraph_format.space_before = Pt(12)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(4)

    # Anexo de imágenes
    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run('ANEXO: IMÁGENES DEL ESTUDIO').bold = True
        table = doc.add_table(rows=0, cols=2)
        for idx in range(0, len(imagenes), 2):
            row = table.add_row().cells
            for j in range(2):
                if idx + j < len(imagenes):
                    cp = row[j].paragraphs[0]
                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cp.add_run().add_picture(io.BytesIO(imagenes[idx+j]), width=Inches(2.45))
                    cp.add_run(f"\nFig. {idx + j + 1}")
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext, fotos = "", []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_ext += pag.get_text() + "\n"
                        for img in pag.get_images(full=True):
                            fotos.append(d.extract_image(img[0])["image"])
            else:
                fotos.append(a.read())

        if st.button("Generar Informe Médico Técnico"):
            with st.spinner("Analizando datos técnicos y redactando informe..."):
                texto_limpio = limpiar_texto(texto_ext)
                
                # PROMPT REFORZADO - ESTILO TÉCNICO MÉDICO
                prompt = f"""
                Eres un cardiólogo experto redactando un informe técnico. 
                Analiza estos datos de ecocardiograma: {texto_limpio}

                REGLAS DE ORO:
                1. Usa lenguaje MÉDICO TÉCNICO (abreviaturas como DDVI, DSVI, AI, FEy, VDF).
                2. NO uses frases genéricas o decorativas. Sé directo.
                3. PRIORIDAD DE DATOS: Si ves FEy de 30-31% o mención de 'Hipocinesia', repórtalo como Deterioro Severo. 
                4. NUNCA digas que la función es normal si los diámetros están aumentados o la FEy es baja.

                ESTRUCTURA DEL INFORME:
                DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
                I. EVALUACIÓN ANATÓMICA Y CAVIDADES: Diámetros (DDVI, DSVI), Aurícula Izquierda (volumen/diámetro), Masa cardíaca e Índice de Masa.
                II. FUNCIÓN VENTRICULAR IZQUIERDA: Fracción de Eyección (especificar técnica, ej. Simpson), Volúmenes (VDF, VSF), Motilidad parietal (ej. hipocinesia global).
                III. EVALUACIÓN HEMODINÁMICA (Doppler): Flujo transmitral (Onda E, A, relación E/A), Doppler Tisular (e'), Presiones de llenado.
                IV. HALLAZGOS EXTRACARDÍACOS: Vena Cava Inferior y colapso, hallazgos vasculares o renales.
                CONCLUSIÓN FINAL: Diagnóstico principal en una sola frase técnica en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0 # Temperatura 0 para que sea preciso y no invente
                )
                
                texto_final = res.choices[0].message.content
                st.markdown(texto_final)
                st.download_button("📥 DESCARGAR INFORME TÉCNICO", generar_docx_profesional(texto_final, fotos), "Informe_Cardiologico_Tecnico.docx")
