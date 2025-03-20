import streamlit as st
import time
import requests
import json
from io import BytesIO
import tempfile
import os
import unicodedata
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from msal import ConfidentialClientApplication
from reportlab.platypus import BaseDocTemplate, SimpleDocTemplate, PageTemplate, Frame, NextPageTemplate, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from reportlab.lib.colors import Color
from PIL import Image
from tempfile import NamedTemporaryFile
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import time
from reportlab.platypus import HRFlowable

path_proposta_envio = ''
versao_proposta = ''

def blank_line(elements, x):
    for i in range(x):
        elements.append(Spacer(1, 12)) 

def list_files_in_folder(access_token, folder_name, retry_attempts=3, initial_delay=10, delay=5):
    url = "https://api.hubapi.com/filemanager/api/v2/files"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Atraso inicial para garantir que o arquivo tenha tempo de ser processado
    time.sleep(initial_delay)
    
    for attempt in range(retry_attempts):
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            files = response.json().get('objects', [])
            matching_files = [file for file in files if folder_name in file['name']]
            if not matching_files:
                st.warning(f"No files found in folder '{folder_name}'.")
                return None
            
            file = matching_files[-1]
            return file['name'], file['url']
        
        else:
            st.warning(f"Failed to retrieve files: {response.status_code}, {response.text}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    st.error("Max retry attempts reached. Could not retrieve files.")
    return None

def get_versao(file_base_name):
    # Substitua com suas próprias credenciais do Azure
    CLIENT_ID = st.secrets['azure']['client_id']
    CLIENT_SECRET = st.secrets['azure']['client_secret']
    TENANT_ID = st.secrets['azure']['tenant_id']
    AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
    SCOPE = ['https://graph.microsoft.com/.default']

    # Configuração do Cliente MSAL
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY_URL,
        client_credential=CLIENT_SECRET,
    )

    # Adquirindo o Token
    result = app.acquire_token_for_client(SCOPE)

    # Verifique se o token foi adquirido com sucesso
    if 'access_token' in result:
        access_token = result['access_token']
        # Cabeçalho com o token para autenticação
        headers = {'Authorization': 'Bearer ' + access_token}

        # ID do usuário para acessar seu OneDrive
        user_id = 'cfbe7de5-e62c-4acb-8719-c6190103d174'
        folder_response = requests.get(
            f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root/children',
            headers=headers
        )
        
        if folder_response.status_code == 200:
            folders = folder_response.json().get('value', [])
            folder_id = next((item['id'] for item in folders if item['name'] == '11. Orçamentos'), None)

            if folder_id:
                # Verificar se o arquivo já existe e determinar a versão
                version = 1
                while True:
                    version_suffix = f"_v{version:02d}"
                    versioned_file_name = f"{file_base_name}{version_suffix}.pdf"
                    check_url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/11.%20Orçamentos/{versioned_file_name}'
                    check_response = requests.get(check_url, headers=headers)
                    if check_response.status_code == 404:  # Arquivo não encontrado
                        break
                    version += 1
                
                # Criar arquivo temporário com a última versão
                latest_version = version - 1
                latest_version_suffix = f"_v{latest_version:02d}"
                latest_versioned_file_name = f"{file_base_name}{latest_version_suffix}.pdf"
                
                # Baixar o conteúdo do arquivo mais recente
                download_url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/11.%20Orçamentos/{latest_versioned_file_name}:/content'
                download_response = requests.get(download_url, headers=headers)
                if download_response.status_code == 200:
                    file_content = BytesIO(download_response.content)
                    return GenerateTemp_PDF(latest_versioned_file_name, file_content)
    
    return None

def GenerateTemp_PDF(filename, file):
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, filename)
    with open(temp_file_path, 'wb') as temp_file:
        # Copiar o conteúdo para o arquivo temporário
        temp_file.write(file.getvalue())
    return temp_file_path

