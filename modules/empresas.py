import streamlit as st
import requests
from utils.database import get_collection
import pandas as pd
from datetime import datetime
from modules.contatos import *
from modules.atividades import *
from modules.tarefas import *

def buscar_dados_cnpj(cnpj):
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def buscar_dados_cep(cep):
    url = f"https://viacep.com.br/ws/{cep}/json/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

@st.fragment
def editar_empresa(user, admin):
    if "empresa_selecionada" not in st.session_state or not st.session_state["empresa_selecionada"]:
        st.warning("Nenhuma empresa selecionada para edição.")
        return
    
    empresa = st.session_state["empresa_selecionada"]

    # Se admin for True, pode editar qualquer empresa
    # Se admin for False, só pode editar as empresas que possui
    eh_proprietario = admin or (user == empresa["Vendedor"])

    st.subheader("✏️ Editar Empresa")

    collection_usuarios = get_collection("usuarios")  # Coleção de usuários
    collection_empresas = get_collection("empresas")

    # Buscar os campos "nome", "sobrenome" e "email" para cada usuário
    usuarios = list(collection_usuarios.find({}, {"nome": 1, "sobrenome": 1, "email": 1}))

    # Formatar a lista de usuários para o formato: "nome sobrenome (email)"
    lista_usuarios = [f"{usuario['nome']} {usuario['sobrenome']}" for usuario in usuarios]
    lista_usuarios.sort()

    with st.form(key="form_edicao_empresa"):
        col1, col2 = st.columns(2)
        with col1:
            razao_social = st.text_input("Nome da Empresa", value=empresa["Nome"], disabled=not eh_proprietario)

        with col2:
            cidade = st.text_input("Cidade", value=empresa["Cidade"], disabled=True)  # Cidade não editável
        
        col3, col4 = st.columns(2)
        with col3:
            estado = st.text_input("Estado", value=empresa["UF"], disabled=True)  # Estado não editável
        with col4:
            novo_usuario = st.selectbox(
                "Usuário (Vendedor)", 
                options=lista_usuarios, 
                index=lista_usuarios.index(empresa["Vendedor"]) if empresa["Vendedor"] in lista_usuarios else 0, 
                disabled=not eh_proprietario
            )

        col5, col6 = st.columns(2)
        with col5:
            setor = st.selectbox(
                "Setor", 
                ["", "Comercial", "Residencial", "Residencial MCMV", "Industrial"], 
                index=["","Comercial", "Residencial", "Residencial MCMV", "Industrial"].index(empresa.get("Setor", "Comercial")), 
                disabled=not eh_proprietario
            )
        with col6:
            options_produto = ["", "NBR Fast", "Consultoria NBR", "Consultoria Hygge", "Consultoria Certificação"]
            default_produto = empresa.get("Produto Interesse", [])
            if not isinstance(default_produto, list):
                default_produto = [default_produto] if default_produto in options_produto else ["NBR Fast"]
            else:
                default_produto = [p for p in default_produto if p in options_produto]
                if not default_produto:
                    default_produto = ["NBR Fast"]
            produto_interesse = st.multiselect(
                "Produto de Interesse", 
                options_produto, 
                default=default_produto,
                disabled=not eh_proprietario
            )

        col7, col8 = st.columns(2)
        with col7:
            tamanho_empresa = st.multiselect(
                "Tamanho da Empresa", 
                ["", "Tier 1", "Tier 2", "Tier 3", "Tier 4"],  
                default=empresa.get("Tamanho", []) if isinstance(empresa.get("Tamanho"), list) else [empresa.get("Tamanho", "Tier 1")],
                disabled=not eh_proprietario
            )

        submit = st.form_submit_button("💾 Salvar Alterações", disabled=not eh_proprietario)

        if submit and eh_proprietario:
            # Atualiza os dados no banco de dados
            collection_empresas.update_one(
                {"razao_social": empresa["Nome"]},
                {"$set": {
                    "razao_social": razao_social,
                    "proprietario": novo_usuario,
                    "setor": setor,
                    "produto_interesse": produto_interesse,  # ✅ Agora salva como lista
                    "tamanho_empresa": tamanho_empresa,
                }}
            )

            st.success("Dados da empresa atualizados com sucesso!")
            st.rerun()
  

