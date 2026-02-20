
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- 1. LÓGICA DE EXTRACCIÓN DE PDF (DATOS SEGUROS) ---
def extraer_datos_pdf(file):
    texto_completo = ""
    datos = {}
    try:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            texto_completo += page.extract_text()
        
        # Patrones de búsqueda (Ejemplos de extracción segura)
        patrones = {
            "pac": r"Paciente:\s*(.*)",
            "peso": r"Peso:\s*(\d+\.?\d*)",
            "altura": r"Altura:\s*(\d+)",
            "ddvi": r"DDVI:\s*(\d+)",
            "siv": r"DDSIV:\s*(\d+)",
            "pp": r"DDPP:\s*(\d+)",
            "fey": r"FA:\s*(\d+)",
            "ai": r"DDAI:\s*(\d+)"
        }
        
        for clave, patron in patrones.items():
            match = re.search(patron, texto_completo, re.IGNORECASE)
            if match:
                datos[clave] = match.group(1).strip()
    except:
        pass
    return datos

# --- 2. CÁLCULOS ---
def calcular_sc_dubois(peso, altura):
    if peso > 0 and altura > 0:
        return 0.007184 * (float(peso)**0.425) * (float(altura)**0.725)
    return 0

# --- 3. GENERADOR DE WORD (ESTRUCTURA PROFESIONAL POR CAPÍTULOS) ---
def generar_word(datos):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Identificación
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p.add_run(f"FECHA: {datos['fecha']}\n")
    p.add_run(f"PESO: {datos['peso']} kg | ALTURA: {datos['altura']} cm | SC: {datos['sc']:.2f} m²")
    doc.add_paragraph("_" * 75)

    # CAPÍTULO I: ECOCARDIOGRAMA
    doc.add_paragraph("\nCAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL").bold = True
    # (Aquí se agrupan los datos de tu planilla excel en una tabla profesional)
    t1 = doc.add_table(rows=4, cols=3)
    t1.cell(0,0).text = f"DDVD: {datos['ddvd']} mm"
    t1.cell(0,1).text = f"DDVI: {datos['ddvi']} mm"
    t1.cell(0,2).text = f"DSVI: {datos['dsvi']} mm"
    t1.cell(1,0).text = f"SIV: {datos['siv']} mm"
    t1.cell(1,1).text = f"PP: {datos['pp']} mm"
    t1.cell(1,2).text = f"FEy/FA: {datos['fey']}%"
    t1.cell(2,0).text = f"AI: {datos['ai']} mm"
    t1.cell(2,1).text = f"AO: {datos['drao']} mm"
    t1.cell(2,2).text = f"ES: {datos['es']} mm"

    # CAPÍTULO II: ECO-DOPPLER
    doc.add_paragraph("\nCAPÍTULO II: ECO-DOPPLER HEMODINÁMICO").bold = True
    t2 = doc.add_table(rows=5, cols=4)
    cols = ["Válvula", "Vel. (cm/s)", "Grad. (P/M)", "Insuficiencia"]
    for i, h in enumerate(cols): t2.cell(0,i).text = h
    
    valvs = [
        ("Tricúspide", datos['v_tri'], datos['g_tri'], datos['i_tri']),
        ("Pulmonar", datos['v_pul'], datos['g_pul'], datos['i_pul']),
        ("Mitral", datos['v_mit'], datos['g_mit'], datos['i_mit']),
        ("Aórtica", datos['v_ao'], datos['g_ao'], datos['i_ao'])
    ]
    for i, (n, v, g, ins) in enumerate(valvs, start=1):
        t2.cell(i,0).text = n
        t2.cell(i,1).text = v
        t2.cell(i,2).text = g
        t2.cell(i,3).text = ins

    # CAPÍTULO III: CONCLUSIÓN Y FIRMA
    doc.add_paragraph("\nCAPÍTULO III: CONCLUSIÓN").bold = True
    doc.add_paragraph(datos['conclusion']).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.5))

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- 4. INTERFAZ STREAMLIT (ORDEN SEGÚN TUS ARCHIVOS) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Validación de Datos Médicos")

