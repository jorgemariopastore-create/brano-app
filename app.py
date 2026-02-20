
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- FUNCIONES DE APOYO ---
def extraer_datos_seguros(file):
    """Extrae solo lo básico si es legible, sino devuelve vacío."""
    datos = {}
    if file:
        try:
            reader = PyPDF2.PdfReader(file)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()
            
            # Buscamos solo lo que suele ser estándar en los PDF de equipos
            pac_match = re.search(r"Paciente[:\s]+(.*)", texto, re.IGNORECASE)
            if pac_match: datos["pac"] = pac_match.group(1).strip()
            
            peso_match = re.search(r"Peso[:\s]+(\d+)", texto, re.IGNORECASE)
            if peso_match: datos["peso"] = peso_match.group(1).strip()
        except:
            pass
    return datos

def generar_word(datos):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Identificación del Paciente
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p.add_run(f"FECHA: {datos['fec']}\n")
    p.add_run(f"PESO: {datos['peso']} kg | ALTURA: {datos['alt']} cm")
    doc.add_paragraph("_" * 75)

    # CAPÍTULO I: ECOCARDIOGRAMA (Solo para el Word)
    doc.add_paragraph("\nCAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL").bold = True
    t1 = doc.add_table(rows=2, cols=5)
    t1.style = 'Table Grid'
    # Fila 1
    t1.cell(0,0).text = f"DDVD: {datos['ddvd']}"
    t1.cell(0,1).text = f"DDVI: {datos['ddvi']}"
    t1.cell(0,2).text = f"DSVI: {datos['dsvi']}"
    t1.cell(0,3).text = f"FA: {datos['fa']}%"
    t1.cell(0,4).text = f"ES: {datos['es']}"
    # Fila 2
    t1.cell(1,0).text = f"SIV: {datos['siv']}"
    t1.cell(1,1).text = f"PP: {datos['pp']}"
    t1.cell(1,2).text = f"DRAO: {datos['drao']}"
    t1.cell(1,3).text = f"AI: {datos['ai']}"
    t1.cell(1,4).text = f"AAO: {datos['aao']}"

    # CAPÍTULO II: DOPPLER (Solo para el Word)
    doc.add_paragraph("\nCAPÍTULO II: ECO-DOPPLER HEMODINÁMICO").bold = True
    t2 = doc.add_table(rows=5, cols=4)
    t2.style = 'Table Grid'
    encabezados = ["Válvula", "Velocidad (cm/s)", "Gradiente", "Insuf."]
    for i, nombre in enumerate(encabezados):
        t2.cell(0,i).text = nombre
    
    valvulas = [
        ("Tricúspide", datos['v_tri'], datos['g_tri'], datos['i_tri']),
        ("Pulmonar", datos['v_pul'], datos['g_pul'], datos['i_pul']),
        ("Mitral", datos['v_mit'], datos['g_mit'], datos['i_mit']),
        ("Aórtica", datos['v_ao'], datos['g_ao'], datos['i_ao'])
    ]
    for i, (n, v, g, ins) in enumerate(valvulas, start=1):
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

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Sistema de Validación de Informes")

# 1. Carga de archivo
pdf_subido = st.file_uploader("Subir PDF del Equipo", type=["pdf"])
datos_auto = extraer_datos_seguros(pdf_subido)

