# -*- coding: utf-8 -*-

#import tabula as tb
#frames_list = tb.read_pdf(FILE_PATH, pages='all')
# https://github.com/py-pdf/PyPDF2/issues/480
# https://stackoverflow.com/questions/45390608/eof-marker-not-found-while-use-pypdf2-merge-pdf-file-in-python

import os
os.chdir(r'C:\Users\USUARIO\Desarrollo\lectorPDF')

from datetime import datetime
import shutil as sh
import config
import pandas as pd
from glob import glob
from zipfile import ZipFile
import PyPDF2

import xml.etree.ElementTree as ET

today = datetime.today().strftime('%Y.%m.%d')
zips_paths = r"C:\Users\USUARIO\Desarrollo\lectorPDF\Facturas_DIAN\Pendientes"
dest_path = rf'C:\Users\USUARIO\Desarrollo\lectorPDF\Facturas_DIAN\{today}'
dest_zip_path = os.path.join(dest_path, 'Archivos_zip')
contado_path = os.path.join(dest_path, 'Contado')
credito_path = os.path.join(dest_path, 'Credito')
error_path = os.path.join(dest_path, 'Error')
folders = [dest_path, dest_zip_path, contado_path, credito_path, error_path]

def validate_create_folders(folders: list):
    for folder in folders:
        if not os.path.isdir(folder):
            os.mkdir(folder)
    
def get_paths_to_unzip(zips_paths: str):
    paths_unzip = glob(os.path.join(zips_paths, "*.zip"))
    
    return paths_unzip
    
def unzip_files(zip_path: str, dest_path: str):
    ZipFile(zip_path, mode='r').extractall(dest_path)
    sh.copy2(zip_path, dest_zip_path)
    
def get_pdf_paths(dest_path):
    pdf_paths = glob(os.path.join(dest_path, '*.pdf'))
    
    return pdf_paths

def read_pdf(path: str):
    file_pdf = open(path, 'rb')
    xml_path = os.path.splitext(path)[0] + '.xml'
    
    try:
        pdfReader = PyPDF2.PdfFileReader(file_pdf, strict=False)
    except:
        correct_pdf_eof(file_pdf, path)
        file_pdf = open(path, 'rb')
        try:
            pdfReader = PyPDF2.PdfFileReader(file_pdf, strict=False)
        except:
            print(f'ERROR: {path}')
            sh.copy2(path, error_path)
            return None
    
    num_pages = pdfReader.getNumPages()
    
    doc_text = ''
    for page in range(num_pages):
        text = pdfReader.getPage(page).extractText()
        doc_text = doc_text + text
    
    return doc_text

def text_to_dataframe(doc_text):
    linesNum = dict(enumerate(doc_text.splitlines()))
    dict_fields = {}
    sectionNum = 0
    
    for k, v in linesNum.items():
        for i, section in dict(enumerate(config.fieldsToSearch.keys())).items():
            if section.lower() in v.lower():
                sectionNum = i
        
            for field, dist in config.fieldsToSearch[section].items():
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
    text_dict = dict(enumerate(root.itertext()))
    
    return text_dict

def xml_to_excel(xmls):
    xmls_df = []
    for xml in xmls:
        text_dict = parse_xml(xml)
        xmls_df.append(pd.DataFrame(text_dict, index=[xml]).transpose())
    df_total = pd.concat(xmls_df, axis=1)
    
    return df_total

def separate_contado_credito(df_total):
    contado = df_total[df_total['0 Forma de pago']=='Contado']
    credito = df_total[df_total['0 Forma de pago']=='Crédito']
    
    for key, df in {'Contado': contado, 'Credito': credito}.items():
        for file in df['0 Código Único de Factura - CUFE']:
            file_orig = os.path.join(dest_path, file + ".pdf")
            file_dest = os.path.join(dest_path, key)
            sh.copy2(file_orig, file_dest)
                        
def main(export: bool = False):
    validate_create_folders(folders)
    paths_unzip = get_paths_to_unzip(zips_paths)
    for zip_path in paths_unzip:
        unzip_files(zip_path, dest_path)
    
    pdf_paths = get_pdf_paths(dest_path)
    
    list_df = []
    for path in pdf_paths:
       doc_text = read_pdf(path)
       if not doc_text is None:
           df_fields = text_to_dataframe(doc_text)
           list_df.append(df_fields)
     
    df_total = pd.concat(list_df).sort_index(axis=1)
    separate_contado_credito(df_total)
    
    if export:
        cons_path = os.path.join(dest_path, f'Consolidado_{today}.xlsx')
        df_total.to_excel(cons_path, index=False)
    
    return df_total
       
if __name__ == '__main__':
    df_total = main(export=True)