def upload_onedrive2(pdf_path):
    # Substitua com suas próprias credenciais do Azure
    CLIENT_ID = st.secrets['azure']['client_id']
    CLIENT_SECRET = st.secrets['azure']['client_secret']
    TENANT_ID = st.secrets['azure']['tenant_id']
    AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
    SCOPE = ['https://graph.microsoft.com/.default']

    # Configuração do Cliente MSAL
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY_URL,
        client_credential=CLIENT_SECRET,
    )

    # Adquirindo o Token
    result = app.acquire_token_for_client(SCOPE)

    # Verifique se o token foi adquirido com sucesso
    if 'access_token' in result:
        access_token = result['access_token']
        # Cabeçalho com o token para autenticação
        headers = {'Authorization': 'Bearer ' + access_token}

        # ID do usuário para acessar seu OneDrive
        user_id = 'cfbe7de5-e62c-4acb-8719-c6190103d174'
        folder_response = requests.get(
            f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root/children',
            headers=headers
        )
        
        if folder_response.status_code == 200:
            folders = folder_response.json().get('value', [])
            folder_id = next((item['id'] for item in folders if item['name'] == '11. Orçamentos'), None)

            if folder_id:
                file_name = os.path.basename(pdf_path)
                file_base_name, file_extension = os.path.splitext(file_name)
                
                # Verificar se o arquivo já existe e determinar a versão
                version = 1
                while True:
                    version_suffix = f"_v{version:02d}"
                    versioned_file_name = f"{file_base_name}{version_suffix}{file_extension}"
                    check_url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{folder_id}:/{versioned_file_name}'
                    check_response = requests.get(check_url, headers=headers)
                    if check_response.status_code == 404:  # Arquivo não encontrado
                        break
                    version += 1

                # Upload do arquivo com a versão determinada
                upload_url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{folder_id}:/{versioned_file_name}:/content'
                with open(pdf_path, "rb") as file:
                    media_content = file.read()
                
                upload_response = requests.put(upload_url, headers=headers, data=media_content)

                if upload_response.status_code in [200, 201]:
                    st.success(f"Etapa 2 de 2 - Arquivo adicionado com sucesso como '{versioned_file_name}' na pasta de orçamentos.")
                else:
                    st.error(f"Erro ao carregar o arquivo: {upload_response.status_code} {upload_response.text}")
            else:
                st.error("Pasta '11. Orçamentos' não encontrada.")
        else:
            st.error("Erro ao listar pastas na raiz do OneDrive.")
            st.json(folder_response.json())
    else:
        st.error("Erro ao adquirir o token: " + result.get("error_description", ""))
    
    pdf_path.replace('.pdf',f'_v{version:02d}.pdf')
    return version

def remove_special_characters(text):
    def clean_text(t):
        # Normalize text to decomposed Unicode form to separate characters and diacritics
        normalized_text = unicodedata.normalize('NFD', t)
        # Use regular expression to filter out non-alphanumeric characters and diacritics
        removed_special_chars = re.sub(r'[^a-zA-Z0-9\s]', '', normalized_text)
        # Remove extra whitespaces
        cleaned_text = ' '.join(removed_special_chars.split())
        return cleaned_text

    if isinstance(text, str):
        return clean_text(text)
    elif isinstance(text, list):
        return [clean_text(t) for t in text if isinstance(t, str)]
    else:
        raise TypeError("The input must be a string or a list of strings.")

def remove_hifen_from_lists(obj):
    if isinstance(obj, list):
        return [x for x in obj if x != "-"]
    elif isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = remove_none_from_lists(value)
    return obj

def remove_none_from_lists(obj):
    if isinstance(obj, list):
        return [x for x in obj if x != "Nenhum"]
    elif isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = remove_none_from_lists(value)
    return obj
                      
def sorting_key(s):
    # Extrai os componentes da string usando expressões regulares
    match = re.search(r'(P\d+)_UH(\d+)_([A-Z]+[A-Z0-9]*)', s)
    if match:
        pav, uh, ambiente = match.groups()
        return (pav, int(uh), ambiente)
    else:
        # Retorna uma tupla com valores padrão que colocam esta string no final
        return ("", float('inf'), s)

