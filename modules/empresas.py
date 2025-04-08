import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor
import random
from datetime import datetime, timedelta
import pandas as pd
from utils.database import get_collection
from modules.contatos import *
from modules.atividades import *
from modules.tarefas import *

# Cria uma sessão global do requests para reuso
session = requests.Session()

def clean_cnpj(cnpj):
    return cnpj.replace(".", "").replace("/", "").replace("-", "").replace(" ", "")

def clean_cep(cep):
    return cep.replace("-", "").replace(" ", "")

@st.cache_data(ttl=600)
def buscar_dados_cnpj(cnpj):
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"
    response = session.get(url)
    if response.status_code == 200:
        return response.json()
    return None

@st.cache_data(ttl=600)
def buscar_dados_cep(cep):
    url = f"https://viacep.com.br/ws/{cep}/json/"
    response = session.get(url)
    if response.status_code == 200:
        return response.json()
    return None

@st.fragment
def editar_empresa(user, admin):
    if "empresa_selecionada" not in st.session_state or not st.session_state["empresa_selecionada"]:
        st.warning("Nenhuma empresa selecionada para edição.")
        return

    empresa = st.session_state["empresa_selecionada"]

    # Se admin for True, pode editar qualquer empresa; caso contrário, apenas se for proprietário
    eh_proprietario = admin or (user == empresa["Vendedor"])

    st.subheader("✏️ Editar Empresa")

    collection_usuarios = get_collection("usuarios")
    collection_empresas = get_collection("empresas")

    usuarios = list(collection_usuarios.find({}, {"nome": 1, "sobrenome": 1, "email": 1}))
    lista_usuarios = [f"{usuario['nome']} {usuario['sobrenome']}" for usuario in usuarios]
    lista_usuarios.sort()

    with st.form(key="form_edicao_empresa"):
        col1, col2 = st.columns(2)
        with col1:
            razao_social = st.text_input("Nome da Empresa", value=empresa["Nome"], disabled=not eh_proprietario)
        with col2:
            cidade = st.text_input("Cidade", value=empresa["Cidade"], disabled=True)

        col3, col4 = st.columns(2)
        with col3:
            estado = st.text_input("Estado", value=empresa["UF"], disabled=True)
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
                index=["", "Comercial", "Residencial", "Residencial MCMV", "Industrial"].index(
                    empresa.get("Setor", "Comercial")),
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
                default=empresa.get("Tamanho", []) if isinstance(empresa.get("Tamanho"), list)
                else [empresa.get("Tamanho", "Tier 1")],
                disabled=not eh_proprietario
            )

        submit = st.form_submit_button("💾 Salvar Alterações", disabled=not eh_proprietario)

        if submit and eh_proprietario:
            collection_empresas.update_one(
                {"razao_social": empresa["Nome"]},
                {"$set": {
                    "razao_social": razao_social,
                    "proprietario": novo_usuario,
                    "setor": setor,
                    "ultima_atividade": datetime.today().strftime("%Y-%m-%d"),
                    "produto_interesse": produto_interesse,
                    "tamanho_empresa": tamanho_empresa,
                }}
            )
            st.success("Dados da empresa atualizados com sucesso!")
            st.rerun()

