import utils.database as db
collection_empresas = db.get_collection("empresas")
# adicionar o campo telefone_fixo para todas as empresas
collection_empresas.update_many(
    {},  # Seleciona todas as empresas
    {"$set": {"telefone_fixo": ""}}  # Adiciona o campo telefone_fixo com valor vazio
)
