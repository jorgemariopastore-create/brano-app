
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
from datetime import datetime

# --- 1. LÓGICA DE CÁLCULO MÉDICO ---
def calcular_sc_dubois(peso, altura):
    if peso > 0 and altura > 0:
        return 0.007184 * (peso**0.425) * (altura**0.725)
    return 0

def calcular_masa_vi(ddvi, siv, pp):
    try:
        ddvi_cm, siv_cm, pp_cm = float(ddvi)/10, float(siv)/10, float(pp)/10
        masa = 0.8 * 1.04 * ((ddvi_cm + siv_cm + pp_cm)**3 - (ddvi_cm)**3) + 0.6
        return round(masa, 1)
    except:
        return 0

# --- 2. GENERADOR DE WORD PROFESIONAL ---
def generar_word(datos):
    doc = Document()
    
    # Estilo base Arial 11
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # 1. IDENTIFICACIÓN DEL PACIENTE
    p_paciente = doc.add_paragraph()
    p_paciente.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p_paciente.add_run(f"FECHA: {datos['fecha']}\n")
    p_paciente.add_run(f"PESO: {datos['peso']} kg | ALTURA: {datos['altura']} cm | SC: {datos['sc']:.2f} m²")
    doc.add_paragraph("_" * 75)

    # CAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL
    doc.add_paragraph("\nCAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL").bold = True
    tabla_i = doc.add_table(rows=2, cols=3)
    tabla_i.cell(0,0).text = f"DDVI: {datos['ddvi']} mm"
    tabla_i.cell(0,1).text = f"SIV: {datos['siv']} mm"
    tabla_i.cell(0,2).text = f"PP: {datos['pp']} mm"
    tabla_i.cell(1,0).text = f"FEy: {datos['fey']}%"
    tabla_i.cell(1,1).text = f"AI: {datos['ai']} mm"
    tabla_i.cell(1,2).text = f"Masa VI: {datos['masa']} gr"

    # CAPÍTULO II: ECO-DOPPLER HEMODINÁMICO
    doc.add_paragraph("\nCAPÍTULO II: ECO-DOPPLER HEMODINÁMICO").bold = True
    tabla_ii = doc.add_table(rows=5, cols=4)
    # Encabezados
    hd = ["Válvula", "Vel. Máx (m/s)", "Grad. Pico/Med", "Insuficiencia"]
    for i, texto in enumerate(hd):
        tabla_ii.cell(0,i).text = texto
    
    valvulas = [
        ("Aórtica", datos['v_ao'], datos['g_ao'], datos['i_ao']),
        ("Pulmonar", datos['v_pul'], datos['g_pul'], datos['i_pul']),
        ("Mitral", datos['v_mit'], datos['g_mit'], datos['i_mit']),
        ("Tricúspide", datos['v_tri'], datos['g_tri'], datos['i_tri'])
    ]
    
    for i, (nom, vel, grad, insuf) in enumerate(valvulas, start=1):
        tabla_ii.cell(i,0).text = nom
        tabla_ii.cell(i,1).text = vel
        tabla_ii.cell(i,2).text = grad
        tabla_ii.cell(i,3).text = insuf

    # CAPÍTULO III: CONCLUSIÓN Y FIRMA
    doc.add_paragraph("\nCAPÍTULO III: CONCLUSIÓN").bold = True
    p_conclu = doc.add_paragraph(datos['conclusion'])
    p_conclu.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Cierre con Firma Digital
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144 - MÉDICO CARDIÓLOGO")
    
    ruta_firma = "firma_doctor.png"
    if os.path.exists(ruta_firma):
        doc.add_picture(ruta_firma, width=Inches(1.5))

    # ANEXO DE IMÁGENES
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
    grid = doc.add_table(rows=4, cols=2)
    grid.style = 'Table Grid'
    for row in grid.rows:
        for cell in row.cells:
            cell.paragraphs[0].add_run("\n\n\n\n\n")

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- 3. INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 CardioReport Pro")

# Carga de PDF (Única fuente)
pdf_file = st.file_uploader("Subir Informe PDF del Equipo", type=["pdf"])

