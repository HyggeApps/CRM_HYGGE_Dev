import random
from pymongo import MongoClient
from urllib.parse import quote_plus

def get_db_client():
    username = "crm_hygge"
    password = "BN1hNGf7cdlRGKL5"
    mongo_uri = f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}@crmhygge.wiafd.mongodb.net/?retryWrites=true&w=majority&appName=CRMHygge"
    return MongoClient(mongo_uri)

def get_collection(collection_name):
    client = get_db_client()
    db = client["crm_database"]
    return db[collection_name]

# Conecta à coleção "tarefas"
collection_tarefas = get_collection("tarefas")

def atualizar_titulos():
    # Percorre todas as tarefas
    for tarefa in collection_tarefas.find():
        empresa = tarefa.get("empresa", "")
        titulo = tarefa.get("titulo", "")
        # Gera um hexadecimal aleatório de 4 caracteres
        random_hex = f"{random.randint(0, 0xFFFF):04x}"
        # Novo título: título atual concatenado com o campo "empresa" e o hexadecimal
        novo_titulo = f"{titulo} ({empresa} - {random_hex})"
        
        # Atualiza o documento com o novo título e adiciona o campo "hexa"
        collection_tarefas.update_one(
            {"_id": tarefa["_id"]},
            {"$set": {"titulo": novo_titulo, "hexa": random_hex}}
        )
        print(f"Tarefa {tarefa['_id']} atualizada para: {novo_titulo}")

# Executa a atualização
atualizar_titulos()