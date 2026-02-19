
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io

# --- FUNCIÓN SENIOR: LIMPIEZA ABSOLUTA ---
def procesar_nuevo_estudio(archivo_pdf):
    # 1. Cerramos cualquier conexión anterior
    archivo_pdf.seek(0)
    doc = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
    
    # 2. Extraemos datos (Si no los lee, devuelve vacío, no el anterior)
    texto = " ".join([pag.get_text() for pag in doc])
    
    # 3. Extraemos imágenes DESDE CERO (Vaciamos la lista anterior)
    nuevas_fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            pix = doc.extract_image(xref)
            if pix["size"] > 15000: # Filtro para capturas reales
                nuevas_fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return texto, nuevas_fotos

# --- LA GRILLA DE 2 COLUMNAS (4 FILAS) ---
def crear_word_profesional(datos, fotos):
    doc = Document()
    # ... (Encabezado y Texto Justificado Arial 12) ...
    
    if fotos:
        doc.add_page_break()
        doc.add_heading('ANEXO DE IMÁGENES', 1)
        # Creamos tabla: 2 columnas, filas necesarias
        tabla = doc.add_table(rows=(len(fotos) + 1) // 2, cols=2)
        for i, foto in enumerate(fotos):
            celda = tabla.rows[i // 2].cells[i % 2]
            run = celda.paragraphs[0].add_run()
            run.add_picture(foto, width=Inches(3.0)) # Tamaño óptimo para 2 por fila
    return doc
