import streamlit as st
from utils.database import get_collection
from datetime import datetime, time
import pandas as pd
import datetime as dt
import calendar
import utils

hoje = dt.date.today()  # current date

def filtrar_por_periodo(df, periodo):
    df_filtrado = df.copy()

    if periodo == "Mês atual":
        ano_atual = hoje.year
        mes_atual = hoje.month
        # Primeiro e último dia do mês atual:
        primeiro_dia = dt.date(ano_atual, mes_atual, 1)
        ultimo_dia = dt.date(
            ano_atual, 
            mes_atual, 
            calendar.monthrange(ano_atual, mes_atual)[1]
        )
        df_filtrado = df_filtrado[
            (df_filtrado['data_fechamento'].dt.date >= primeiro_dia) &
            (df_filtrado['data_fechamento'].dt.date <= ultimo_dia)
        ]

    elif periodo == "Próximos 30 dias":
        limite = hoje + dt.timedelta(days=30)
        df_filtrado = df_filtrado[df_filtrado['data_fechamento'].dt.date <= limite]
    
    elif periodo == "Próximos 3 meses":
        limite = hoje + dt.timedelta(days=90)
        df_filtrado = df_filtrado[df_filtrado['data_fechamento'].dt.date <= limite]

    elif periodo == "Próximos 6 meses":
        limite = hoje + dt.timedelta(days=180)
        df_filtrado = df_filtrado[df_filtrado['data_fechamento'].dt.date <= limite]

    elif periodo == "Próximo ano":
        limite = hoje + dt.timedelta(days=365)
        df_filtrado = df_filtrado[df_filtrado['data_fechamento'].dt.date <= limite]

    else:
        # "Todo o período": não filtra nada
        pass

    return df_filtrado

def format_currency(value):
    """
    Formata um valor numérico no padrão brasileiro de moeda:
    Exemplo: 10900.0 -> "R$ 10.900,00"
    """
    return "R$ " + "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")