def GenerateTemp_URL(sfx, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        # Fazer o download do conteúdo da URL com cabeçalhos personalizados
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()  # Verifica se a solicitação foi bem-sucedida

        # Criar um arquivo temporário e copiar o conteúdo para ele
        with NamedTemporaryFile(delete=False, suffix=sfx) as fname:
            for chunk in response.iter_content(chunk_size=8192):
                fname.write(chunk)
            name_path = fname.name

        # Verificar se o arquivo é um PDF válido
        with open(name_path, 'rb') as file:
            header = file.read(4)
            if header != b'%PDF':
                raise ValueError("Downloaded file is not a valid PDF")

        print(f"Temporary file created at: {name_path}")
        return name_path

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except ValueError as e:
        print(f"Error: {e}")

def GenerateTemp(sfx, file):
    with NamedTemporaryFile(delete=False, suffix=sfx) as fname:
        # Copiar o conteúdo para o arquivo temporário
        fname.write(file.getvalue())
        name_path = fname.name
        return name_path

def read_img(url_da_imagem):
    try:
        if url_da_imagem.startswith('http'):
            response = requests.get(url_da_imagem)
            image = Image.open(BytesIO(response.content))
            st.image(image)
        else:
            image = Image.open(url_da_imagem)
            st.image(image)
    except Exception as e:
        st.error(f"Erro ao carregar a imagem: {e}")

def carregar_imagem(url_da_imagem):    
    try:
        if url_da_imagem.startswith('http'):
            response = requests.get(url_da_imagem)
            image = Image.open(BytesIO(response.content))
        else:
            image = Image.open(url_da_imagem)
        return image
    except Exception as e:
        st.error(f"Erro ao carregar a imagem: {e}")
        return None

email_principal = None
custom_color = Color(118/255.0, 136/255.0, 40/255.0)


    
def get_max_value_from_folder_names(CLIENT_ID, CLIENT_SECRET, TENANT_ID, drive_id, folder_item_id):
    AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
    SCOPE = ['https://graph.microsoft.com/.default']
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY_URL, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(SCOPE)

    max_value = -1

    if 'access_token' in result:
        access_token = result['access_token']
        headers = {'Authorization': f'Bearer {access_token}'}

        list_folders_url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_item_id}/children'
        folders_response = requests.get(list_folders_url, headers=headers).json()

        for folder in folders_response.get('value', []):
            if 'folder' in folder:
                folder_name = folder['name']
                # Assuming the folder name format is "XXX - blablabla"
                try:
                    value = int(folder_name.split(' - ')[0])
                    max_value = max(max_value, value)
                except ValueError:
                    # The folder name doesn't start with a numeric value
                    continue

        if max_value > -1:
            print(f"The maximum value found is: {max_value}")
            return max_value
        else:
            print("No numeric prefixes found in folder names.")
    else:
        print("Error acquiring token:", result.get("error_description", ""))

def copy_folder_contents(drive_id, source_folder_id, destination_folder_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    list_items_url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{source_folder_id}/children'
    items_response = requests.get(list_items_url, headers=headers)
    
    if items_response.status_code == 200:
        items = items_response.json().get('value', [])
        
        for item in items:
            copy_url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item["id"]}/copy'
            copy_body = {
                "parentReference": {
                    "id": destination_folder_id
                }
            }
            copy_response = requests.post(copy_url, headers=headers, json=copy_body)
            
            if copy_response.status_code == 202:
                print(f"Copying {item['name']} started. Waiting for completion...")
                # Wait a bit to give time for the copy operation
                time.sleep(5)  # Wait for 5 seconds (adjust as needed based on file size)
            else:
                print(f"Failed to initiate copy for {item['name']}: {copy_response.status_code} {copy_response.text}")
    else:
        print(f"Error listing items in source folder: {items_response.status_code} {items_response.text}")
        
