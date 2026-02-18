
def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    
    # Configuración de estilo
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Título Principal
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True

    # Cuerpo del Informe
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS", "I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # --- SECCIÓN DE FIRMA (Faltaba en el Word) ---
    doc.add_paragraph("\n") # Espacio para la firma
    firma = doc.add_paragraph()
    firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_firma = firma.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    run_firma.bold = True

    # --- SECCIÓN DE IMÁGENES EN FILAS DE A 2 ---
    if pdf_bytes:
        doc.add_page_break()
        header_img = doc.add_paragraph()
        header_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header_img.add_run("ANEXO DE IMÁGENES").bold = True
        
        pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
        imagenes = []
        for page in pdf_file:
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = pdf_file.extract_image(xref)
                imagenes.append(base_image["image"])
        
        # Crear tabla para organizar 2 imágenes por fila
        if imagenes:
            num_imgs = len(imagenes)
            rows = (num_imgs + 1) // 2
            table = doc.add_table(rows=rows, cols=2)
            table.autofit = True
            
            for i, img_data in enumerate(imagenes):
                row = i // 2
                col = i % 2
                paragraph = table.cell(row, col).paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                # Ajustamos el ancho a 3 pulgadas para que entren dos cómodas
                run.add_picture(io.BytesIO(img_data), width=Inches(3.0))
        
        pdf_file.close()
    
    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()
