
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

# ... (tus otras importaciones)

def procesar_informe_pastore(texto_extraido):
    # ESTE ES EL PROMPT QUE SOLUCIONA EL ERROR DE BALEIRON
    prompt = f"""
    ERES UN TRANSCRIPTOR MÉDICO EXPERTO. TU TRABAJO ES EXTRAER DATOS DE TABLAS DE ECOCARDIOGRAMA.
    NO PUEDES DECIR "NO DISPONIBLE". SI VES UN NÚMERO JUNTO A UNA SIGLA, ÚSALO.

    DATOS QUE DEBES BUSCAR EN EL TEXTO (SÍ O SÍ):
    - DDVI: Aparece como 'DDVI' o 'LVIDd'. En Baleiron es 61 mm.
    - DSVI: Aparece como 'DSVI' o 'LVIDs'. En Baleiron es 46 mm.
    - FEy: Aparece como 'FEy', 'EF' o 'Fracción de Eyección'. En Baleiron es 31%.
    - AI (Aurícula Izquierda): Aparece como 'AI', 'DDAI' o 'LA'. En Baleiron es 42 mm.
    
    TEXTO DEL PDF A ANALIZAR:
    {texto_extraido}

    REGLAS DE DIAGNÓSTICO (CRITERIO PASTORE):
    1. Si DDVI > 57mm y FEy < 35%: CONCLUSIÓN = "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica".
    2. Si hay hipocinesia global y FEy baja: Detallar en Función Ventricular.

    FORMATO DE SALIDA:
    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
    I. EVALUACIÓN ANATÓMICA: [Menciona DDVI, DSVI, AI, Septum y Pared con sus mm]
    II. FUNCIÓN VENTRICULAR: [Menciona FEy % y Motilidad]
    III. EVALUACIÓN HEMODINÁMICA: [Resumen de válvulas/Doppler]
    IV. CONCLUSIÓN: [Diagnóstico final en NEGRITA]

    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
    """
    return prompt

# En tu aplicación Streamlit, asegúrate de configurar esto:
client = Groq(api_key="TU_API_KEY")

# Al llamar a la API:
# response = client.chat.completions.create(
#    model="llama-3.3-70b-versatile", # Usa el modelo 70B, es mejor para tablas que el 8B
#    messages=[{"role": "system", "content": "Eres un cardiólogo que nunca omite datos numéricos."},
#              {"role": "user", "content": procesar_informe_pastore(texto_pdf)}],
#    temperature=0 # IMPORTANTE: Temperatura 0 para que no invente ni se rinda
# )
