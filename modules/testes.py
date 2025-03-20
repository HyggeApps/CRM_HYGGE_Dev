from pymongo import MongoClient # type: ignore
from urllib.parse import quote_plus
import ast

def get_db_client():
    """Retorna o cliente MongoDB usando cache para otimizar conexões."""
    username = "crm_hygge"
    password = "BN1hNGf7cdlRGKL5"
    mongo_uri = f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}@crmhygge.wiafd.mongodb.net/?retryWrites=true&w=majority&appName=CRMHygge"
    return MongoClient(mongo_uri)

def get_collection(collection_name):
    """Retorna uma coleção específica do banco de dados."""
    client = get_db_client()  # Usa o cliente cacheado
    db = client["crm_database"]  # Nome do banco de dados
    return db[collection_name]

collection_produtos = get_collection('produtos')

import re
import ast

# Prefixos que identificam os produtos que queremos combinar
prefix_auditoria = "Auditoria Certificação - "
prefix_certificacao = "Certificação - "

# Consulta os produtos que começam com um dos dois prefixos
filtro = {
    "nome": {
        "$regex": f"^({re.escape(prefix_auditoria)}|{re.escape(prefix_certificacao)})"
    }
}
produtos = list(collection_produtos.find(filtro))

# Agrupa os produtos pela parte do nome que vem após o prefixo
grupos = {}
for prod in produtos:
    nome = prod.get("nome", "")
    if nome.startswith(prefix_auditoria):
        remainder = nome[len(prefix_auditoria):]
    elif nome.startswith(prefix_certificacao):
        remainder = nome[len(prefix_certificacao):]
    else:
        continue

    grupos.setdefault(remainder, []).append(prod)

# Para cada grupo que contenha mais de um produto, cria um novo produto combinado
for remainder, produtos_group in grupos.items():
    # Só combina se houver pelo menos dois produtos (um de cada tipo, por exemplo)
    if len(produtos_group) < 2:
        continue

    total_preco_servico = 0
    total_preco_modelagem = 0
    servicos_adicionais_combinados = {}

    for prod in produtos_group:
        total_preco_servico += prod.get("preco_servico", 0)
        total_preco_modelagem += prod.get("preco_modelagem", 0)

        servicos = prod.get("servicos_adicionais", {})
        # Caso venha como string, tenta converter para dicionário
        if isinstance(servicos, str):
            try:
                servicos = ast.literal_eval(servicos)
            except Exception:
                servicos = {}

        # Soma os valores de cada serviço adicional
        for chave, valor in servicos.items():
            if chave in servicos_adicionais_combinados:
                servicos_adicionais_combinados[chave] += valor
            else:
                servicos_adicionais_combinados[chave] = valor

    # Define o novo nome com base na parte comum (remainder)
    novo_nome = "Auditoria e Certificação - " + remainder

    # Exemplo de definição dos demais campos:
    # Aqui se assume que o "remainder" possui duas partes separadas por " - ",
    # onde a primeira corresponde ao tipo e a última ao tamanho.
    partes = remainder.split(" - ")
    novo_tipo = "Auditoria e Certificação - " + (partes[0] if partes else "")
    novo_tamanho = partes[-1] if len(partes) > 1 else ""

    novo_produto = {
        "nome": novo_nome,
        "categoria": "Certificação",  # Conforme especificado
        "tipo": novo_tipo,
        "tamanho": novo_tamanho,
        "preco_modelagem": total_preco_modelagem,
        "preco_servico": total_preco_servico,
        "servicos_adicionais": servicos_adicionais_combinados
    }

    resultado = collection_produtos.insert_one(novo_produto)
    print(f"Novo produto criado para o grupo '{novo_nome}' com ID: {resultado.inserted_id}")