@st.fragment            
def cadastrar_empresas(user, admin):
    collection_empresas = get_collection("empresas")
    collection_subempresas = get_collection("subempresas")
    collection_tarefas = get_collection("tarefas")

    st.header('Cadastro de Empresas')
    st.write('----')

    if "dados_cnpj" not in st.session_state:
        st.session_state["dados_cnpj"] = {}
    if "dados_cep" not in st.session_state:
        st.session_state["dados_cep"] = {}

    st.subheader("🔍 Busca Automática de CNPJ e CEP")
    with st.expander("Preencher Dados com CNPJ e CEP (dois cliques para buscar)"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cnpj_input = st.text_input("CNPJ", max_chars=18, placeholder="Digite o CNPJ", key="cnpj_input")
            if st.button("🔍 Buscar CNPJ", key="buscar_cnpj"):
                cnpj_limpo = clean_cnpj(cnpj_input)
                if len(cnpj_limpo) == 14:
                    dados = buscar_dados_cnpj(cnpj_limpo)
                    if dados:
                        st.success("Dados do CNPJ encontrados!")
                        st.session_state["dados_cnpj"] = dados
                    else:
                        st.error("CNPJ não encontrado!")
                else:
                    st.error("CNPJ inválido! Certifique-se de que tem 14 dígitos.")
        with col2:
            cep_input = st.text_input("CEP", max_chars=10, placeholder="Digite o CEP", key="cep_input")
            if st.button("🔍 Buscar CEP", key="buscar_cep"):
                cep_limpo = clean_cep(cep_input)
                if len(cep_limpo) == 8:
                    dados = buscar_dados_cep(cep_limpo)
                    if dados:
                        st.success("Dados do CEP encontrados!")
                        st.session_state["dados_cep"] = dados
                    else:
                        st.error("CEP não encontrado!")
                else:
                    st.error("CEP inválido! Certifique-se de que tem 8 dígitos.")
        with col3:
            if st.button("🔍 Buscar Ambos", key="buscar_ambos"):
                # Executa buscas em paralelo
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_cnpj = executor.submit(buscar_dados_cnpj, clean_cnpj(cnpj_input))
                    future_cep = executor.submit(buscar_dados_cep, clean_cep(cep_input))
                    dados_cnpj = future_cnpj.result()
                    dados_cep = future_cep.result()
                if dados_cnpj:
                    st.success("Dados do CNPJ encontrados!")
                    st.session_state["dados_cnpj"] = dados_cnpj
                else:
                    st.error("CNPJ não encontrado ou inválido!")
                if dados_cep:
                    st.success("Dados do CEP encontrados!")
                    st.session_state["dados_cep"] = dados_cep
                else:
                    st.error("CEP não encontrado ou inválido!")

    st.subheader("📃 Formulário de Cadastro")
    with st.form(key="form_cadastro_empresa"):
        razao_social = st.text_input("Nome da Empresa *",
                                     value=st.session_state["dados_cnpj"].get("nome", ""),
                                     key="razao_social")
        cols1 = st.columns(3)
        with cols1[0]:
            site = st.text_input("Site",
                                 value=st.session_state["dados_cnpj"].get("site", ""),
                                 key="site")
        with cols1[1]:
            cnpj = st.text_input("CNPJ",
                                 value=clean_cnpj(cnpj_input),
                                 max_chars=18,
                                 key="cnpj")
        with cols1[2]:
            cep = st.text_input("CEP",
                                value=st.session_state["dados_cnpj"].get("cep",
                                      st.session_state["dados_cep"].get("localidade", "")),
                                key="cep")
        
        cols2 = st.columns(3)
        with cols2[0]:
            endereco = st.text_input("Endereço",
                                     value=st.session_state["dados_cnpj"].get("endereco",
                                           st.session_state["dados_cep"].get("uf", "")),
                                     key="endereco")
        collection_cidades = get_collection("cidades")
        collection_ufs = get_collection("ufs")
        cidades_options = sorted(collection_cidades.distinct("cidade"))
        ufs_options = sorted(collection_ufs.distinct("uf"))
        cidades_options = [""] + cidades_options
        ufs_options = [""] + ufs_options
        default_cidade = st.session_state["dados_cnpj"].get("municipio",
                            st.session_state["dados_cep"].get("localidade", ""))
        default_estado = st.session_state["dados_cnpj"].get("uf",
                            st.session_state["dados_cep"].get("uf", ""))
        default_index_cidade = cidades_options.index(default_cidade) if default_cidade in cidades_options else 0
        default_index_estado = ufs_options.index(default_estado) if default_estado in ufs_options else 0
        with cols2[1]:
            cidade = st.selectbox("Cidade *", options=cidades_options,
                                  index=default_index_cidade, key="cidade")
        with cols2[2]:
            estado = st.selectbox("Estado *", options=ufs_options,
                                  index=default_index_estado, key="estado")
        
        cols3 = st.columns(3)
        with cols3[0]:
            setor = st.selectbox("Setor *",
                                 ["Comercial", "Residencial", "Residencial MCMV", "Industrial"],
                                 key="setor")
        with cols3[1]:
            produto_interesse = st.multiselect(
                "Produto de Interesse *", 
                ["NBR Fast", "Consultoria NBR", "Consultoria HYGGE", "Consultoria Certificação"],
                key="produto_interesse",
                placeholder="Selecione o produto de interesse"
            )
        with cols3[2]:
            tamanho_empresa = st.multiselect("Tamanho da Empresa *",
                                             ["Tier 1", "Tier 2", "Tier 3", "Tier 4"],
                                             key="tamanho_empresa", placeholder="Selecione o tamanho da empresa")
        
        cols4 = st.columns(3)
        with cols4[1]:
            st.write("")  # Espaço para alinhamento

        grau_cliente = 'Lead'
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
                        "produto_interesse": produto_interesse,
                        "pais": "Brasil",
                        "endereco": endereco,
                        "cnpj": cnpj,
                        "cep": cep,
                    }
                    collection_empresas.insert_one(document)
                    collection_subempresas.insert_one(document)
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
def excluir_empresa(user, admin):
    if "empresa_selecionada" not in st.session_state or not st.session_state["empresa_selecionada"]:
        st.warning("Nenhuma empresa selecionada para exclusão.")
        return

    empresa = st.session_state["empresa_selecionada"]
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
        st.session_state["empresa_selecionada"] = None
        st.session_state["confirmar_exclusao"] = False