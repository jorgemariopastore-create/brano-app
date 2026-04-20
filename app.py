import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
from groq import Groq

# LEEMOS LA CLAVE DIRECTAMENTE DESDE LA CONFIGURACIÓN DE STREAMLIT
# (Ya no ponemos la clave en el código para que GitHub no nos bloquee)
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("⚠️ Error: No se encontró la clave en Secrets. Configúrala en la web de Streamlit.")
    st.stop()

# ... (El resto de tus funciones: extraer_datos_estacion, redactar_ia, generar_word se mantienen IGUAL)
# ... (Simplemente pega aquí abajo el resto de tu código que ya tenías)
