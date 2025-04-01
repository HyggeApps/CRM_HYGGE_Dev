import streamlit as st
import datetime
import utils.database as db

def infos_empresa(empresa_obj, collection_empresas, collection_usuarios, user, admin):
    # Permite edição se o user for o proprietário da empresa ou se for admin
    editable = admin or (empresa_obj.get("proprietario", "") == user)

    collection_cidades = db.get_collection("cidades")
    collection_ufs = db.get_collection("ufs")
    cidades_options = sorted(collection_cidades.distinct("cidade"))
    ufs_options = sorted(collection_ufs.distinct("uf"))
    cidades_options = [""] + cidades_options
    ufs_options = [""] + ufs_options

    razao_social = st.text_input("Razão Social", 
                                  value=empresa_obj.get("razao_social", ""), 
                                  disabled=not editable, 
                                  key="empresa_razao_social")
    col1, col2, col3 = st.columns(3)
    with col1:
        usuarios_options = sorted(
            set(
            f"{usuario.get('nome', '').strip()} {usuario.get('sobrenome', '').strip()}"
            for usuario in collection_usuarios.find({})
            )
        )
        usuarios_options = [""] + usuarios_options
        proprietario = st.selectbox(
            "Proprietário",
            usuarios_options,
            index=usuarios_options.index(empresa_obj.get("proprietario", "")) 
              if empresa_obj.get("proprietario", "") in usuarios_options else 0,
            disabled=not editable,
            key="empresa_proprietario"
        )
        cidade = st.selectbox(
            "Cidade",
            cidades_options,
            index=cidades_options.index(empresa_obj.get("cidade", "")) if empresa_obj.get("cidade", "") in cidades_options else 0,
            disabled=not editable,
            key="empresa_cidade"
        )
        uf = st.selectbox(
            "UF",
            ufs_options,
            index=ufs_options.index(empresa_obj.get("uf", "")) if empresa_obj.get("uf", "") in ufs_options else 0,
            disabled=not editable,
            key="empresa_uf"
        )
        ultima_atividade = st.text_input("Última Atividade", 
                                         value=empresa_obj.get("ultima_atividade", ""), 
                                         disabled=not editable, 
                                         key="empresa_ultima_atividade")
        site = st.text_input("Site", 
                             value=empresa_obj.get("site", ""), 
                             disabled=not editable, 
                             key="empresa_site")
        
    with col2:
        data_criacao = st.text_input("Data de Criação", 
                                     value=empresa_obj.get("data_criacao", ""), 
                                     disabled=not editable, 
                                     key="empresa_data_criacao")
        setores_options = sorted(collection_empresas.distinct("setor"))
        if not "" in setores_options:
            setores_options = [""] + setores_options
        setor = st.selectbox(
            "Setor",
            setores_options,
            index=setores_options.index(empresa_obj.get("setor", "")) if empresa_obj.get("setor", "") in setores_options else 0,
            disabled=not editable,
            key="empresa_setor"
        )
        grau_cliente_options = ["Lead", "Lead qualificado", "Oportunidade", "Cliente"]
        grau_cliente = st.selectbox(
            "Grau Cliente",
            grau_cliente_options,
            index=grau_cliente_options.index(empresa_obj.get("grau_cliente", ""))
              if empresa_obj.get("grau_cliente", "") in grau_cliente_options else 0,
            disabled=not editable,
            key="empresa_grau_cliente"
        )
        tamanho_empresa_options = ["","Tier 1", "Tier 2", "Tier 3", "Tier 4"]
        tamanho_empresa = st.multiselect(
            "Tamanho Empresa",
            options=tamanho_empresa_options,
            default=empresa_obj.get("tamanho_empresa", []),
            disabled=not editable,
            key="empresa_tamanho_empresa"
        )

        produto_interesse_options = sorted(collection_empresas.distinct("produto_interesse"))
        if "" not in produto_interesse_options:
            produto_interesse_options = [""] + produto_interesse_options
        produto_interesse = st.multiselect("Produto Interesse",
                           options=produto_interesse_options,
                           default=empresa_obj.get("produto_interesse", []),
                           disabled=not editable,
                           key="empresa_produto_interesse")
        
    with col3:
        pais = st.text_input("País", 
                             value=empresa_obj.get("pais", ""), 
                             disabled=not editable, 
                             key="empresa_pais")
        endereco = st.text_input("Endereço", 
                                 value=empresa_obj.get("endereco", ""), 
                                 disabled=not editable, 
                                 key="empresa_endereco")
        cnpj = st.text_input("CNPJ", 
                             value=empresa_obj.get("cnpj", ""), 
                             disabled=not editable, 
                             key="empresa_cnpj")
        cep = st.text_input("CEP", 
                            value=empresa_obj.get("cep", ""), 
                            disabled=not editable, 
                            key="empresa_cep")

    if editable:
        if st.button("Salvar alterações", key="empresa_salvar_alteracoes"):
            updated_data = {
                "razao_social": razao_social,
                "proprietario": proprietario,
                "cidade": cidade,
                "uf": uf,
                "ultima_atividade": ultima_atividade,
                "site": site,
                "data_criacao": data_criacao,
                "setor": setor,
                "grau_cliente": grau_cliente,
                "tamanho_empresa": [item.strip() for item in tamanho_empresa] if tamanho_empresa else [],
                "produto_interesse": [item.strip() for item in produto_interesse] if produto_interesse else [],
                "pais": pais,
                "endereco": endereco,
                "cnpj": cnpj,
                "cep": cep
            }
            result = collection_empresas.update_one({"_id": empresa_obj["_id"]}, {"$set": updated_data})
            if result.modified_count:
                st.success("Empresa atualizada com sucesso.")
            else:
                st.info("Nenhuma alteração realizada.")