with st.form("validador_datos"):
    st.subheader("📋 Validación de Datos del Paciente")
    
    col1, col2 = st.columns(2)
    paciente = col1.text_input("Nombre del Paciente", value="")
    fecha = col2.date_input("Fecha del estudio", datetime.now())
    
    c1, c2, c3 = st.columns(3)
    peso = c1.number_input("Peso (kg)", min_value=0.0, step=0.1)
    alt = c2.number_input("Altura (cm)", min_value=0)
    sc = calcular_sc_dubois(peso, alt)
    c3.metric("SC Calculada", f"{sc:.2f} m²")

    st.divider()

    # CAPÍTULO I
    st.subheader("Capítulo I: Ecocardiograma Estructural")
    ci1, ci2, ci3 = st.columns(3)
    ddvi = ci1.text_input("DDVI (mm)", value="")
    siv = ci2.text_input("SIV (mm)", value="")
    pp = ci3.text_input("PP (mm)", value="")
    fey = ci1.text_input("FEy (%)", value="")
    ai = ci2.text_input("AI (mm)", value="")
    
    # Cálculo de masa en tiempo real si hay datos
    m_calc = calcular_masa_vi(ddvi if ddvi else 0, siv if siv else 0, pp if pp else 0)
    masa = ci3.text_input("Masa VI (gr)", value=str(m_calc) if m_calc > 0 else "")

    # CAPÍTULO II (Campos en blanco por seguridad)
    st.subheader("Capítulo II: Eco-Doppler Hemodinámico")
    st.info("Complete las velocidades y gradientes observados.")
    
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    # Aórtica
    v_ao = col_v1.text_input("V. Aórtica (m/s)", "")
    g_ao = col_v1.text_input("Grad. Ao (P/M)", "")
    i_ao = col_v1.selectbox("Insuf. Ao", ["Ausente", "Leve", "Mod.", "Severa"])
    # Pulmonar
    v_pul = col_v2.text_input("V. Pulmonar (m/s)", "")
    g_pul = col_v2.text_input("Grad. Pul (P/M)", "")
    i_pul = col_v2.selectbox("Insuf. Pul", ["Ausente", "Leve", "Mod.", "Severa"])
    # Mitral
    v_mit = col_v3.text_input("V. Mitral (m/s)", "")
    g_mit = col_v3.text_input("Grad. Mit (P/M)", "")
    i_mit = col_v3.selectbox("Insuf. Mit", ["Ausente", "Leve", "Mod.", "Severa"])
    # Tricúspide
    v_tri = col_v4.text_input("V. Tricúspide (m/s)", "")
    g_tri = col_v4.text_input("Grad. Tri (P/M)", "")
    i_tri = col_v4.selectbox("Insuf. Tri", ["Ausente", "Leve", "Mod.", "Severa"])

    # CAPÍTULO III
    st.subheader("Capítulo III: Conclusión")
    conclu = st.text_area("Diagnóstico Final", "Ecocardiograma Doppler dentro de parámetros normales.")

    # BOTÓN GENERAR
    boton_generar = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

if boton_generar:
    if not paciente:
        st.error("Por favor, ingrese el nombre del paciente.")
    else:
        datos_finales = {
            "pac": paciente.upper(), "fecha": fecha.strftime("%d/%m/%Y"),
            "peso": peso, "altura": alt, "sc": sc,
            "ddvi": ddvi, "siv": siv, "pp": pp, "fey": fey, "ai": ai, "masa": masa,
            "v_ao": v_ao, "g_ao": g_ao, "i_ao": i_ao,
            "v_pul": v_pul, "g_pul": g_pul, "i_pul": i_pul,
            "v_mit": v_mit, "g_mit": g_mit, "i_mit": i_mit,
            "v_tri": v_tri, "g_tri": g_tri, "i_tri": i_tri,
            "conclusion": conclu
        }
        
        doc_word = generar_word(datos_finales)
        st.success("✅ Informe generado correctamente.")
        st.download_button(
            label="📥 Descargar Informe Word",
            data=doc_word,
            file_name=f"Informe_{paciente.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