def gerenciamento_oportunidades(user):
    
    collection_atividades = get_collection("atividades")
    collection_oportunidades = get_collection("oportunidades")
    collection_clientes = get_collection("empresas")
    collection_usuarios = get_collection("usuarios")
    collection_produtos = get_collection("produtos")

    estagios = ["Frio", "Morno", "Quente", "Aguardando projeto", "Aguardando a assinatura","On-hold", "Perdido", "Fechado"]
    
    st.header('💸 Negócios em andamento')
    with st.popover('➕ Cadastrar negócio'):
        st.header("Cadastrar negócio")
        st.write('----')
        
        # Supondo que as coleções e variáveis já estejam definidas:
        # collection_clientes, collection_usuarios, collection_produtos,
        # collection_oportunidades, collection_atividades, user, estagios

        clientes = list(collection_clientes.find({"proprietario": user}, {"_id": 0, "razao_social": 1, "cnpj": 1}))
        usuarios = list(collection_usuarios.find({}, {"_id": 0, "nome": 1, "sobrenome": 1, "email": 1}))
        produtos = list(collection_produtos.find({}, {"_id": 0, "nome": 1, "categoria": 1, "preco": 1, "base_desconto": 1}))

        opcoes_clientes = [f"{c['razao_social']}" for c in clientes]
        opcoes_produtos = [f"{p['nome']}" for p in produtos]

        if not clientes:
            st.warning("Cadastre um cliente antes de criar oportunidades.")
        elif not usuarios or not produtos:
            st.warning("Certifique-se de ter usuários e produtos cadastrados.")
        else:
            with st.form(key="form_cadastro_oportunidade"):
                cliente = st.selectbox("Cliente", options=opcoes_clientes, key="select_cliente_oportunidade")
                nome_opp = st.text_input('Nome da oportunidade', key="nome_oportunidade")
                # Multiselect para permitir a seleção de mais de um produto
                #produtos_selecionados_text = st.multiselect("Produtos", options=opcoes_produtos, key="select_produto_oportunidade")
                total = st.number_input('Valor estimado', key="valor_estimado_oportunidade")
                #estagio = st.selectbox("Estágio", options=estagios, key="select_estagio_oportunidade")
                estagio = 'Aguardando projeto'
                data_fechamento_date = st.date_input("Data de Fechamento (Prevista)", key="input_data_fechamento_oportunidade")
                submit = st.form_submit_button("Cadastrar")
            
                if submit:
                    if cliente:
                        # Buscar o cliente selecionado
                        cliente_selecionado = next((c for c in clientes if f"{c['razao_social']}" == cliente), None)
                        # Buscar os produtos selecionados (mapeia os textos selecionados para os objetos de produtos)
                        #produtos_selecionados_obj = [p for p in produtos if f"{p['nome']}" in produtos_selecionados_text]
            
                        if cliente_selecionado:
                            data_criacao = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
                            data_fechamento_datetime = datetime.combine(data_fechamento_date, time.min)
                            data_fechamento = data_fechamento_datetime.isoformat(timespec='milliseconds') + 'Z'
                            
                            # "produtos" será uma lista com os nomes dos produtos selecionados
                            
                            valor_estimado_formatado = format_currency(total)
                            
                            document = {
                                "cliente": cliente_selecionado["razao_social"],
                                "nome_oportunidade": nome_opp,
                                "proprietario": user,
                                "produtos": '',
                                "valor_estimado": valor_estimado_formatado,
                                "valor_orcamento": '',
                                "estagio": estagio,
                                "data_criacao": data_criacao,
                                "data_fechamento": data_fechamento,
                                "motivo_perda": '',
                                "motivo_ganho": '',
                                "dias_para_fechar": '',
                                "condicoes_pagamento": '',
                                "prazo_execucao": '',
                                "categoria": '',
                                "tipo": '',
                                "tamanho": '',
                                "contatos_selecionados": [],
                                "contato_principal": '',
                                "desconto_solicitado": 20.0,
                                "desconto_aprovado": 20.0,
                                'negocio_fechado': False,
                                'negocio_perdido': False,
                                'aprovacao_gestor': False,
                                'solicitacao_desconto':False

                            }
                            collection_oportunidades.insert_one(document)
            
                            # Criar uma nova atividade informando que a oportunidade foi cadastrada
                            nova_atividade = {
                                "atividade_id": str(datetime.now().timestamp()),  
                                "tipo_atividade": "Observação",
                                "status": "Registrado",
                                "titulo": f"Oportunidade '{nome_opp}' criada",
                                "empresa": cliente_selecionado["razao_social"],
                                "descricao": f"O vendedor {user} criou a oportunidade '{nome_opp}' com valor estimado de: {valor_estimado_formatado}.",
                                "data_execucao_atividade": datetime.today().strftime("%Y-%m-%d"),
                                "data_criacao_atividade": datetime.today().strftime("%Y-%m-%d")
                            }
            
                            collection_atividades.insert_one(nova_atividade)
                            st.success("Oportunidade e atividade cadastradas com sucesso!")
                            st.rerun()
                        else:
                            st.error("Erro ao localizar as entidades selecionadas. Tente novamente.")
                    else:
                        st.error("Preencha todos os campos obrigatórios.")


    # Buscar oportunidades no banco
    oportunidades = list(
        collection_oportunidades.find(
            {"proprietario": user},  # <─ ADICIONE ESTA CLÁUSULA PARA FILTRAR
            {"_id": 0, "cliente": 1, "nome_oportunidade": 1,"valor_orcamento": 1, "valor_estimado": 1,
            "data_criacao": 1, "data_fechamento": 1, "estagio": 1, "produtos": 1}
        )
    )
    if not oportunidades:
        st.warning("Nenhuma oportunidade encontrada.")
        return
    
    df_oportunidades = pd.DataFrame(oportunidades)
    df_oportunidades['data_criacao'] = pd.to_datetime(df_oportunidades['data_criacao'], errors='coerce')
    df_oportunidades["data_fechamento"] = pd.to_datetime(df_oportunidades["data_fechamento"], errors="coerce")
    

    # Opções de períodos
    opcoes_periodo = [
        "Mês atual",
        "Próximos 30 dias",
        "Próximos 3 meses",
        "Próximos 6 meses",
        "Próximo ano",
        "Todo o período"
    ]

    periodo_escolhido = st.selectbox("Filtrar por previsão de fechamento:", opcoes_periodo, index=4)
    df_oportunidades_filtrado = filtrar_por_periodo(df_oportunidades, periodo_escolhido)
    filtro_nome = st.text_input("Filtrar por nome da oportunidade (parcial ou completo):")

    # Se o usuário digitar algo, filtramos
    if filtro_nome.strip():
        df_oportunidades_filtrado = df_oportunidades_filtrado[
            df_oportunidades_filtrado["nome_oportunidade"]
                .str.contains(filtro_nome, case=False, na=False)
        ]

    # Mapeamento de ícones para cada estágio
    icones_estagios = {
        "Aguardando projeto": "⏳",
        "Frio": "❄️",
        "Morno": "🌥️",
        "Quente": "🔥",
        "Aguardando a assinatura": "✍️"
    }

    css = """
        <style>
            /* Define um tamanho máximo e rolagem para o conteúdo dos expanders */
            div[data-testid="stExpander"] div[role="group"] {
                max-height: 400px;
                overflow-y: auto;
            }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)
    # Criar colunas para exibição por estágio

    estagios_disponiveis = ["Aguardando projeto", "Frio", "Morno", "Quente", "Aguardando a assinatura"]
    colunas_estagios = st.columns(len(estagios_disponiveis))
    # Seção de oportunidades "ativas"
    for i, estagio in enumerate(estagios_disponiveis):
        with colunas_estagios[i]:
            st.subheader(f"{icones_estagios[estagio]} {estagio}")  # Ícone dinâmico
            
            # Filtra as oportunidades daquele estágio
            df_filtrado = df_oportunidades_filtrado[df_oportunidades_filtrado["estagio"] == estagio]
            
            # Calcula o total da categoria
            total_valor = 0
            for _, row_valor in df_filtrado.iterrows():
                if row_valor['valor_orcamento'] != '': valor_str = str(row_valor['valor_orcamento']).replace("R$", "").replace(".", "").replace(",", ".").strip()
                else: valor_str = str(row_valor['valor_estimado']).replace("R$", "").replace(".", "").replace(",", ".").strip()
                try:
                    total_valor += float(valor_str)
                except ValueError:
                    pass
            
            # Mostra o total acima do expander
            st.write(f"💵 **Total: R$ {total_valor:,.2f}**")
            
            # Expander para ver detalhes
            with st.expander("📋 Ver mais..."):
                st.write('----')
                
                if not df_filtrado.empty:
                    for i, (idx, row) in enumerate(df_filtrado.iterrows()):
                        st.subheader(f"{row['nome_oportunidade']}")
                        if row['valor_orcamento'] != '':
                            st.write(f"**💲 {row['valor_orcamento']}**")
                        else:
                            st.write(f"**💲 {row['valor_estimado']}**")
                        
                        if pd.notnull(row["data_criacao"]):
                            data_criacao_str = row["data_criacao"].strftime("%d/%m/%Y")
                        else:
                            data_criacao_str = "Data não informada"

                        if pd.notnull(row["data_fechamento"]):
                            data_fechamento_str = row["data_fechamento"].strftime("%d/%m/%Y")
                        else:
                            data_fechamento_str = "Data não informada"

                        st.write(f'📆 Criação: **{data_criacao_str}**')
                        st.write(f"📆 Previsão de fechamento: **{data_fechamento_str}**")
                        
                        st.multiselect(
                            "**Produtos:**", 
                            row['produtos'], 
                            default=row['produtos'], 
                            disabled=True, 
                            key=f'produtos_{row["nome_oportunidade"]}_{i}'
                        )

                        novo_estagio = st.selectbox(
                            "Alterar estágio",
                            options=estagios_disponiveis + ['On-hold','Perdido','Fechado'],
                            index=estagios_disponiveis.index(row['estagio']),
                            key=f"select_{row['nome_oportunidade']}_{i}"
                        )

                        if novo_estagio != row['estagio']:
                            collection_oportunidades.update_one(
                                {"nome_oportunidade": row['nome_oportunidade']},
                                {"$set": {"estagio": novo_estagio}}
                            )
                            st.success(f"Estágio alterado para {novo_estagio}")
                            st.rerun()  # Atualiza a página após a mudança

                        # ──────────────────────────────────────────────────────────────────────────
                        # Exemplo de "editar oportunidade" via expander
                        # ──────────────────────────────────────────────────────────────────────────
                        with st.popover("✏️ Editar oportunidade"):
                            # Aqui você pode permitir editar campos específicos,
                            # como nome, valor estimado, datas, etc.
                            novo_nome = st.text_input("Nome da oportunidade", value=row["nome_oportunidade"], key=f"nome_{row['nome_oportunidade']}_{i}")  # Unique key)
                            #novo_valor = st.text_input("Valor estimado", value=str(row["valor_estimado"]),key=f"valor_{row['nome_oportunidade']}")
                            nova_data_fechamento_date = st.date_input(
                                "Data de fechamento",
                                value=row["data_fechamento"] if isinstance(row["data_fechamento"], dt.date) 
                                                            else dt.date.today(),
                                key=f"dataFechamento_{row['nome_oportunidade']}_{i}"
                            )
                            
                            nova_data_fechamento_datetime = datetime.combine(nova_data_fechamento_date, time.min)
                            nova_data_fechamento = nova_data_fechamento_datetime.isoformat(timespec='milliseconds') + 'Z'
                            
                            # Button to save changes
                            if st.button("Salvar alterações", key=f"salvar_{row['nome_oportunidade']}_{i}"):
                                update_fields = {
                                    "nome_oportunidade": novo_nome,
                                    #"valor_estimado": novo_valor,
                                    "data_fechamento": nova_data_fechamento
                                }
                                result = collection_oportunidades.update_one(
                                    {"nome_oportunidade": row['nome_oportunidade']},
                                    {"$set": update_fields}
                                )
                                if result.modified_count:
                                    # Criar uma nova atividade informando que a tarefa foi concluída
                                    cliente_doc = collection_clientes.find_one({"razao_social": row["cliente"]})
                                    if cliente_doc is not None:
                                        cnpj_cliente = cliente_doc["cnpj"]
                                    else:
                                        cnpj_cliente = "Não encontrado"
                                    nova_atividade = {
                                        "atividade_id": str(datetime.now().timestamp()),  
                                        "tipo_atividade": "Observação",
                                        "status": "Registrado",
                                        "titulo": f"Oportunidade '{nome_opp}' atualizada",
                                        "empresa": row['cliente'],
                                        "descricao": f"O vendedor {user} atualizou a oportunidade '{nome_opp}: nova data de fechamento: {nova_data_fechamento}'.",
                                        "data_execucao_atividade": datetime.today().strftime("%Y-%m-%d"),
                                        "data_criacao_atividade": datetime.today().strftime("%Y-%m-%d")
                                    }

                                    # Inserir no banco de atividades
                                    collection_atividades.insert_one(nova_atividade)
                                    st.success(f"Oportunidade '{novo_nome}' atualizada com sucesso!")
                                else:
                                    st.warning("Nenhum documento foi atualizado. Verifique se o filtro está correto ou se não houve mudança.")
                                st.rerun()

                        st.write("----")
                else:
                    st.info("Nenhuma oportunidade.")

    # Separador visual
    st.write('----')
    st.header('💸 Negócios encerrados/On-Hold')

    # Seção de oportunidades "encerradas"
    col1, col2, col3 = st.columns(3)
    estagios_encerrados = {
        "Perdido": {"icone": "❌", "titulo": "Perdidas"},
        "On-hold": {"icone": "⏸️", "titulo": "On-Hold"},
        "Fechado": {"icone": "✅", "titulo": "Fechadas"}
    }
    colunas_encerradas = [col1, col2, col3]

    # Iterar sobre os estágios encerrados
    for col, (estagio, info) in zip(colunas_encerradas, estagios_encerrados.items()):
        with col:
            st.subheader(f"{info['icone']} {info['titulo']}")

            # Filtra as oportunidades daquele estágio
            df_filtrado = df_oportunidades_filtrado[df_oportunidades_filtrado["estagio"] == estagio]

            # Calcula o total da categoria
            total_valor = 0
            for _, row_valor in df_filtrado.iterrows():
                if row_valor['valor_orcamento'] != '': valor_str = str(row_valor['valor_orcamento']).replace("R$", "").replace(".", "").replace(",", ".").strip()
                else: valor_str = str(row_valor['valor_estimado']).replace("R$", "").replace(".", "").replace(",", ".").strip()
                try:
                    total_valor += float(valor_str)
                except ValueError:
                    pass

            # Mostra o total acima do expander
            st.write(f"💵 **Total: R$ {total_valor:,.2f}**")

            # Expander para ver detalhes das propostas encerradas
            with st.expander(f"📋 Propostas {info['titulo'].lower()}"):
                st.write('----')
                
                if not df_filtrado.empty:
                    for i, (_, row) in enumerate(df_filtrado.iterrows()):
                        st.subheader(f"{row['nome_oportunidade']}")
                        st.write(f"**💲 {row['valor_estimado']}**")
                        
                        # Formatando a data de criação
                        if pd.notnull(row["data_criacao"]):
                            data_criacao_str = row["data_criacao"].strftime("%d/%m/%Y")
                        else:
                            data_criacao_str = "Data não informada"

                        # Formatando a data de fechamento
                        if pd.notnull(row["data_fechamento"]):
                            data_fechamento_str = row["data_fechamento"].strftime("%d/%m/%Y")
                        else:
                            data_fechamento_str = "Data não informada"

                        st.write(f'📆 Criação: **{data_criacao_str}**')
                        st.write(f"📆 Previsão de fechamento: **{data_fechamento_str}**")
                        
                        # Atribuindo uma chave única usando o índice
                        st.multiselect(
                            "**Produtos:**", 
                            row['produtos'], 
                            default=row['produtos'], 
                            disabled=True, 
                            key=f"produtos_{row['nome_oportunidade']}_{i}"
                        )

                        if row['estagio'] == 'On-hold':
                            # Criar selectbox para alterar o estágio com chave única
                            novo_estagio = st.selectbox(
                                "Alterar estágio",
                                options=list(estagios_encerrados.keys()) + ['Aguardando projeto','Frio', 'Morno','Quente','Aguardando assinatura'],
                                index=list(estagios_encerrados.keys()).index(row['estagio']),
                                key=f"select_{row['nome_oportunidade']}_encerrado_{i}"
                            )

                            # Se o estágio for alterado, atualizar no MongoDB
                            if novo_estagio != row['estagio']:
                                collection_oportunidades.update_one(
                                    {"nome_oportunidade": row['nome_oportunidade']},
                                    {"$set": {"estagio": novo_estagio}}
                                )
                                st.success(f"Estágio alterado para {novo_estagio}")
                                st.rerun()  # Atualiza a página após a mudança
                            # ──────────────────────────────────────────────────────────────────────────
                            # Exemplo de "editar oportunidade" via expander
                            # ──────────────────────────────────────────────────────────────────────────

                            with st.popover("✏️ Editar oportunidade"):
                                # Aqui você pode permitir editar campos específicos,
                                # como nome, valor estimado, datas, etc.
                                novo_nome = st.text_input("Nome da oportunidade", value=row["nome_oportunidade"], key=f"nome_{row['nome_oportunidade']}")  # Unique key)
                                nova_data_fechamento_date = st.date_input(
                                "Data de fechamento",
                                value=row["data_fechamento"] if isinstance(row["data_fechamento"], dt.date) 
                                                            else dt.date.today(),
                                key=f"dataFechamento_{row['nome_oportunidade']}"
                                )
                                
                                nova_data_fechamento_datetime = datetime.combine(nova_data_fechamento_date, time.min)
                                nova_data_fechamento = nova_data_fechamento_datetime.isoformat(timespec='milliseconds') + 'Z'
                                
                                # Button to save changes
                                if st.button("Salvar alterações", key=f"salvar_{row['nome_oportunidade']}"):
                                    update_fields = {
                                        "nome_oportunidade": novo_nome,
                                        "data_fechamento": nova_data_fechamento
                                    }
                                    result = collection_oportunidades.update_one(
                                        {"nome_oportunidade": row['nome_oportunidade']},
                                        {"$set": update_fields}
                                    )
                                    if result.modified_count:
                                        # Criar uma nova atividade informando que a tarefa foi concluída
                                        nova_atividade = {
                                            "atividade_id": str(datetime.now().timestamp()),  
                                            "tipo_atividade": "Observação",
                                            "status": "Registrado",
                                            "titulo": f"Oportunidade '{novo_nome}' atualizada",
                                            "empresa": row["cliente"],
                                            "descricao": f"O vendedor {user} atualizou a oportunidade '{novo_nome}': nova data de fechamento prevista: {nova_data_fechamento}'.",
                                            "data_execucao_atividade": datetime.today().strftime("%Y-%m-%d"),
                                            "data_criacao_atividade": datetime.today().strftime("%Y-%m-%d")
                                        }

                                        # Inserir no banco de atividades
                                        collection_atividades.insert_one(nova_atividade)
                                        st.success(f"Oportunidade '{novo_nome}' atualizada com sucesso!")
                                    else:
                                        st.warning("Nenhum documento foi atualizado. Verifique se o filtro está correto ou se não houve mudança.")
                                    st.rerun()

                        st.write("---")

                else:
                    st.info(f"Nenhuma oportunidade.")