@st.fragment            
def cadastrar_empresas(user, admin):
    collection_empresas = get_collection("empresas")
    collection_subempresas = get_collection("subempresas")
    collection_tarefas = get_collection("tarefas")  # Conectar com a coleção de tarefas

    st.header('Cadastro de Empresas')
    st.write('----')

    if "dados_cnpj" not in st.session_state:
        st.session_state["dados_cnpj"] = {}
    if "dados_cep" not in st.session_state:
        st.session_state["dados_cep"] = {}

    # 🔍 Busca CNPJ e CEP antes de exibir o formulário
    st.subheader("🔍 Busca Automática de CNPJ e CEP")
    with st.expander("Preencher Dados com CNPJ e CEP (dois cliques para buscar)"):
        col1, col2 = st.columns(2)
        with col1:
            cnpj_input = st.text_input("CNPJ", max_chars=18, placeholder="Digite o CNPJ", key="cnpj_input")
            if st.button("🔍 Buscar CNPJ", key="buscar_cnpj"):
                cnpj_limpo = cnpj_input.replace(".", "").replace("/", "").replace("-", "").replace(" ", "")
                if len(cnpj_limpo) == 14:
                    dados_cnpj = buscar_dados_cnpj(cnpj_limpo)
                    if dados_cnpj:
                        st.success("Dados do CNPJ encontrados!")
                        st.session_state["dados_cnpj"] = dados_cnpj
                    else:
                        st.error("CNPJ não encontrado!")
                else:
                    st.error("CNPJ inválido! Certifique-se de que tem 14 dígitos.")

        with col2:
            cep_input = st.text_input("CEP", max_chars=10, placeholder="Digite o CEP", key="cep_input")
            if st.button("🔍 Buscar CEP", key="buscar_cep"):
                cep_limpo = cep_input.replace("-", "").replace(" ", "")
                if len(cep_limpo) == 8:
                    dados_cep = buscar_dados_cep(cep_limpo)
                    if dados_cep:
                        st.success("Dados do CEP encontrados!")
                        st.session_state["dados_cep"] = dados_cep
                    else:
                        st.error("CEP não encontrado!")
                else:
                    st.error("CEP inválido! Certifique-se de que tem 8 dígitos.")

    # 📃 Formulário de Cadastro
    st.subheader("📃 Formulário de Cadastro")
    with st.form(key="form_cadastro_empresa"):
        razao_social = st.text_input("Nome da Empresa *", value=st.session_state["dados_cnpj"].get("nome", ""), key="razao_social")
        col1, col2 = st.columns(2)
        with col1:
            site = st.text_input("Site", value=st.session_state["dados_cnpj"].get("site", ""), key="site")
        with col2:
            cnpj = st.text_input("CNPJ", value=cnpj_input.replace(".", "").replace("/", "").replace("-", "").replace(" ", ""), max_chars=18, key="cnpj")

        col7, col8 = st.columns(2)
        with col7:
            cep = st.text_input("CEP", value=st.session_state["dados_cnpj"].get("cep", st.session_state["dados_cep"].get("localidade", "")), key="cep")
        with col8:
            endereco = st.text_input("Endereço", value=st.session_state["dados_cnpj"].get("endereco", st.session_state["dados_cep"].get("uf", "")), key="endereco")

        col3, col4 = st.columns(2)

        # Consulta as coleções de cidades e UFs
        collection_cidades = get_collection("cidades")
        collection_ufs = get_collection("ufs")

        # Obtém as opções únicas
        cidades_options = sorted(collection_cidades.distinct("cidade"))
        ufs_options = sorted(collection_ufs.distinct("uf"))

        # Inclui uma opção vazia para possibilitar não seleção
        cidades_options = [""] + cidades_options
        ufs_options = [""] + ufs_options

        # Define valores padrão a partir dos dados do session_state
        default_cidade = st.session_state["dados_cnpj"].get("municipio", st.session_state["dados_cep"].get("localidade", ""))
        default_estado = st.session_state["dados_cnpj"].get("uf", st.session_state["dados_cep"].get("uf", ""))

        # Define os índices padrão se o valor estiver presente nas opções
        default_index_cidade = cidades_options.index(default_cidade) if default_cidade in cidades_options else 0
        default_index_estado = ufs_options.index(default_estado) if default_estado in ufs_options else 0

        # Cria os widgets com as opções consultadas no banco
        with col3:
            cidade = st.selectbox(
                "Cidade *",
                options=cidades_options,
                index=default_index_cidade,
                key="cidade"
            )

        with col4:
            estado = st.selectbox(
                "Estado *",
                options=ufs_options,
                index=default_index_estado,
                key="estado"
            )

        col5, col6 = st.columns(2)
        with col5:
            setor = st.selectbox("Setor *", ["Comercial", "Residencial", "Residencial MCMV", "Industrial"], key="setor")
        with col6:
            produto_interesse = st.multiselect("Produto de Interesse *", 
                                               ["NBR Fast", "Consultoria NBR", "Consultoria HYGGE", "Consultoria Certificação"],
                                               key="produto_interesse")

        col7, col8 = st.columns(2)
        with col7:
            tamanho_empresa = st.multiselect("Tamanho da Empresa *", ["Tier 1", "Tier 2", "Tier 3", "Tier 4"], key="tamanho_empresa")
        with col8:
            grau_cliente = st.selectbox("Grau do Cliente", ["Lead", "Lead Qualificado", "Oportunidade", "Cliente"], key="grau_cliente", disabled=True)

        submit = st.form_submit_button("✅ Cadastrar")

        if submit:
            if not razao_social or not cnpj or not cidade or not estado or not setor or not produto_interesse or not tamanho_empresa:
                st.error("Preencha todos os campos obrigatórios!")
            else:
                existing_company = collection_empresas.find_one({"razao_social": razao_social})
                if existing_company:
                    st.error("Empresa já cadastrada com esta razão social!")
                else:
                    random_hex = f"{random.randint(0, 0xFFFF):04x}"
                    # Registrar empresa
                    now = datetime.today().strftime("%Y-%m-%d")
                    document = {
                        "razao_social": razao_social,
                        "proprietario": user,
                        "cidade": cidade,
                        "uf": estado,
                        "ultima_atividade": now,
                        "site": site,
                        "setor": setor,
                        "grau_cliente": grau_cliente,
                        "negocios": 0,
                        "data_criacao": now,
                        "proxima_atividade": "",
                        "tamanho_empresa": tamanho_empresa,
                        "produto_interesse": produto_interesse,  # ✅ Agora é uma lista
                        "pais": "Brasil",
                        "endereco": endereco,
                        "cnpj": cnpj,
                        "cep": cep,
                    }
                    collection_empresas.insert_one(document)
                    collection_subempresas.insert_one(document)

                    # Criar automaticamente uma tarefa associada à empresa
                    prazo_execucao = datetime.today().date() + timedelta(days=1)
                    tarefa_document = {
                        "titulo": f"Identificar personas ({razao_social} - {random_hex})",
                        "empresa": razao_social,
                        "data_execucao": prazo_execucao.strftime("%Y-%m-%d"),
                        "observacoes": "Nova empresa cadastrada",
                        "status": "🟨 Em andamento"
                    }
                    collection_tarefas.insert_one(tarefa_document)

                    st.success("Empresa cadastrada com sucesso e tarefa inicial criada!")
                    st.rerun()
                    
