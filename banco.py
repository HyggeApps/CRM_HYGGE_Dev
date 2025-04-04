import utils.database as db

# para todas as empresas no collection_empresas criar o campo "empresa_ativa" com valor True

collection_empresas = db.get_collection("empresas")

# Se dentre as opções de produto_interesse houver 'NBR Fast' duplicado, remover uma das opções

