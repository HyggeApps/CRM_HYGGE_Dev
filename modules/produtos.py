import streamlit as st
from utils.database import get_collection
from bson import ObjectId
import pandas as pd


def gerenciamento_produtos():
    collection = get_collection("produtos")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Produto", "Editar Produto", "Remover Produto"])
    
    # Aba: Cadastrar Produto
    with tab1:
        st.subheader("Cadastrar Produto")
        
        # Linha 1: Categoria, Tipo e Tamanho/Quantidade
        col_cat, col_tipo, col_tam = st.columns(3)
        with col_cat:
            categorias_existentes = collection.distinct("categoria")
            opcoes_categoria = [''] + categorias_existentes + ["-- Novo --"]
            categoria = st.selectbox("Categoria: *", opcoes_categoria, key="cad_categoria")
            if categoria == "-- Novo --":
                categoria = st.text_input("Digite a nova categoria:", key="cad_categoria_novo")
        with col_tipo:
            tipos_existentes = []
            if categoria:
                tipos_existentes = collection.distinct("tipo", {"categoria": categoria})
            opcoes_tipo = [''] + tipos_existentes + ["-- Novo --"]
            tipo = st.selectbox("Tipo do empreendimento: *", opcoes_tipo, key="cad_tipo")
            if tipo == "-- Novo --":
                tipo = st.text_input("Digite o novo tipo para a categoria escolhida:", key="cad_tipo_novo")
        with col_tam:
            tamanhos_existentes = []
            if categoria and tipo:
                tamanhos_existentes = collection.distinct("tamanho", {"categoria": categoria, "tipo": tipo})
            opcoes_tamanho = [''] + tamanhos_existentes + ["-- Novo --"]
            tamanho = st.selectbox("Tamanho/Quantidade: *", opcoes_tamanho, key="cad_tamanho")
            if tamanho == "-- Novo --":
                tamanho = st.text_input("Digite o novo tamanho/quantidade para o tipo escolhido:", key="cad_tamanho_novo")
        
        # Linha 2: Preços e Nome do Produto
        col_preco_mod, col_preco_serv, col_nome = st.columns(3)
        with col_preco_mod:
            preco_modelagem = st.number_input("Preço Modelagem", min_value=0.0, step=0.01, value=150.0, key="cad_preco_modelagem")
        with col_preco_serv:
            preco_servico = st.number_input("Preço Serviço", min_value=0.0, step=0.01, value=200.0, key="cad_preco_servico")
        with col_nome:
            nome_gerado = f"{tipo} - {tamanho}" if tipo and tamanho else ""
            nome_produto = st.text_input("Nome do Produto", value=nome_gerado, key="cad_nome")
        
        # Linha 3: Serviços Adicionais
        st.markdown("### Serviços Adicionais")
        servicos_adicionais = {}
        
        # Serviços pré-definidos
        servicos_opcoes = ['Reunião', 'Urgência', 'Cenário extra']
        servicos_selecionados = st.multiselect("Selecione os serviços adicionais desejados", servicos_opcoes, key="cad_servicos")
        for servico in servicos_selecionados:
            valor = st.number_input(f"Valor para {servico}:", min_value=0, step=1, value=0, key=f"valor_{servico}")
            servicos_adicionais[servico] = valor
        
        # Serviços personalizados (vários)
        if "custom_services" not in st.session_state:
            st.session_state.custom_services = []
        
        with st.expander("Adicionar serviços personalizados"):
            if st.button("Adicionar novo serviço personalizado", key="add_custom_service"):
                st.session_state.custom_services.append({"nome": "", "valor": 0})
            # Para cada serviço personalizado, use colunas para organizar os campos
            for idx, service in enumerate(st.session_state.custom_services):
                col_custom1, col_custom2 = st.columns(2)
                with col_custom1:
                    nome_custom = st.text_input(f"Nome do serviço personalizado {idx+1}:", key=f"custom_nome_{idx}")
                with col_custom2:
                    valor_custom = st.number_input(f"Valor para o serviço personalizado {idx+1}:", min_value=0, step=1, key=f"custom_valor_{idx}")
                st.session_state.custom_services[idx]["nome"] = nome_custom
                st.session_state.custom_services[idx]["valor"] = valor_custom
                if nome_custom:
                    servicos_adicionais[nome_custom] = valor_custom
        
        # Linha final: Botão de Cadastro
        if st.button("Cadastrar Produto", key="cad_submit"):
            if categoria and tipo and tamanho and nome_produto:
                # Verifica se o produto já existe
                existing = collection.find_one({"nome": nome_produto})
                if existing:
                    st.error("Produto já cadastrado com este nome!")
                else:
                    document = {
                        "nome": nome_produto,
                        "categoria": categoria,
                        "tipo": tipo,
                        "tamanho": tamanho,
                        "preco_modelagem": preco_modelagem,
                        "preco_servico": preco_servico,
                        "servicos_adicionais": servicos_adicionais
                    }
                    collection.insert_one(document)
                    st.success("Produto cadastrado com sucesso!")
            else:
                st.error("Preencha todos os campos obrigatórios.")
    
    # --- Aba: Editar Produto (Tabela com st.data_editor e filtros em colunas) ---
    with tab2:
        
        # Consulta todos os produtos e converte para DataFrame
        produtos = list(collection.find({}))
        if not produtos:
            st.info("Nenhum produto cadastrado.")
        else:
            import pandas as pd
            from bson import ObjectId
            
            df = pd.DataFrame(produtos)
            # Converte _id para string
            df['_id'] = df['_id'].astype(str)
            # Cria uma coluna separada para o _id e a oculta da edição
            df["doc_id"] = df["_id"]
            df.drop(columns=["_id"], inplace=True)
            
            # Obtém os valores únicos para os filtros
            nomes = sorted(df["nome"].unique().tolist())
            categorias = sorted(df["categoria"].unique().tolist())
            tipos = sorted(df["tipo"].unique().tolist())
            tamanhos = sorted(df["tamanho"].unique().tolist())
            
            st.markdown("### Filtros")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                filter_nome = st.selectbox("Filtrar por Nome:", options=["Todos"] + nomes, key="filter_nome")
            with col2:
                filter_categoria = st.selectbox("Filtrar por Categoria:", options=["Todas"] + categorias, key="filter_categoria")
            with col3:
                filter_tipo = st.selectbox("Filtrar por Tipo:", options=["Todos"] + tipos, key="filter_tipo")
            with col4:
                filter_tamanho = st.selectbox("Filtrar por Tamanho:", options=["Todos"] + tamanhos, key="filter_tamanho")
            
            # Aplica os filtros ao DataFrame
            filtered_df = df.copy()
            if filter_nome != "Todos":
                filtered_df = filtered_df[filtered_df["nome"] == filter_nome]
            if filter_categoria != "Todas":
                filtered_df = filtered_df[filtered_df["categoria"] == filter_categoria]
            if filter_tipo != "Todos":
                filtered_df = filtered_df[filtered_df["tipo"] == filter_tipo]
            if filter_tamanho != "Todos":
                filtered_df = filtered_df[filtered_df["tamanho"] == filter_tamanho]
            
            st.write("Edite os produtos abaixo:")
            # Exibe a tabela editável ocultando o índice (que agora contém o doc_id)
            edited_df = st.data_editor(filtered_df, num_rows="dynamic", use_container_width=True, hide_index=True)
            
            if st.button("Salvar Alterações"):
                for _, row in edited_df.iterrows():
                    product_id = row["doc_id"]
                    update_data = row.to_dict()
                    update_data.pop("doc_id", None)
                    collection.update_one({"_id": ObjectId(product_id)}, {"$set": update_data})
                st.success("Alterações salvas com sucesso!")

    
    # Aba: Remover Produto
    with tab3:
        st.subheader("Remover Produto")
        
        # Buscar todos os produtos cadastrados
        produtos = list(collection.find())
        
        if produtos:
            # Criar um dicionário para mapear o texto exibido à _id do produto
            produtos_dict = {}
            for produto in produtos:
                produto_id = produto["_id"]
                produto_categoria = produto.get("categoria", "Sem categoria")
                produto_nome = produto.get("nome", "Sem nome")
                display_text = f"{produto_categoria} - {produto_nome}"
                produtos_dict[display_text] = produto_id
            
            # Exibir a lista suspensa com os produtos
            produto_selecionado = st.selectbox("Selecione o produto para remover", list(produtos_dict.keys()))
            
            if st.button("Remover Produto", key="remove_submit"):
                selected_id = produtos_dict[produto_selecionado]
                try:
                    result = collection.delete_one({"_id": selected_id})
                    if result.deleted_count > 0:
                        st.success(f"Produto '{produto_selecionado}' removido com sucesso!")
                    else:
                        st.error("Nenhum produto encontrado para remoção.")
                except Exception as e:
                    st.error(f"Ocorreu um erro ao remover o produto: {e}")
        else:
            st.info("Nenhum produto cadastrado para remover.")