@st.fragment
def consultar_empresas(user, admin):
    collection_empresas = get_collection("empresas")
    collection_usuarios = get_collection("usuarios")
    collection_oportunidades = get_collection("oportunidades")

    # Carrega todas as razões sociais e vendedores
    todas_razoes = list(collection_empresas.distinct("razao_social"))
    todas_razoes = [r for r in todas_razoes if r]

    usuarios = list(collection_usuarios.find({}, {"nome": 1, "sobrenome": 1}))
    vendedores = [f"{usuario['nome']} {usuario['sobrenome']}" for usuario in usuarios if usuario.get('nome') and usuario.get('sobrenome')]
    vendedores.sort()

    # Carrega os demais filtros com o mesmo padrão
    ufs = list(collection_empresas.distinct("uf"))
    ufs = [u for u in ufs if u]

    setores = list(collection_empresas.distinct("setor"))
    setores = [s for s in setores if s]

    produtos_interesse = list(collection_empresas.distinct("produto_interesse"))
    produtos_interesse = [p for p in produtos_interesse if p]

    grau_clientes = list(collection_empresas.distinct("grau_cliente"))
    grau_clientes = [g for g in grau_clientes if g]

    # Exemplo de uso dos filtros na interface Streamlit:
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)

    with col1:
        filtro_razao_social = st.selectbox(
            "Nome",
            options=[""] + todas_razoes,
            index=0,
            placeholder="Selecione a razão social"
        )

    with col2:
        filtro_vendedor = st.selectbox(
            "Vendedor",
            options=[""] + vendedores,
            index=0,
            placeholder="Selecione o vendedor"
        )

    with col3:
        filtro_tamanho = st.multiselect(
            "Tamanho",
            options=["Tier 1", "Tier 2", "Tier 3", "Tier 4"],
            default=[],
            placeholder="Selecione o tamanho"
        )

    with col4:
        filtro_data_atividade = st.date_input("Data da última atividade", value=None)

    with col5:
        filtro_uf = st.selectbox(
            "UF",
            options=[""] + ufs,
            index=0,
            placeholder="Selecione a UF"
        )

    with col6:
        filtro_setor = st.multiselect(
            "Setor",
            options=setores,
            default=[],
            placeholder="Selecione o setor"
        )

    with col7:
        filtro_produto_interesse = st.multiselect(
            "Produto Interesse",
            options=produtos_interesse,
            default=[],
            placeholder="Selecione o produto de interesse"
        )

    with col8:
        filtro_grau_cliente = st.selectbox(
            "Grau Cliente",
            options=[""] + grau_clientes,
            index=0,
            placeholder="Selecione o grau do cliente"
        )

    # Construção da query com os filtros aplicados
    query = {}

    if filtro_razao_social and filtro_razao_social != "":
        query["razao_social"] = {"$regex": filtro_razao_social, "$options": "i"}

    if filtro_tamanho:
        query["tamanho_empresa"] = {"$in": filtro_tamanho}

    if filtro_vendedor and filtro_vendedor != "":
        query["proprietario"] = filtro_vendedor

    if filtro_data_atividade:
        query["ultima_atividade"] = {"$gte": filtro_data_atividade.strftime("%Y-%m-%d")}

    if filtro_uf and filtro_uf != "":
        query["uf"] = filtro_uf

    if filtro_setor:
        query["setor"] = {"$in": filtro_setor}

    if filtro_produto_interesse:
        query["produto_interesse"] = {"$in": filtro_produto_interesse}

    if filtro_grau_cliente and filtro_grau_cliente != "":
        query["grau_cliente"] = filtro_grau_cliente

    # Buscar empresas no banco de dados com os filtros aplicados
    empresas_filtradas = list(
        collection_empresas.find(
            query,
            {
                "_id": 0,
                "razao_social": 1,
                "proprietario": 1,
                "data_criacao": 1,
                "ultima_atividade": 1,
                "cidade": 1,
                "uf": 1,
                "setor": 1,
                "tamanho_empresa": 1,
                "produto_interesse": 1,
                "grau_cliente": 1,
                "cnpj": 1  
            },
        )
    )

    if empresas_filtradas:
        df_empresas = pd.DataFrame(empresas_filtradas)

        # ✅ Garantir que "CNPJ" existe antes de renomear colunas
        if "razao_social" in df_empresas.columns:
            df_empresas = df_empresas.rename(
                columns={
                    "razao_social": "Nome",
                    "proprietario": "Vendedor",
                    "data_criacao": "Data de Criação",
                    "ultima_atividade": "Última Atividade",
                    "cidade": "Cidade",
                    "uf": "UF",
                    "setor": "Setor",
                    "tamanho_empresa": "Tamanho",
                    "produto_interesse": "Produto Interesse",
                    "grau_cliente": "Grau Cliente",
                    "cnpj": "CNPJ"
                }
            )
        else:
            st.error("Erro: O campo 'Nome' não foi encontrado no banco de dados.")

        # Adicionar a coluna "Visualizar" na primeira posição
        df_empresas.insert(0, "Visualizar", False)

        # ✅ Corrigir seleção no session_state
        empresa_nome_selecionada = st.session_state.get("empresa_nome_selecionada", None)

        if empresa_nome_selecionada and empresa_nome_selecionada in df_empresas["Nome"].values:
            df_empresas.loc[df_empresas["Nome"] == empresa_nome_selecionada, "Visualizar"] = True

        # Criar editor de dados interativo
        #df_empresas = df_empresas.sort_values(by='Última Atividade', ascending=False)

        if admin:
            df_empresas.insert(0, "Editar", False)

            # Exibe botões para selecionar/desmarcar tudo
            col_select, col_deselect, v3, v4, v5, v6, v7, v8 = st.columns(8)
            with col_select:
                if st.button("Selecionar tudo", use_container_width=True):
                    df_empresas["Editar"] = True
            with col_deselect:
                if st.button("Desmarcar tudo", use_container_width=True):
                    df_empresas["Editar"] = False
            
            
            df_empresas["Produto Interesse"] = df_empresas["Produto Interesse"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else x
            )

            edited_df = st.data_editor(
                df_empresas,
                column_config={
                    "Editar": st.column_config.CheckboxColumn(
                        "Editar",
                        help="Marque para editar a empresa"
                    ),
                    "Visualizar": st.column_config.CheckboxColumn(
                        "Visualizar",
                        help="Marque para ver detalhes da empresa"
                    )
                },
                disabled=["Nome", "Vendedor", "Data de Criação", "Última Atividade", "Cidade", "UF", "Setor", "Tamanho", "Produto Interesse", "Grau Cliente", "CNPJ"],
                column_order=["Editar", "Visualizar", "Nome", "Vendedor", "Última Atividade", "Grau Cliente", "Cidade", "UF", "Setor", "Produto Interesse", "Tamanho", "Data de Criação", "CNPJ"],
                hide_index=True,
                use_container_width=True
            )

            selected_names = edited_df.loc[edited_df["Editar"] == True, "Nome"].tolist()
            if selected_names:
                with st.expander("🔧 Atualizar informações da(s) empresa(s)", expanded=False):
                    novo_proprietario = st.selectbox(
                        "Selecione o novo Vendedor",
                        options=vendedores,
                        index=0
                    )
                    novo_setor = st.selectbox(
                        "Selecione o novo setor",
                        options=setores,
                        index=0
                    )
                    novo_produto = st.selectbox(
                        "Selecione o novo produto de interesse",
                        options=produtos_interesse,
                        index=0
                    )
                    
                    if st.button("Atualizar Informações"):
                        update_fields = {
                            "proprietario": novo_proprietario,
                            "setor": novo_setor,
                            "produto_interesse": novo_produto
                        }
                        resultado = collection_empresas.update_many(
                            {"razao_social": {"$in": selected_names}},
                            {"$set": update_fields}
                        )
                        st.success(f"{resultado.modified_count} registros de empresas atualizados com sucesso.")
                        
                        # Atualizar também as oportunidades: para cada empresa atualizada,
                        # se o campo "cliente" for igual ao nome da empresa, atualiza o "proprietario"
                        for empresa in selected_names:
                            collection_oportunidades.update_many(
                                {"cliente": empresa},
                                {"$set": {"proprietario": novo_proprietario}}
                            )
                        st.success("Vendedor das oportunidades atualizado com sucesso.")
                        st.rerun()
            else:
                st.write("Nenhuma empresa selecionada para alterações.")
        
        else:
            df_empresas["Produto Interesse"] = df_empresas["Produto Interesse"].apply(
                lambda x: x if isinstance(x, list) or pd.isnull(x) else [x]
            )
            edited_df = st.data_editor(
                df_empresas,
                column_config={
                    "Visualizar": st.column_config.CheckboxColumn(
                        "Visualizar",
                        help="Marque para ver detalhes da empresa"
                    )
                },
                disabled=["Nome", "Vendedor", "Data de Criação", "Última Atividade", "Cidade", "UF", "Setor", "Tamanho", "Produto Interesse", "Grau Cliente", "CNPJ"],
                column_order=["Visualizar", "Nome", "Vendedor", "Última Atividade", "Grau Cliente", "Cidade", "UF", "Setor", "Produto Interesse", "Tamanho", "Data de Criação", "CNPJ"],
                hide_index=True,
                use_container_width=True
            )


        st.write(f'🔍 **{len(df_empresas)}** empresas encontradas.')

        # 🔹 Atualiza a empresa selecionada corretamente
        novas_selecoes = edited_df[edited_df["Visualizar"]].index.tolist()

        # Se uma empresa foi selecionada, desmarcar todas as outras
        if novas_selecoes:
            selected_index = novas_selecoes[0]
            nova_empresa = edited_df.iloc[selected_index].to_dict()

            # Se a seleção mudou, atualizar session_state
            if empresa_nome_selecionada != nova_empresa["Nome"]:
                st.session_state["empresa_selecionada"] = nova_empresa
                st.session_state["empresa_nome_selecionada"] = nova_empresa["Nome"]
                st.rerun()  # 🔄 Garante a atualização imediata no UI

        # Se nenhuma empresa estiver marcada, limpar session_state corretamente
        elif empresa_nome_selecionada:
            del st.session_state["empresa_selecionada"]
            del st.session_state["empresa_nome_selecionada"]
            st.rerun()

        # Exibir detalhes da empresa selecionada
        if st.session_state.get("empresa_selecionada"):
            empresa = st.session_state["empresa_selecionada"]
            empresa_nome = empresa["Nome"]

            st.write('----')

            col1, col2 = st.columns([3.5, 6.5])
            with col1:
                st.write("### 🔍 Detalhes da empresa selecionada")
                with st.popover('✏️ Editar empresa'):
                    editar_empresa(user, admin)

                with st.expander("📋 Dados da Empresa", expanded=True):

                    collection_empresas = get_collection("empresas")
                    empresa_selecionada = st.session_state.get("empresa_selecionada", None)
                    empresa_atual = collection_empresas.find_one({"razao_social": empresa_selecionada["Nome"]})
                    empresa_id = empresa_atual.get("_id") if empresa_atual and "_id" in empresa_atual else None
                    if empresa_id:
                        empresa_atualizada = collection_empresas.find_one({"_id": empresa_id}, {"_id": 0})

                        if empresa_atualizada:
                            dados_empresa = {
                                "Nome": empresa_atualizada.get("razao_social", ""),
                                "Vendedor": empresa_atualizada.get("proprietario", ""),
                                "Última Atividade": empresa_atualizada.get("ultima_atividade", ""),
                                "Data de Criação": empresa_atualizada.get("data_criacao", ""),
                                "Cidade/UF": f"{empresa_atualizada.get('cidade', '')}, {empresa_atualizada.get('uf', '')}",
                                "Setor": empresa_atualizada.get("setor", ""),
                                "Tamanho": empresa_atualizada.get("tamanho_empresa", ""),
                                "Produto Interesse": empresa_atualizada.get("produto_interesse", ""),
                                "Grau Cliente": empresa_atualizada.get("grau_cliente", ""),
                                "CNPJ": empresa_atualizada.get("cnpj", "")
                            }

                            df_dados_empresa = pd.DataFrame(dados_empresa.items(), columns=["Campo", "Informação"])
                            st.dataframe(df_dados_empresa, hide_index=True, use_container_width=True)
                        else:
                            st.warning("Empresa não encontrada no banco de dados.")
                    else:
                        st.warning("Nenhuma empresa selecionada.")

                # Integrando a função de exibir contatos
                if empresa_id:
                    st.write('----')
                    st.subheader("☎️ Informações sobre contatos")
                    exibir_contatos_empresa(user, admin, empresa_id)
                else:
                    st.error("Erro ao carregar o ID da empresa.")

            with col2:
                st.write("### 📜 Tarefas para a empresa")
                if empresa_id:
                    gerenciamento_tarefas(user, admin, empresa_id)
                st.write('----')
                st.write("### 📌 Histórico de atividades")
                if empresa_id:
                    exibir_atividades_empresa(user, admin, empresa_id)
                else:
                    st.error("Erro ao carregar o ID da empresa.")

        else:
            st.write('----')
            st.info("Selecione uma empresa para ver os detalhes.")


@st.fragment
def excluir_empresa(user, admin):
    if "empresa_selecionada" not in st.session_state or not st.session_state["empresa_selecionada"]:
        st.warning("Nenhuma empresa selecionada para exclusão.")
        return
    
    empresa = st.session_state["empresa_selecionada"]

    # Se admin for True, pode excluir qualquer empresa
    # Se admin for False, só pode excluir as empresas que possui
    pode_excluir = admin

    if not pode_excluir:
        st.error("Você não tem permissão para excluir empresas, solicite para o administrador.")
        return
    else:
        collection_empresas = get_collection("empresas")
        collection_empresas.delete_one({"razao_social": empresa["Nome"]})
        collection_subempresas = get_collection("subempresas")
        collection_subempresas.delete_one({"razao_social": empresa["Nome"]})

        st.success(f"Empresa **{empresa['Nome']}** foi removida com sucesso!")
        st.session_state["empresa_selecionada"] = None  # Limpa a seleção
        st.session_state["confirmar_exclusao"] = False
          # Recarrega a página