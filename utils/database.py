import streamlit as st
from pymongo import MongoClient
from urllib.parse import quote_plus

@st.cache_resource
def get_db_client():
    """Retorna o cliente MongoDB usando cache para otimizar conexões."""
    username = st.secrets['database']['username']
    password = st.secrets['database']['password']
    mongo_uri = f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}@crmhygge.wiafd.mongodb.net/?retryWrites=true&w=majority&appName=CRMHygge"
    return MongoClient(mongo_uri)

def get_collection(collection_name):
    """Retorna uma coleção específica do banco de dados."""
    client = get_db_client()  # Usa o cliente cacheado
    db = client["crm_database"]  # Nome do banco de dados
    return db[collection_name]