archivo_pdf = st.file_uploader("1. Levante el PDF aquí", type=["pdf"])
datos_extraidos = extraer_datos_pdf(archivo_pdf) if archivo_pdf else {}

with st.form("form_medico"):
    st.subheader("📋 Datos del Paciente")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=datos_extraidos.get("pac", ""))
    fec = c2.date_input("Fecha", datetime.now())
    pes = c3.text_input("Peso (Kg)", value=datos_extraidos.get("peso", ""))
    alt = c4.text_input("Altura (cm)", value=datos_extraidos.get("altura", ""))

    st.divider()
    
    # SECCIÓN ECOCARDIOGRAMA (ORDEN DE TU EXCEL)
    st.subheader("📏 Ecocardiograma (Orden según planilla)")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd = e1.text_input("DDVD", value="")
    ddvi = e2.text_input("DDVI", value=datos_extraidos.get("ddvi", ""))
    dsvi = e3.text_input("DSVI", value="")
    fa = e4.text_input("FA (%)", value=datos_extraidos.get("fey", ""))
    es = e5.text_input("ES (mm)", value="")
    
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv = e1b.text_input("DDSIV", value=datos_extraidos.get("siv", ""))
    pp = e2b.text_input("DDPP", value=datos_extraidos.get("pp", ""))
    drao = e3b.text_input("DRAO", value="")
    ai = e4b.text_input("DDAI", value=datos_extraidos.get("ai", ""))
    aao = e5b.text_input("AAO", value="")

    st.divider()

    # SECCIÓN DOPPLER (ORDEN DE TU DOCX)
    st.subheader("🔊 Eco-Doppler (Orden según planilla)")
    
    # Creamos las filas tal cual tu tabla de Word
    d1, d2, d3, d4 = st.columns([2, 2, 2, 2])
    d1.label("Válvula")
    d2.label("Velocidad cm/seg")
    d3.label("Gradiente (P/M)")
    d4.label("Insuficiencia")

    # Fila Tricúspide
    v_tri = d2.text_input("Tri", label_visibility="collapsed")
    g_tri = d3.text_input("G-Tri", label_visibility="collapsed")
    i_tri = d4.selectbox("I-Tri", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    # Fila Pulmonar
    v_pul = d2.text_input("Pul", label_visibility="collapsed")
    g_pul = d3.text_input("G-Pul", label_visibility="collapsed")
    i_pul = d4.selectbox("I-Pul", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    # Fila Mitral
    v_mit = d2.text_input("Mit", label_visibility="collapsed")
    g_mit = d3.text_input("G-Mit", label_visibility="collapsed")
    i_mit = d4.selectbox("I-Mit", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    # Fila Aórtica
    v_ao = d2.text_input("Ao", label_visibility="collapsed")
    g_ao = d3.text_input("G-Ao", label_visibility="collapsed")
    i_ao = d4.selectbox("I-Ao", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    st.divider()
    conclu = st.text_area("Conclusión", "Hallazgos dentro de límites normales.")
    
    generar = st.form_submit_button("🚀 GENERAR INFORME CAPITULADO")

if generar:
    sc = calcular_sc_dubois(pes if pes else 0, alt if alt else 0)
    datos_finales = {
        "pac": pac, "fecha": fec.strftime("%d/%m/%Y"), "peso": pes, "altura": alt, "sc": sc,
        "ddvd": ddvd, "ddvi": ddvi, "dsvi": dsvi, "fey": fa, "es": es, "siv": siv, "pp": pp, "drao": drao, "ai": ai, "aao": aao,
        "v_tri": v_tri, "g_tri": g_tri, "i_tri": i_tri,
        "v_pul": v_pul, "g_pul": g_pul, "i_pul": i_pul,
        "v_mit": v_mit, "g_mit": g_mit, "i_mit": i_mit,
        "v_ao": v_ao, "g_ao": g_ao, "i_ao": i_ao,
        "conclusion": conclu
    }
    doc_res = generar_word(datos_finales)
    st.download_button("📥 Descargar Word", data=doc_res, file_name=f"Informe_{pac}.docx")
