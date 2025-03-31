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

# código que irá conferir se existe empresa_id na atividade, se não existir, adicionar com base no nome da 'empresa' que será comparada com a 'razao_social' do banco;

collection_empresas = get_collection("empresas")
collection_tarefas = get_collection("tarefas")

# percorrer as empresas e adicionar 'empresa_id' quando não houver com base na comparação de 'empresa' e 'razao_social'
empresas = collection_empresas.find()
for empresa in empresas:
    razao_social = empresa['razao_social']
    empresa_id = empresa['_id']

    # Verifica se a atividade já possui o 'empresa_id' correspondente
    atividades = collection_tarefas.find({"empresa_id": {"$exists": False}})
    for atividade in atividades:
        if atividade['empresa'] == razao_social:
            # Atualiza a atividade com o 'empresa_id'
            collection_tarefas.update_one(
                {"_id": atividade["_id"]},
                {"$set": {"empresa_id": empresa_id}}
            )