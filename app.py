
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from bs4 import BeautifulSoup  # Librería para leer HTML
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- EL NUEVO ESCÁNER DE HTML + TXT ---

def extraer_datos_master(contenido, es_html=False):
    datos = {k: "No evaluado" for k in ["ddvi", "dsvi", "sep", "par", "fey", "fa"]}
    
    if es_html:
        # Lógica para HTML: Busca en las celdas de las tablas
        soup = BeautifulSoup(contenido, 'html.parser')
        filas = soup.find_all('tr')
        for fila in filas:
            celdas = [c.get_text().strip() for c in fila.find_all('td')]
            if len(celdas) >= 2:
                nombre = celdas[0].upper()
                valor = celdas[1].replace(',', '.')
                
                # Mapeo de etiquetas en HTML
                if "LVIDD" in nombre or "LVID(D)" in nombre: datos["ddvi"] = valor
                elif "LVIDS" in nombre or "LVID(S)" in nombre: datos["dsvi"] = valor
                elif "IVSD" in nombre or "IVS(D)" in nombre: datos["sep"] = valor
                elif "LVPWD" in nombre or "LVPW(D)" in nombre: datos["par"] = valor
                elif "EF" in nombre or "FE" in nombre: datos["fey"] = valor
                elif "FS" in nombre or "FA" in nombre: datos["fa"] = valor
    else:
        # Si sigue siendo TXT, usamos el sabueso mejorado
        mapeo = {
            "ddvi": ["LVID d", "LVIDd", "DDVI"],
            "dsvi": ["LVID s", "LVIDs", "DSVI"],
            "sep": ["IVS d", "IVSd", "Septum"],
            "par": ["LVPW d", "LVPWd", "Pared"],
            "fey": ["EF", "FEy", "LVEF", "EF(A-L)"],
            "fa": ["FS", "FA"]
        }
        for clave, etiquetas in mapeo.items():
            for etiqueta in etiquetas:
                patron = re.compile(rf"{re.escape(etiqueta)}[\s\S]{{0,500}}?value\s*=\s*([\d\.,]+)", re.I)
                match = patron.search(contenido)
                if match:
                    val = match.group(1).replace(',', '.')
                    if 0.5 <= float(val) <= 95:
                        datos[clave] = val
                        break
    return datos

# --- INTERFAZ ---

st.title("❤️ CardioReport Pro: Modo Híbrido (HTML/TXT)")

archivo_datos = st.file_uploader("1. Subir Datos (HTML o TXT)", type=["txt", "html"])
archivo_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        # Detectar si es HTML o TXT
        es_html = archivo_datos.name.endswith(".html")
        raw_content = archivo_datos.read().decode("latin-1", errors="ignore")
        
        # Extraer datos con el nuevo motor
        v = extraer_datos_master(raw_content, es_html)

        # Si FEy sigue vacío pero tenemos el 49.2 en FA (error común de Alicia)
        if v["fey"] == "No evaluado" and v["fa"] != "No evaluado":
            v["fey"] = v["fa"]

        client = Groq(api_key=api_key)
        prompt = f"""
        ERES EL DR. FRANCISCO ALBERTO PASTORE. Redacta el informe para ALICIA ALBORNOZ.
        VALORES DETECTADOS: DDVI: {v['ddvi']}mm, DSVI: {v['dsvi']}mm, Septum: {v['sep']}mm, Pared: {v['par']}mm, FEy: {v['fey']}%.
        ESTRUCTURA: I. Anatomía, II. Función, III. Hemodinámica, IV. Conclusión (Si FEy < 55% es disfunción).
        """
        
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        st.info(res.choices[0].message.content)
        # (Aquí va el resto de la lógica de descarga de Word)
