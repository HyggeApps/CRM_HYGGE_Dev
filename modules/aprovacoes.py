import streamlit as st
from utils.database import get_collection
import pandas as pd
import datetime as dt
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor, wait

@st.fragment
def gerenciamento_aprovacoes():
    # Obter as coleções
    col_oportunidades = get_collection("oportunidades")
    col_aprovacoes = get_collection("aprovacoes")
    
    # Buscar somente oportunidades com solicitação de desconto em aberto
    oportunidades = list(col_oportunidades.find({
        "solicitacao_desconto": True,
        "aprovacao_gestor": False
    }))
    
    if not oportunidades:
        st.info("Não há solicitações de desconto em aberto.")
        return
    
    # Criar DataFrame a partir das oportunidades
    df = pd.DataFrame(oportunidades)
    
    # Salvar a lista de _id para usar no update (não será exibido)
    id_mapping = df['_id'].tolist()
    
    # Converter _id para string e selecionar somente as colunas relevantes
    df['_id'] = df['_id'].astype(str)
    df_display = df[['cliente', 'nome_oportunidade', 'proprietario', 'desconto_solicitado', 'aprovacao_gestor']].copy()
    
    # Renomear as colunas para inserir a legenda diretamente
    df_display.rename(columns={
        'cliente': 'Empresa',
        'nome_oportunidade': 'Negócio',
        'proprietario': 'Vendedor',
        'desconto_solicitado': 'Desconto Solicitado',
        'aprovacao_gestor': 'Aprovação do Gestor'
    }, inplace=True)
    
    st.write("### Solicitações de Desconto em aberto")
    
    # Exibir o DataFrame com st.data_editor sem permitir adição de novas linhas
    edited_df = st.data_editor(df_display, num_rows="fixed")
    
    def process_approval(oportunidade_id_str, row):
        # Atualiza a oportunidade em uma única operação
        col_oportunidades.update_one(
            {"_id": ObjectId(oportunidade_id_str)},
            {"$set": {
                "aprovacao_gestor": True,
                "solicitacao_desconto": False,
                "desconto_aprovado": row['Desconto Solicitado']
            }}
        )
        # Registra a aprovação na coleção 'aprovacoes'
        aprovacao = {
            "oportunidade_id": oportunidade_id_str,
            "empresa": row['Empresa'],
            "nome_oportunidade": row['Negócio'],
            "vendedor": row['Vendedor'],
            "desconto_solicitado": row['Desconto Solicitado'],
            "aprovado_por": "gestor",  # Personalize para capturar o usuário logado
            "data_aprovacao": dt.datetime.now()
        }
        col_aprovacoes.insert_one(aprovacao)
    
    if st.button("Salvar Aprovações"):
        tasks = []
        with ThreadPoolExecutor() as executor:
            for idx in range(len(edited_df)):
                if edited_df.iloc[idx]['Aprovação do Gestor'] == True:
                    oportunidade_id_str = id_mapping[idx]
                    row = edited_df.iloc[idx]
                    tasks.append(executor.submit(process_approval, oportunidade_id_str, row))
            wait(tasks)
        st.success("Aprovações salvas com sucesso!")
