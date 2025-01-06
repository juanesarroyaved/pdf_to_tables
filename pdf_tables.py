# -*- coding: utf-8 -*-

"""
TO-DO:
    - Optimizar y organizar código.
    - Una mejor forma de leer los XMLs
    - Pasar info de XMLs a Excel
    - Que cree una carpeta con la hora
    - Crear un archivo de Logs para el usuario.
    - Actualizar today y dest_path con c/ejecución para crear nueva carpeta.
    - Independizar nombre del zip con el de la factura porque algunos nombres son diferentes.
"""

import os
os.chdir(r'C:\Z_Proyectos\lectorPDF')

import shutil as sh
from config import folders, dest_path, dest_zip_path, error_path, fieldsToSearch, zips_paths, logs_path, today
import requests

import pandas as pd
from glob import glob
from zipfile import ZipFile
import PyPDF2
import logging

import xml.etree.ElementTree as ET

def validate_create_folders(folders: list):
    for folder in folders:
        if not os.path.isdir(folder):
            os.mkdir(folder)
    
def get_paths_to_unzip(zips_paths: str):
    paths_unzip = glob(os.path.join(zips_paths, "*.zip"))
    
    return paths_unzip
    
def unzip_files(zip_path: str, dest_path: str):
    zipfile = ZipFile(zip_path, mode='r')
    zipfile.extractall(dest_path)
    move_file(zip_path, dest_zip_path)
    list_files = zipfile.namelist()
    files = {}
    for f in list_files:
        if 'pdf' in f:
            files['pdf'] = f
        elif 'xml' in f:
            files['xml'] = f
    
    return files

def move_file(file_orig, file_dest):
    try:
        sh.copy2(file_orig, file_dest)
    except:
        logging.info(f'ERROR: {file_orig}')
    
def get_pdf_paths(dest_path):
    pdf_paths = glob(os.path.join(dest_path, '*.pdf'))
    
    return pdf_paths

def get_xml_paths(dest_path):
    xml_paths = glob(os.path.join(dest_path, '*.xml'))
    
    return xml_paths

def read_pdf(path: str):
    file_pdf = open(path, 'rb')
    try:
        pdfReader = PyPDF2.PdfFileReader(file_pdf, strict=False)
        num_pages = pdfReader.getNumPages()
        doc_text = ''
        for page in range(num_pages):
            text = pdfReader.getPage(page).extractText()
            doc_text = doc_text + text
        return doc_text
    except:
        return None
    
def text_to_dataframe(doc_text):
    linesNum = dict(enumerate(doc_text.splitlines()))
    dict_fields = {}
    sectionNum = 0
    
    for k, v in linesNum.items():
        for i, section in dict(enumerate(fieldsToSearch.keys())).items():
            if section.lower() in v.lower():
                sectionNum = i
        
            for field, dist in fieldsToSearch[section].items():
                fieldName = str(sectionNum) + ' ' + field
                if field.lower() in v.lower():
                    if type(dist) == list:
                        dict_fields[fieldName] = ''.join(linesNum[int(k) + dis] for dis in dist)
                    else:
                        dict_fields[fieldName] = linesNum[int(k) + dist]
    
    df_fields = pd.DataFrame.from_dict(dict_fields, orient='index').transpose()
    
    return df_fields

def correct_pdf_eof(file_pdf, path):
    txt = file_pdf.readlines()
    for i, x in enumerate(txt[::-1]):
        if b'%%EOF' in x:
            actual_line = len(txt)-i
            print(f'EOF found at line position {-i} = actual {actual_line}, with value {x}')
            new_txt = txt[:actual_line]
            
            with open(f'{path}', 'wb') as f:
                f.writelines(new_txt)
            break