# 2. Formulario de Validación (Siguiendo el orden de tus archivos)
with st.form("formulario_principal"):
    st.subheader("📋 Datos del Paciente")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=datos_auto.get("pac", ""))
    fec = c2.date_input("Fecha", datetime.now())
    peso = c3.text_input("Peso (Kg)", value=datos_auto.get("peso", ""))
    alt = c4.text_input("Altura (cm)", value="")

    st.markdown("---")
    
    # SECCIÓN ECOCARDIOGRAMA (ORDEN EXACTO DE TU EXCEL)
    st.subheader("📏 Ecocardiograma (Carga Estructural)")
    e1, e2, e3, e4, e5 = st.columns(5)
    f1_ddvd = e1.text_input("DDVD", help="Referencia 22-43 mm")
    f1_ddvi = e2.text_input("DDVI")
    f1_dsvi = e3.text_input("DSVI")
    f1_fa = e4.text_input("FA (%)")
    f1_es = e5.text_input("ES (mm)")

    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    f2_siv = e1b.text_input("SIV")
    f2_pp = e2b.text_input("PP")
    f2_drao = e3b.text_input("DRAO")
    f2_ai = e4b.text_input("AI")
    f2_aao = e5b.text_input("AAO")

    st.markdown("---")

    # SECCIÓN DOPPLER (ORDEN EXACTO DE TU TABLA WORD)
    st.subheader("🔊 Eco-Doppler (Carga Hemodinámica)")
    
    # Encabezados de tabla para la web
    col_v, col_vel, col_grad, col_ins = st.columns([2, 2, 2, 2])
    col_v.write("**Válvula**")
    col_vel.write("**Velocidad cm/seg**")
    col_grad.write("**Gradiente**")
    col_ins.write("**Insuficiencia**")

    # Filas de válvulas
    # Tricúspide
    col_v.write("Tricúspide")
    v_tri = col_vel.text_input("Vel_Tri", label_visibility="collapsed")
    g_tri = col_grad.text_input("Grad_Tri", label_visibility="collapsed")
    i_tri = col_ins.selectbox("Ins_Tri", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    # Pulmonar
    col_v.write("Pulmonar")
    v_pul = col_vel.text_input("Vel_Pul", label_visibility="collapsed")
    g_pul = col_grad.text_input("Grad_Pul", label_visibility="collapsed")
    i_pul = col_ins.selectbox("Ins_Pul", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    # Mitral
    col_v.write("Mitral")
    v_mit = col_vel.text_input("Vel_Mit", label_visibility="collapsed")
    g_mit = col_grad.text_input("Grad_Mit", label_visibility="collapsed")
    i_mit = col_ins.selectbox("Ins_Mit", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    # Aórtica
    col_v.write("Aórtica")
    v_ao = col_vel.text_input("Vel_Ao", label_visibility="collapsed")
    g_ao = col_grad.text_input("Grad_Ao", label_visibility="collapsed")
    i_ao = col_ins.selectbox("Ins_Ao", ["No", "Sí (Leve)", "Sí (Mod)", "Sí (Sev)"], label_visibility="collapsed")

    st.markdown("---")
    conclusion = st.text_area("Conclusión Final", value="Ecocardiograma Doppler dentro de parámetros normales.")

    # EL BOTÓN QUE SIEMPRE DEBE APARECER
    enviado = st.form_submit_button("🚀 GENERAR INFORME EN WORD")

# 3. Lógica después de presionar el botón
if enviado:
    if not pac:
        st.error("Por favor, ingrese el nombre del paciente.")
    else:
        dict_datos = {
            "pac": pac, "fec": fec.strftime("%d/%m/%Y"), "peso": peso, "alt": alt,
            "ddvd": f1_ddvd, "ddvi": f1_ddvi, "dsvi": f1_dsvi, "fa": f1_fa, "es": f1_es,
            "siv": f2_siv, "pp": f2_pp, "drao": f2_drao, "ai": f2_ai, "aao": f2_aao,
            "v_tri": v_tri, "g_tri": g_tri, "i_tri": i_tri,
            "v_pul": v_pul, "g_pul": g_pul, "i_pul": i_pul,
            "v_mit": v_mit, "g_mit": g_mit, "i_mit": i_mit,
            "v_ao": v_ao, "g_ao": g_ao, "i_ao": i_ao,
            "conclusion": conclusion
        }
        word_final = generar_word(dict_datos)
        st.success("Informe generado. Descárguelo aquí abajo:")
        st.download_button(
            label="📥 Descargar Word",
            data=word_final,
            file_name=f"Informe_{pac}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
