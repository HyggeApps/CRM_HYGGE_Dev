import pandas as pd

import utils.database as db

def criar_tabela_excel_produtos():
    """Consulta a coleção 'produtos' no banco de dados e cria uma tabela Excel com os dados."""
    # Consultando a collection_produtos e obtendo todos os documentos
    produtos_cursor = db.get_collection('produtos').find()
    produtos_lista = list(produtos_cursor)
    
    # Extraindo os campos desejados de cada produto
    dados = []
    for prod in produtos_lista:
        dados.append({
            'Nome': prod.get('nome', ''),
            'Categoria': prod.get('categoria', ''),
            'Tipo': prod.get('tipo', ''),
            'Tamanho': prod.get('tamanho', ''),
            'Preço Modelagem': prod.get('preco_modelagem', 0),
            'Preço Serviço': prod.get('preco_servico', 0),
            'Serviços Adicionais': prod.get('servicos_adicionais', ''),
            'Escopo': ', '.join(prod.get('escopo', [])) if isinstance(prod.get('escopo', []), list) else prod.get('escopo', '')
        })
    
    # Criando o DataFrame com os dados extraídos
    df_produtos = pd.DataFrame(dados)
    
    # Definindo o caminho do arquivo Excel
    caminho_arquivo = 'produtos.xlsx'
    # Salvando o DataFrame em um arquivo Excel utilizando o openpyxl
    df_produtos.to_excel(caminho_arquivo, engine='openpyxl', index=False)
    
    print(f'Tabela de produtos criada em: {caminho_arquivo}')

criar_tabela_excel_produtos()