def infos_contatos(contatos, collection_contatos, collection_empresas, user, admin):
    if not contatos:
        st.info("Nenhum contato encontrado.")
        return

    # Cria um dicionário com nomes únicos ou rótulos genéricos para os contatos.
    opcoes = {
        f"{contato.get('nome', '').strip()} {contato.get('sobrenome', '').strip()}".strip() or f"Contato {i+1}": i 
        for i, contato in enumerate(contatos)
    }
    selecionado = st.selectbox("Selecione o contato para visualizar:", list(opcoes.keys()), key="contatos_select")
    indice = opcoes[selecionado]
    contato_obj = contatos[indice]

    # Permite edição se o usuário for o proprietário da empresa correspondente ou for admin.
    editable = admin or (collection_empresas.find_one({"_id": contato_obj.get("empresa_id"), "proprietario": user}) is not None)

    nome = st.text_input("Nome", value=contato_obj.get("nome", ""), disabled=not editable, key=f"contato_nome_{indice}")
    sobrenome = st.text_input("Sobrenome", value=contato_obj.get("sobrenome", ""), disabled=not editable, key=f"contato_sobrenome_{indice}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        cargo = st.text_input("Cargo", value=contato_obj.get("cargo", ""), disabled=not editable, key=f"contato_cargo_{indice}")
    with col2:
        email = st.text_input("Email", value=contato_obj.get("email", ""), disabled=not editable, key=f"contato_email_{indice}")
    with col3:
        telefone = st.text_input("Telefone", value=contato_obj.get("fone", ""), disabled=not editable, key=f"contato_fone_{indice}")

    if editable:
        if st.button("Salvar alterações", key=f"contato_salvar_alteracoes_{indice}"):
            updated_data = {
                "nome": nome,
                "sobrenome": sobrenome,
                "cargo": cargo,
                "email": email,
                "fone": telefone,
            }
            result = collection_contatos.update_one({"_id": contato_obj["_id"]}, {"$set": updated_data})
            if result.modified_count:
                st.success("Contato atualizado com sucesso.")
            else:
                st.info("Nenhuma alteração realizada.")

def infos_tarefas(tarefas, collection_tarefas, collection_empresas, user, admin):
    if not tarefas:
        st.info("Nenhuma tarefa encontrada.")
        return

    # Mapeia cada tarefa usando o título e a data de execução para facilitar a identificação.
    opcoes = {
        f"{tarefa.get('titulo', '').strip()} - {tarefa.get('data_execucao', '')}".strip() or f"Tarefa {i+1}": i 
        for i, tarefa in enumerate(tarefas)
    }
    selecionado = st.selectbox("Selecione a tarefa para visualizar:", list(opcoes.keys()), key="tarefas_select")
    indice = opcoes[selecionado]
    tarefa_obj = tarefas[indice]

    # Permite edição se o user for o proprietário da empresa ou for admin.
    editable = admin or (collection_empresas.find_one({"_id": tarefa_obj.get("empresa_id"), "proprietario": user}) is not None)

    titulo = st.text_input("Título", value=tarefa_obj.get("titulo", ""), disabled=not editable, key=f"tarefa_titulo_{indice}")
    col1, col2 = st.columns(2)
    with col1:
        data_execucao = st.text_input("Data de Execução", value=tarefa_obj.get("data_execucao", ""), disabled=not editable, key=f"tarefa_data_execucao_{indice}")
    with col2:
        status = st.text_input("Status", value=tarefa_obj.get("status", ""), disabled=not editable, key=f"tarefa_status_{indice}")
    observacoes = st.text_area("Observações", value=tarefa_obj.get("observacoes", ""), disabled=not editable, key=f"tarefa_observacoes_{indice}")

    if editable:
        if st.button("Salvar alterações", key=f"tarefa_salvar_alteracoes_{indice}"):
            updated_data = {
                "titulo": titulo,
                "data_execucao": data_execucao,
                "status": status,
                "observacoes": observacoes,
            }
            result = collection_tarefas.update_one({"_id": tarefa_obj["_id"]}, {"$set": updated_data})
            if result.modified_count:
                st.success("Tarefa atualizada com sucesso.")
            else:
                st.info("Nenhuma alteração realizada.")

def infos_atividades(atividades, collection_atividades):
    if not atividades:
        st.info("Nenhuma atividade encontrada.")
        return

    # Ordena as atividades da mais recente para a mais antiga.
    def parse_date(atividade):
        data_str = atividade.get("data_execucao_atividade", "")
        try:
            return datetime.datetime.strptime(data_str, "%Y-%m-%d")
        except Exception:
            return datetime.datetime.min  # Atividades sem data ficam no final.

    sorted_atividades = sorted(atividades, key=parse_date, reverse=True)

    # Mapeamento dos meses em português.
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # Agrupa atividades por ano e mês.
    grupos = {}
    for atividade in sorted_atividades:
        data_str = atividade.get("data_execucao_atividade", "")
        try:
            dt = datetime.datetime.strptime(data_str, "%Y-%m-%d")
            chave = (dt.year, dt.month)
        except Exception:
            chave = ("Data não informada", None)
        grupos.setdefault(chave, []).append(atividade)

    # Ordena e exibe os grupos da mais recente para a mais antiga.
    chaves_ordenadas = sorted(
        grupos.keys(),
        key=lambda k: (k[0] if isinstance(k[0], int) else -1, k[1] if k[1] is not None else -1),
        reverse=True
    )

    for chave in chaves_ordenadas:
        if chave[0] == "Data não informada":
            header = "Data não informada"
        else:
            ano, mes = chave
            mes_str = meses_pt.get(mes, "Mês não informado")
            header = f"**{mes_str} de {ano}**"

        with st.expander(header):
            for atividade in grupos[chave]:
                data_exec = atividade.get("data_execucao_atividade", "Data não informada")
                descricao = atividade.get("descricao", "Descrição não informada")
                tipo = atividade.get("tipo_atividade", "Tipo não informado")
                status = atividade.get("status", "Não informado")
                atividade_id = atividade.get('_id', '')

                col1, col2, col3, col4 = st.columns([1, 7, 1, 1])
                with col1:
                    st.text_input("Tipo", value=tipo, disabled=True, key=f"atividade_tipo_{atividade_id}")
                with col2:
                    st.text_input("Descrição", value=descricao, disabled=True, key=f"atividade_descricao_{atividade_id}")
                with col3:
                    st.text_input("Status", value=status, disabled=True, key=f"atividade_status_{atividade_id}")
                with col4:
                    st.text_input("Data de Execução", value=data_exec, disabled=True, key=f"atividade_data_exec_{atividade_id}")

def infos_negocios(negocios, collection_negocios):
    if not negocios:
        st.info("Nenhum negócio encontrado.")
        return

    # Função para converter a data de criação em objeto datetime para ordenação.
    def parse_data_criacao(negocio):
        data_str = negocio.get("data_criacao", "")
        if 'T' in data_str:
            data_str = data_str.split('T')[0]
        try:
            return datetime.datetime.strptime(data_str, "%Y-%m-%d")
        except Exception:
            return datetime.datetime.min  # Caso a data não esteja no formato esperado.

    # Ordena os negócios da mais recente para a mais antiga.
    sorted_negocios = sorted(negocios, key=parse_data_criacao, reverse=True)

    # Cria um dicionário com opções para o selectbox com base nos negócios ordenados.
    opcoes = {
        (
            f"{negocio.get('cliente', '').strip()}: {negocio.get('nome_oportunidade', '').strip()}"
            if negocio.get('cliente', '').strip()
            else negocio.get('nome_oportunidade', '').strip()
        ) + " - " +
        (
            negocio.get('data_criacao', '').split('T')[0] 
            if 'T' in negocio.get('data_criacao', '')
            else negocio.get('data_criacao', '')
        ): i
        for i, negocio in enumerate(sorted_negocios)
    }
    selecionado = st.selectbox("Selecione o negócio para visualizar:", list(opcoes.keys()), key="negocios_select")
    indice = opcoes[selecionado]
    negocio_obj = sorted_negocios[indice]

    # Linha 1: Cliente, Oportunidade e Proprietário em colunas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Cliente", value=negocio_obj.get("cliente", ""), disabled=True, key=f"negocio_cliente_{indice}")
    with col2:
        st.text_input("Oportunidade", value=negocio_obj.get("nome_oportunidade", ""), disabled=True, key=f"negocio_nome_oportunidade_{indice}")
    with col3:
        st.text_input("Proprietário", value=negocio_obj.get("proprietario", ""), disabled=True, key=f"negocio_proprietario_{indice}")

    # Linha 2: Produtos (exibido em tela inteira)
    produtos = negocio_obj.get("produtos", "")
    if isinstance(produtos, list):
        produtos_str = ", ".join(produtos)
    else:
        produtos_str = produtos
    st.text_input("Produtos", value=produtos_str, disabled=True, key=f"negocio_produtos_{indice}")

    # Linha 3: Valor Estimado, Valor Orçamento e Estágio em colunas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Valor Estimado", value=negocio_obj.get("valor_estimado", ""), disabled=True, key=f"negocio_valor_estimado_{indice}")
    with col2:
        st.text_input("Valor Orçamento", value=negocio_obj.get("valor_orcamento", ""), disabled=True, key=f"negocio_valor_orcamento_{indice}")
    with col3:
        st.text_input("Estágio", value=negocio_obj.get("estagio", ""), disabled=True, key=f"negocio_estagio_{indice}")

    # Linha 4: Data Criação, Data Fechamento e Dias para Fechar em colunas
    data_criacao = negocio_obj.get("data_criacao", "")
    if 'T' in data_criacao:
        data_criacao = data_criacao.split('T')[0]
    data_fechamento = negocio_obj.get("data_fechamento", "")
    if 'T' in data_fechamento:
        data_fechamento = data_fechamento.split('T')[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Data Criação", value=data_criacao, disabled=True, key=f"negocio_data_criacao_{indice}")
    with col2:
        st.text_input("Data Fechamento", value=data_fechamento, disabled=True, key=f"negocio_data_fechamento_{indice}")
    with col3:
        st.text_input("Dias para Fechar", value=negocio_obj.get("dias_para_fechar", ""), disabled=True, key=f"negocio_dias_para_fechar_{indice}")

    # Linha 5: Condições de Pagamento e Prazo de Execução em colunas
    col1, col2 = st.columns(2)
    with col1:
        st.text_area("Condições de pagamento da última proposta gerada", value=negocio_obj.get("condicoes_pagamento", ""), disabled=True, key=f"negocio_condicoes_pagamento_{indice}")
    with col2:
        st.text_area("Prazo de Execução da última proposta gerada", value=negocio_obj.get("prazo_execucao", ""), disabled=True, key=f"negocio_prazo_execucao_{indice}")