def parse_xml(xml_path):
    root = ET.parse(f'{xml_path}').getroot()
    pago = 0
    for r in root:
        if 'PaymentMeans' in r.tag:
            pago = int(r[0].text)
    
    file_orig = os.path.join(dest_path, 'Archivos_zip', cufe + ".zip")
    
    status = 'Pending'
    if pago == 1:
        file_dest = os.path.join(dest_path, 'Contado')
        status = 'OK'
    elif pago == 2:
        file_dest = os.path.join(dest_path, 'Credito')
        status = 'OK'
        
    if not status == 'Pending':
        move_file(file_orig, file_dest)
    
    return status

def separate_contado_credito(df_total):
    
    if '0 Código Único de Factura - CUFE' not in df_total.columns: return
    
    df_total['0 Código Único de Factura - CUFE'] = df_total['0 Código Único de Factura - CUFE'].fillna('NA')
    contado = df_total[df_total['0 Forma de pago']=='Contado']
    credito = df_total[df_total['0 Forma de pago']=='Crédito']
    
    for key, df in {'Contado': contado, 'Credito': credito}.items():
        for file in df['0 Código Único de Factura - CUFE']:
            file_orig = os.path.join(dest_path, 'Archivos_zip', file + ".zip")
            file_dest = os.path.join(dest_path, key)
            move_file(file_orig, file_dest)
                
def get_it_from_dian_page(path: str):
    print(f'ERROR: {cufe}')
    logging.info(f'ERROR: {cufe}')
    
    base_url = r'https://catalogo-vpfe.dian.gov.co/Document/ShowDocumentToPublic/'
    doc_url = base_url + cufe
    response = requests.get(doc_url)
    with open(os.path.join(error_path,f'{cufe}.html'), 'wb') as f:
        f.write(response.content)
        f.close()

def validate_cufes_left(cufes_ok, cufes_all):
    cufes_left = []
    for cufe in cufes_all:
        if cufe not in cufes_ok:
            cufes_left.append(cufe)
            logging.info(f'CUFE FALTANTE: {cufe}')
    
    return cufes_left

def create_logger(dest_path):
    logging.basicConfig(filename=f'{logs_path}\{today}.log', encoding='utf-8',
                        format='%(asctime)s: %(message)s', datefmt='%Y.%m.%d %H:%M %p',
                        level=logging.DEBUG)
    
def main(export: bool = False):

    global cufe
    
    validate_create_folders(folders)
    create_logger(dest_path)
    
    logging.info('INICIO EJECUCIÓN.')
    
    cufes_ok = []
    cufes_all = []
    df_list = []
    paths_unzip = get_paths_to_unzip(zips_paths)
    for zip_path in paths_unzip:        
        files = unzip_files(zip_path, dest_path)
        cufe = os.path.splitext(os.path.split(zip_path)[1])[0]
        cufes_all.append(cufe)
        pdf_path = os.path.join(dest_path, files['pdf'])
        doc_text = read_pdf(pdf_path)
        
        if not doc_text is None:
            df_fields = text_to_dataframe(doc_text)
            df_fields['Path'] = pdf_path
            df_list.append(df_fields)
            cufes_ok.append(cufe)
            logging.info(f'OK PDF: {cufe}')
        else:
            xml_path = os.path.join(dest_path, files['xml']) 
            status = parse_xml(xml_path)
            
            if not status == 'Pending':
                logging.info(f'OK XML: {cufe}')
                cufes_ok.append(cufe)
            else:
                get_it_from_dian_page(xml_path)
                file_orig = os.path.join(dest_path, 'Archivoz_zip', zip_path)
                move_file(file_orig, error_path)
                
    df_total = pd.concat(df_list).sort_index(axis=1)
    #separate_contado_credito(df_total)
    cufes_left = validate_cufes_left(cufes_ok, cufes_all)
    
    if export:
        cons_path = os.path.join(logs_path, f'Consolidado_{today}.xlsx')
        df_total.to_excel(cons_path, index=False)
    
    logging.info('FIN EJECUCIÓN.')
    
    return df_total

if __name__ == '__main__':
    df_total = main(export=True)

