
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- 1. EXTRACCIÓN DE PDF (SOLO SI EL TEXTO ES LEGIBLE) ---
def extraer_datos_pdf(file):
    texto_completo = ""
    datos = {}
    if file is not None:
        try:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                texto_completo += page.extract_text()
            
            # Buscamos datos clave (mejorado para detectar mayúsculas/minúsculas)
            patrones = {
                "pac": r"Paciente[:\s]+(.*)",
                "peso": r"Peso[:\s]+(\d+)",
                "altura": r"Altura[:\s]+(\d+)",
                "ddvi": r"DDVI[:\s]+(\d+)",
                "siv": r"SIV[:\s]+(\d+)",
                "pp": r"PP[:\s]+(\d+)",
                "fa": r"FA[:\s]+(\d+)",
                "ai": r"AI[:\s]+(\d+)"
            }
            for clave, patron in patrones.items():
                match = re.search(patron, texto_completo, re.IGNORECASE)
                if match:
                    datos[clave] = match.group(1).strip()
        except:
            pass
    return datos

# --- 2. CÁLCULO SC ---
def calcular_sc_dubois(peso, altura):
    try:
        p = float(peso)
        a = float(altura)
        if p > 0 and a > 0:
            return 0.007184 * (p**0.425) * (a**0.725)
    except:
        pass
    return 0

# --- 3. GENERADOR DE WORD (ESTRUCTURA TÉCNICA CAPITULADA) ---
def generar_word(datos):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Bloque Paciente
    p_id = doc.add_paragraph()
    p_id.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p_id.add_run(f"FECHA: {datos['fecha']}\n")
    p_id.add_run(f"PESO: {datos['peso']} kg | ALTURA: {datos['altura']} cm | SC: {datos['sc']:.2f} m²")
    doc.add_paragraph("_" * 75)

    # CAPÍTULO I: ECOCARDIOGRAMA
    doc.add_paragraph("\nCAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL").bold = True
    t1 = doc.add_table(rows=3, cols=4)
    t1.style = 'Table Grid'
    mediciones = [
        ("DDVD", datos['ddvd']), ("DDVI", datos['ddvi']), ("DSVI", datos['dsvi']), ("FA/FEy", datos['fey']),
        ("ES", datos['es']), ("SIV", datos['siv']), ("PP", datos['pp']), ("DRAO", datos['drao']),
        ("AI", datos['ai']), ("AAO", datos['aao']), ("", ""), ("", "")
    ]
    idx = 0
    for r in range(3):
        for c in range(4):
            if idx < len(mediciones):
                t1.cell(r, c).text = f"{mediciones[idx][0]}: {mediciones[idx][1]} mm" if mediciones[idx][0] else ""
                idx += 1

    # CAPÍTULO II: DOPPLER
    doc.add_paragraph("\nCAPÍTULO II: ECO-DOPPLER HEMODINÁMICO").bold = True
    t2 = doc.add_table(rows=5, cols=4)
    t2.style = 'Table Grid'
    hd = ["Válvula", "Vel. cm/s", "Grad. P/M", "Insuf."]
    for i, h in enumerate(hd): t2.cell(0,i).text = h
    
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

    # CAPÍTULO III: CONCLUSIÓN
    doc.add_paragraph("\nCAPÍTULO III: CONCLUSIÓN").bold = True
    doc.add_paragraph(datos['conclusion']).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Firma
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.5))

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- 4. INTERFAZ DE CARGA (STREAMLIT) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Validación Médica")

archivo_pdf = st.file_uploader("Suba el PDF del estudio", type=["pdf"])
datos_ex = extraer_datos_pdf(archivo_pdf)

# FORMULARIO ÚNICO
with st.form("main_form"):
    st.subheader("📋 Datos del Paciente")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=datos_ex.get("pac", ""))
    fec = c2.date_input("Fecha", datetime.now())
    pes = c3.text_input("Peso (Kg)", value=datos_ex.get("peso", ""))
    alt = c4.text_input("Altura (cm)", value=datos_ex.get("altura", ""))

    st.divider()
    
    # SECCIÓN ECOCARDIOGRAMA (ORDEN DE TU PLANILLA)
    st.subheader("📏 Ecocardiograma")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd = e1.text_input("DDVD", value="")
    ddvi = e2.text_input("DDVI", value=datos_ex.get("ddvi", ""))
    dsvi = e3.text_input("DSVI", value="")
    fa = e4.text_input("FA (%)", value=datos_ex.get("fa", ""))
    es = e5.text_input("ES (mm)", value="")
    
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv = e1b.text_input("SIV", value=datos_ex.get("siv", ""))
    pp = e2b.text_input("PP", value=datos_ex.get("pp", ""))
    drao = e3b.text_input("DRAO", value="")
    ai = e4b.text_input("AI", value=datos_ex.get("ai", ""))
    aao = e5b.text_input("AAO", value="")

    st.divider()

    # SECCIÓN DOPPLER (ORDEN DE TU TABLA)
    st.subheader("🔊 Eco-Doppler")
    
    # Encabezados visuales
    h1, h2, h3, h4 = st.columns([2, 2, 2, 2])
    h1.markdown("**Válvula**")
    h2.markdown("**Velocidad cm/seg**")
    h3.markdown("**Gradiente (P/M)**")
    h4.markdown("**Insuficiencia**")

    # Filas Tricúspide -> Pulmonar -> Mitral -> Aórtica
    v_tri = h2.text_input("Tri_V", label_visibility="collapsed")
    g_tri = h3.text_input("Tri_G", label_visibility="collapsed")
    i_tri = h4.selectbox("Tri_I", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
    
    v_pul = h2.text_input("Pul_V", label_visibility="collapsed")
    g_pul = h3.text_input("Pul_G", label_visibility="collapsed")
    i_pul = h4.selectbox("Pul_I", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
    
    v_mit = h2.text_input("Mit_V", label_visibility="collapsed")
    g_mit = h3.text_input("Mit_G", label_visibility="collapsed")
    i_mit = h4.selectbox("Mit_I", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
    
    v_ao = h2.text_input("Ao_V", label_visibility="collapsed")
    g_ao = h3.text_input("Ao_G", label_visibility="collapsed")
    i_ao = h4.selectbox("Ao_I", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")

    st.divider()
    conclu = st.text_area("Conclusión", "Hallazgos dentro de límites normales.")
    
    # EL BOTÓN DE SUBMIT QUE FALTABA
    submitted = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

# Lógica fuera del formulario para la descarga
if submitted:
    sc_val = calcular_sc_dubois(pes, alt)
    dfinal = {
        "pac": pac, "fecha": fec.strftime("%d/%m/%Y"), "peso": pes, "altura": alt, "sc": sc_val,
        "ddvd": ddvd, "ddvi": ddvi, "dsvi": dsvi, "fey": fa, "es": es, "siv": siv, "pp": pp, "drao": drao, "ai": ai, "aao": aao,
        "v_tri": v_tri, "g_tri": g_tri, "i_tri": i_tri,
        "v_pul": v_pul, "g_pul": g_pul, "i_pul": i_pul,
        "v_mit": v_mit, "g_mit": g_mit, "i_mit": i_mit,
        "v_ao": v_ao, "g_ao": g_ao, "i_ao": i_ao,
        "conclusion": conclu
    }
    archivo = generar_word(dfinal)
    st.download_button("📥 Descargar Informe en Word", data=archivo, file_name=f"Informe_{pac}.docx")
