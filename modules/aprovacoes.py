import streamlit as st
from utils.database import get_collection
import pandas as pd
import datetime as dt
from bson import ObjectId

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
    
    # Converter _id para string (se necessário) e selecionar somente as colunas relevantes
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
    
    if st.button("Salvar Aprovações"):
        # Iterar pelas linhas do DataFrame editado
        for idx in range(len(edited_df)):
            # Se o campo de aprovação foi marcado (True) na edição, atualiza a oportunidade e registra a aprovação
            if edited_df.iloc[idx]['Aprovação do Gestor'] == True:
                oportunidade_id_str = id_mapping[idx]
                # Atualiza a oportunidade para aprovar o desconto
                col_oportunidades.update_one(
                    {"_id": ObjectId(oportunidade_id_str)},
                    {"$set": {"aprovacao_gestor": True}}
                )
                col_oportunidades.update_one(
                    {"_id": ObjectId(oportunidade_id_str)},
                    {"$set": {"solicitacao_desconto": False}}
                )
                col_oportunidades.update_one(
                    {"_id": ObjectId(oportunidade_id_str)},
                    {"$set": {"desconto_aprovado": col_oportunidades.find_one({"_id": ObjectId(oportunidade_id_str)})['desconto_solicitado']}}
                )
                # Insere o registro de aprovação na coleção 'aprovacoes'
                aprovacao = {
                    "oportunidade_id": oportunidade_id_str,
                    "empresa": edited_df.iloc[idx]['Empresa'],
                    "nome_oportunidade": edited_df.iloc[idx]['Negócio'],
                    "vendedor": edited_df.iloc[idx]['Vendedor'],
                    "desconto_solicitado": edited_df.iloc[idx]['Desconto Solicitado'],
                    "aprovado_por": "gestor",  # Personalize para capturar o usuário logado
                    "data_aprovacao": dt.datetime.now()
                }
                col_aprovacoes.insert_one(aprovacao)
        st.success("Aprovações salvas com sucesso!")