def upload_to_3projetos(file_path, file_name, new_folder_name):
    # Azure credentials and MSAL Client Configuration
    CLIENT_ID = st.secrets['azure']['client_id']
    CLIENT_SECRET = st.secrets['azure']['client_secret']
    TENANT_ID = st.secrets['azure']['tenant_id']
    AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
    SCOPE = ['https://graph.microsoft.com/.default']
    
    item_id = '013JXZXANSVFYITQ6LDBEZYV2QO2FRFRMH'  # Replace with actual shared drive ID
    drive_id = "b!yrE7SxqrykWOoQYwwGXFrzTd7LHaY8FOgzJR4akW6vvvT1mGsai9QqqR_4XDxhMj"  # Replace with actual shared folder item ID
    
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY_URL, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(SCOPE)

    if 'access_token' in result:
        access_token = result['access_token']
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        new_folder_name = str(get_max_value_from_folder_names(CLIENT_ID, CLIENT_SECRET, TENANT_ID, drive_id, item_id)+1)+' - '+new_folder_name
        # Step 1: Create new folder
        create_folder_url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children'
        folder_data = {
            "name": new_folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        folder_response = requests.post(create_folder_url, headers=headers, json=folder_data)
        if folder_response.status_code in [200, 201]:
            new_folder_id = folder_response.json()['id']
            print(f"New folder '{new_folder_name}' created successfully.")
            
            # Step 2: Upload file to the new folder
            upload_url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{new_folder_id}:/{file_name}:/content'
            with open(file_path, "rb") as file:
                file_content = file.read()
            upload_response = requests.put(upload_url, headers=headers, data=file_content)
            if upload_response.status_code in [200, 201]:
                print("File successfully uploaded to the new folder.")
                # Step 3: Copy folder contents
                source_folder_id = "01FCG3WNBQBOAVYJGQMFD3YNRVQAWUC433"  # ID of the "000 - EMPRESA - PROJETO" folder
                copy_folder_contents(drive_id, source_folder_id, new_folder_id, access_token)
            else:
                print(f"Error uploading file: {upload_response.status_code} {upload_response.text}")
        else:
            print(f"Error creating folder: {folder_response.status_code} {folder_response.text}")
    else:
        print("Error acquiring token:", result.get("error_description", ""))

def upload_to_3projetos_v02(new_folder_name):
    # Azure credentials and MSAL Client Configuration
    CLIENT_ID = st.secrets['azure']['client_id']
    CLIENT_SECRET = st.secrets['azure']['client_secret']
    TENANT_ID = st.secrets['azure']['tenant_id']
    AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
    SCOPE = ['https://graph.microsoft.com/.default']
    
    item_id = '013JXZXANIYRELCT76MZHYGO2OF6YB7XAR'  # Replace with actual shared drive ID
    drive_id = "b!yrE7SxqrykWOoQYwwGXFrzTd7LHaY8FOgzJR4akW6vvvT1mGsai9QqqR_4XDxhMj"
    
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY_URL, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(SCOPE)

    if 'access_token' in result:
        access_token = result['access_token']
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        new_folder_name = str(get_max_value_from_folder_names(CLIENT_ID, CLIENT_SECRET, TENANT_ID, drive_id, item_id)+1)+' - '+new_folder_name
        # Step 1: Create new folder
        create_folder_url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children'
        folder_data = {
            "name": new_folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        folder_response = requests.post(create_folder_url, headers=headers, json=folder_data)
        if folder_response.status_code in [200, 201]:
            new_folder_id = folder_response.json()['id']
            print(f"New folder '{new_folder_name}' created successfully.")
            # Step 3: Copy folder contents
            source_folder_id = "013JXZXAOOEHVKTIHXVVHIERCVM4MJJHKZ"  # ID of the "000 - EMPRESA - PROJETO" folder
            copy_folder_contents(drive_id, source_folder_id, new_folder_id, access_token)

        else:
            print(f"Error creating folder: {folder_response.status_code} {folder_response.text}")
    else:
        print("Error acquiring token:", result.get("error_description", ""))


def generate_proposal_pdf2(empresa, id, negocio, produtos, valor_negocio, desconto, condicao_pagamento, prazo, nome_contato_principal, escopos):
                
    # Path to the font file
    font_path = Path(__file__).parent / "PDFs2/Hero-Regular.ttf"

    # Ensure the font file exists
    if not font_path.is_file():
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # Create a temporary file for the font
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tmp_font:
        # Read the font file and write its content to the temporary file
        with open(font_path, 'rb') as font_file:
            tmp_font.write(font_file.read())

    # Register the font with a name (e.g., 'HeroLightRegular')
    pdfmetrics.registerFont(TTFont('HeroLightRegular', tmp_font.name))

            # Path to the font file
    font_path_2 = Path(__file__).parent / "PDFs2/Hero-Bold.ttf"

    # Ensure the font file exists
    if not font_path_2.is_file():
        raise FileNotFoundError(f"Font file not found: {font_path_2}")

    # Create a temporary file for the font
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tmp_font:
        # Read the font file and write its content to the temporary file
        with open(font_path_2, 'rb') as font_file:
            tmp_font.write(font_file.read())

    # Register the font with a name (e.g., 'HeroLightRegular')
    pdfmetrics.registerFont(TTFont('HeroBold', tmp_font.name))


    font_path_3 = Path(__file__).parent / "PDFs2/Hero-Light.ttf"

    # Ensure the font file exists
    if not font_path_3.is_file():
        raise FileNotFoundError(f"Font file not found: {font_path_2}")

    # Create a temporary file for the font
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tmp_font:
        # Read the font file and write its content to the temporary file
        with open(font_path_2, 'rb') as font_file:
            tmp_font.write(font_file.read())

    # Register the font with a name (e.g., 'sessionLightRegular')
    pdfmetrics.registerFont(TTFont('sessionLight', tmp_font.name))
    
    def add_background(canvas, doc):
        # Define your background drawing code here
        canvas.saveState()
        canvas.drawImage(image_reader, 0, 0, width=A4[0], height=A4[1])
        canvas.restoreState()

        # Create a temporary directory for the PDF
    temp_dir = tempfile.mkdtemp()
    pdf_filename = f'{negocio}_{id}.pdf'
    capa = f'Capa.pdf'
    contracapa = f'Contracapa.pdf'           
    pdf_path = os.path.join(temp_dir, pdf_filename)
    capa_path = os.path.join(temp_dir, capa)
    contracapa_path = os.path.join(temp_dir, contracapa)
    
    # ESTILOS DE PARAGRAFGO
    # Define your styles and elements
    styles = getSampleStyleSheet()
    hero_light_style = ParagraphStyle(
        'HeroLight',
        parent=styles['Normal'],
        fontName='HeroLightRegular',
        fontSize=10,
        leading=16
    )
    session_light_style = ParagraphStyle(
        'sessionLight',
        parent=styles['Normal'],
        fontName='HeroLightRegular',
        fontSize=10,
        leading=16
    )
    hero_bold_style = ParagraphStyle(
        'HeroBold',
        parent=styles['Normal'],
        fontName='HeroBold',
        fontSize=10,
        leading=16
    )
    left_hero_light_style = ParagraphStyle(
        'HeroLight',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        fontName='HeroLightRegular',
        fontSize=10,
        leading=16,
        #leftIndent= 1 * cm  # Define o recuo de 2 cm à esquerda
    )
    left_hero_light_style_small = ParagraphStyle(
        'HeroLight',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        fontName='HeroLightRegular',
        fontSize=8,
        leading=16,
        leftIndent= 1 * cm  # Define o recuo de 2 cm à esquerda
    )
    left_hero_light_style_small_gray = ParagraphStyle(
        'HeroLight',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        fontName='HeroLightRegular',
        fontSize=8,
        leading=16,
        textColor=colors.gray,
        #leftIndent= 1 * cm  # Define o recuo de 2 cm à esquerda
    )
    
    justify_hero_light_style_small_gray = ParagraphStyle(
        'HeroLight',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontName='HeroLightRegular',
        fontSize=8,
        leading=16,
        textColor=colors.gray,
        leftIndent= 1 * cm  # Define o recuo de 2 cm à esquerda
    )
    left_hero_bold_style = ParagraphStyle(
        'HeroBold',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        fontName='HeroBold',
        fontSize=10,
        leading=16,
        #leftIndent=1 * cm  # Define o recuo de 2 cm à esquerda
    )
    
    right_hero_light_style = ParagraphStyle(
        'HeroLight',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontName='HeroLightRegular',
        fontSize=10,
        leading=16,
        #leftIndent= 1 * cm  # Define o recuo de 2 cm à esquerda
    )
    right_hero_bold_style = ParagraphStyle(
        'HeroBold',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontName='HeroBold',
        fontSize=10,
        leading=16,
        #leftIndent=1 * cm  # Define o recuo de 2 cm à esquerda
    )

    right_hero_bold_style_green = ParagraphStyle(
        'HeroBold',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontName='HeroBold',
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#7a8630")
        #leftIndent=1 * cm  # Define o recuo de 2 cm à esquerda
    )

    right_hero_light_style_gray = ParagraphStyle(
        'HeroBold',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontName='HeroBold',
        fontSize=10,
        leading=16,
        textColor=colors.gray,
        #leftIndent=1 * cm  # Define o recuo de 2 cm à esquerda
    )
    title_hero_light_style = ParagraphStyle(
        'TitleHeroLight',
        parent=styles['Normal'],
        fontName='HeroLightRegular',
        alignment=TA_LEFT,
        fontSize=30,
        leading=35,
        #leftIndent= -0.5 * cm
    )

    right_aligned_style = ParagraphStyle(
        'RightAlignedHeroLight',
        parent=hero_light_style,
        alignment=TA_RIGHT,
        fontSize=10
    )
    left_aligned_style = ParagraphStyle(
        'LeftAlignedHeroLight',
        parent=hero_light_style,
        alignment=TA_LEFT,
        fontSize=10

    )
    contra_aligned_style = ParagraphStyle(
        'ContraAlignedHeroLight',
        parent=styles['Normal'],
        fontName='HeroLightRegular',
        alignment=TA_LEFT,
        fontSize=15,
        textColor=colors.whitesmoke,
        leftIndent=-0.2 * cm  # Define o recuo de 2 cm à esquerda


    )
    justify_style = ParagraphStyle(
        'JustifyStyle',
        parent=hero_light_style,
        alignment=TA_JUSTIFY
    )

    center_style = ParagraphStyle(
        'JustifyStyle',
        parent=hero_light_style,
        alignment=TA_CENTER,
        fontSize=12
    )

    center_style_bold_green = ParagraphStyle(
        'JustifyStyle',
        parent=hero_bold_style,
        alignment=TA_CENTER,
        fontSize=12,
        textColor=colors.HexColor("#7a8630")
    )
    
    # CAPA DA PROPOSTA
    image_reader=None
    for p in produtos:
        #st.write(p)
        if 'NBR' in p:
            #st.write('entrei')
            image_reader = Path(__file__).parent / "PDFs2/NBR_Capa.png"
            break
    if image_reader is None:
        image_reader = Path(__file__).parent / "PDFs2/Capa.png"

    #st.write(image_reader)

    # Criação do documento no padrão A4
    doc = BaseDocTemplate(capa_path, pagesize=A4)

    # Create a frame and a page template with the background
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='background', frames=frame, onPage=add_background)
    doc.addPageTemplates([template])

    # Conteúdo do documento - lista de todos os elementos que compoe a proposta
    elements = []

    if 'NBR' in str(image_reader):
        blank_line(elements,19)
        elements.append(Paragraph('', title_hero_light_style))
        elements.append(PageBreak())

    else:
        blank_line(elements,19)
        elements.append(Paragraph(f'{negocio}', title_hero_light_style))
        elements.append(PageBreak())

    # PAGINA DA PROPOSTA
    # Gerar PDF
    doc.build(elements)

    # Initialize the BaseDocTemplate
    doc = BaseDocTemplate(pdf_path, pagesize=A4)

    image_reader = Path(__file__).parent / "PDFs2/Template.png"

    for p in produtos:
        if 'NBR' in p:
            image_reader = Path(__file__).parent / "PDFs2/Template_NBRFast.png"
            break

    # Create a frame and a page template with the background
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='background', frames=frame, onPage=add_background)
    doc.addPageTemplates([template])


    indent_style = ParagraphStyle('Indented', parent=hero_light_style, leftIndent=20)

    # Data de hoje
    data_hoje = datetime.now()

    # Mapeamento dos meses em inglês para português
    meses = {
        "January": "janeiro",
        "February": "fevereiro",
        "March": "março",
        "April": "abril",
        "May": "maio",
        "June": "junho",
        "July": "julho",
        "August": "agosto",
        "September": "setembro",
        "October": "outubro",
        "November": "novembro",
        "December": "dezembro"
    }

    #st.write(1)
    # Formatando a data
    data_formatada = data_hoje.strftime("%d de %B de %Y")
    mes_portugues = meses[data_hoje.strftime("%B")]
    data_formatada_ptbr = data_formatada.replace(data_hoje.strftime("%B"), mes_portugues)

    # CABEÇALHO, NUMERO PROPOSTA, VALIDADE DA PROPOSTA
    blank_line(elements,2)
    elements.append(Paragraph(f'Curitiba, {data_formatada_ptbr}', hero_bold_style))
    elements.append(Paragraph(f'Código da proposta: {id}', hero_bold_style))
    elements.append(Paragraph(f'Validade da proposta: 30 dias', hero_bold_style))

    blank_line(elements,1)
    elements.append(Paragraph('À', hero_light_style))
    elements.append(Paragraph(f'{empresa}', hero_light_style))
    elements.append(Paragraph(f'A/C: {nome_contato_principal}', hero_light_style))
    elements.append(Paragraph(f'Ref: {negocio}', hero_bold_style))

    blank_line(elements, 1)
    elements.append(Paragraph(f'Proposta comercial Hygge referente ao empreendimento {negocio}, conforme tabela de investimento a seguir e detalhamento do escopo nas páginas subsequentes.', justify_style))
    
    blank_line(elements,2)
    elements.append(Paragraph(f'INVESTIMENTO', center_style_bold_green))
    blank_line(elements,1)
    
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.black, spaceBefore=5, spaceAfter=5))
    for p, e in zip(produtos, escopos):
        elements.append(Paragraph(f'{p}', left_hero_light_style))
        if len(e) > 0:
            for v in e:
                elements.append(Paragraph(f'• {v}', justify_hero_light_style_small_gray))
    
    elements.append(HRFlowable(width="100%", thickness=0.5, lineCap='round', color=colors.black, spaceBefore=5, spaceAfter=5))

    if desconto > 0:
        elements.append(Paragraph(f'Total                     R$ {float(valor_negocio+desconto):,.2f}'.replace(',', '.'), right_hero_bold_style))
        elements.append(Paragraph(f'Desconto                 - R$ {float(desconto):,.2f}'.replace(',', '.'), right_hero_light_style_gray))
        elements.append(Paragraph(f'Total com desconto        R$ {float(valor_negocio):,.2f}'.replace(',', '.'), right_hero_bold_style_green))
        elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.black, spaceBefore=5, spaceAfter=5))

    else:    
        elements.append(Paragraph(f'Total                     R$ {float(valor_negocio+desconto):,.2f}'.replace(',', '.'), right_hero_bold_style_green))
        elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.black, spaceBefore=5, spaceAfter=5))


    blank_line(elements,3)
    # texto das condições de pagamento
    elements.append(Paragraph(f'Forma de pagamento:', left_hero_light_style))
    elements.append(Paragraph(f'{condicao_pagamento}', left_hero_bold_style))
    blank_line(elements,1)
    elements.append(Paragraph(f'Prazo de execução:', left_hero_light_style))
    elements.append(Paragraph(f'{prazo}', left_hero_bold_style))                

    # Gerar PDF da contracapa
    doc.build(elements)

    image_reader = Path(__file__).parent / "PDFs2/Contracapa.png"

    # Initialize the BaseDocTemplate
    doc = BaseDocTemplate(contracapa_path, pagesize=A4)

    # Create a frame and a page template with the background
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='background', frames=frame, onPage=add_background)
    doc.addPageTemplates([template])

    # Conteúdo do documento
    elements = []

    blank_line(elements,1)

    # Gerar PDF dos aditivos e adicionais e textos extra
    doc.build(elements)
    aditivo_filename = Path(__file__).parent / "PDFs2/Aditivos.pdf"
    termos_filename = Path(__file__).parent / "PDFs2/Termos e condições da prestação de serviço.pdf"
    NBRFast_Termos = Path(__file__).parent / "PDFs2/NBRFast_Termos.pdf"
    NBR_disposicoes = Path(__file__).parent / "PDFs2/NBRFast_Disposicoes.pdf" 
    #NBR_clientes_hygge = Path(__file__).parent / "PDFs2/NBRFAst_clientes.pdf"
    disposicoes_gerais_filename = Path(__file__).parent / "PDFs2/Disposições Gerais.pdf"  
    clientes_hygge_filename = Path(__file__).parent / "PDFs2/Nossos clientes.pdf"
    pq_escolher_filename = Path(__file__).parent / "PDFs2/pq a Hygge.pdf"
    

    # Supondo que 'produtos' seja uma lista de strings
    flag_EVTA = any('Certificação' in produto or 'Auditoria' in produto for produto in produtos)

    if flag_EVTA:
        pdfs = [capa_path]  # CAPA
   

        # Seleciona um produto de referência que contenha as palavras-chave
        produto_ref = next((produto for produto in produtos if 'Certificação' in produto or 'Auditoria' in produto), None)
        if produto_ref:
            # Verifica se o arquivo de INTRO existe
            path_intro = Path(__file__).parent / f"PDFs2/Descritivo - {produto_ref} - intro.pdf"
            if path_intro.exists():
                #st.success(f"Arquivo encontrado: {path_intro.name}")
                pdfs.append(path_intro)
            else:
                st.warning(f"Arquivo não encontrado: {path_intro.name}. Será omitido.")

            # Adiciona a proposta
            pdfs.append(pdf_path)

            # Verifica se o arquivo de ESCOPO existe
            path_escopo = Path(__file__).parent / f"PDFs2/Descritivo - {produto_ref} - escopo.pdf"
            if path_escopo.exists():
                #st.success(f"Arquivo encontrado: {path_escopo.name}")
                pdfs.append(path_escopo)
            else:
                st.warning(f"Arquivo não encontrado: {path_escopo.name}. Será omitido.")

        # Adiciona os demais PDFs obrigatórios
        pdfs.extend([termos_filename, disposicoes_gerais_filename, clientes_hygge_filename, contracapa_path])
    else:
        pdfs = [capa_path, pdf_path]

        for produto in produtos:
            # Ignora itens que não geram PDF
            if produto in ['Reunião', 'Urgência', 'Cenário adicional de simulação']:
                continue

            # Caso especial para 'NBR' com 'Cenário adicional' sem 'Aditivo'
            if 'NBR' in produto and 'Cenário adicional' in produtos and 'Aditivo' not in produto:
                path_item = Path(__file__).parent / "PDFs2/Descritivo - Laudo NBR Fast e Aditivo.pdf"
            else:
                path_item = Path(__file__).parent / f"PDFs2/Descritivo - {produto}.pdf"

            if path_item.exists():
                pdfs.append(path_item)
            else:
                st.warning(f"Arquivo não encontrado: {path_item.name}. Será omitido.")

        #pdfs.extend([NBRFast_Termos, NBR_disposicoes, NBR_clientes_hygge, contracapa_path])
        pdfs.extend([NBRFast_Termos, NBR_disposicoes, contracapa_path])
    writer = PdfWriter()

    for pdf in pdfs:
        try:
            reader = PdfReader(open(pdf, 'rb'))
            for i in range(len(reader.pages)):
                writer.add_page(reader.pages[i])
        except:
            st.error(f"Erro ao adicionar o pdf {pdf} ao arquivo. Peça para o seu gestor verificar se os produtos selecionados possuem **descritivo** e **escopo**.") 
            return None

    with open(pdf_path, 'wb') as f_out:
        writer.write(f_out)
        st.success('Etapa 1 de 2 - Proposta gerada com sucesso!')
        
    return pdf_path