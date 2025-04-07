import streamlit as st
from msal import ConfidentialClientApplication
import requests
import smtplib
import pandas as pd
import utils.database as db
from streamlit_slickgrid import (
    slickgrid,
)
import modules.dataview.exibir_dados as exibir_dados
from modules import (
    usuarios as usuarios_lib,
    empresas as empresas_lib,
    tarefas as tarefas_lib,
    meus_numeros as meus_numeros_lib,
    contatos as contatos_lib,
    templates as templates_lib,
    produtos as produtos_lib,
    negocios as negocios_lib,
    orcamentos as orcamentos_lib,
    aprovacoes as aprovacoes_lib,
)
import modules.css_adicionais as css_adicionais
import modules.slickgrids as sl
import utils.functions as funcs
from streamlit_option_menu import option_menu
from bson import ObjectId
css_adicionais.page_config()

import concurrent.futures

# Prepare collections
collection_empresas = db.get_collection("empresas")
collection_contatos = db.get_collection("contatos")
collection_tarefas = db.get_collection("tarefas")
collection_atividades = db.get_collection("atividades")
collection_negocios = db.get_collection("oportunidades")
collection_usuarios = db.get_collection("usuarios")
collection_produtos = db.get_collection("produtos")
collection_oportunidades = db.get_collection("oportunidades")
collection_cidades = db.get_collection("cidades")
collection_ufs = db.get_collection("ufs")

def get_data():
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Buscar empresas primeiro pois os IDs são necessários
        future_empresas = executor.submit(list, collection_empresas.find())
        empresas = future_empresas.result()
        empresa_ids = [empresa["_id"] for empresa in empresas]
        
        # Executar as queries em paralelo usando os IDs
        future_contatos = executor.submit(list, collection_contatos.find({"empresa_id": {"$in": empresa_ids}}))
        future_tarefas = executor.submit(list, collection_tarefas.find({"empresa_id": {"$in": empresa_ids}}))
        future_atividades = executor.submit(list, collection_atividades.find({"empresa_id": {"$in": empresa_ids}}))
        future_oportunidades = executor.submit(list, collection_negocios.find({"empresa_id": {"$in": empresa_ids}}))
        
        contatos = future_contatos.result()
        tarefas = future_tarefas.result()
        atividades = future_atividades.result()
        oportunidades = future_oportunidades.result()
    return empresas, contatos, tarefas, atividades, oportunidades

empresas, contatos, tarefas, atividades, oportunidades = get_data()

# Criar mapeamentos em memória rapidamente
contatos_map = {}
for contato in contatos:
    contatos_map.setdefault(contato["empresa_id"], []).append(contato)

tarefas_map = {}
for tarefa in tarefas:
    tarefas_map.setdefault(tarefa["empresa_id"], []).append(tarefa)

atividades_map = {}
for atividade in atividades:
    atividades_map.setdefault(atividade["empresa_id"], []).append(atividade)

oportunidades_map = {}
for oportunidade in oportunidades:
    oportunidades_map.setdefault(oportunidade["empresa_id"], []).append(oportunidade)


if not st.experimental_user.is_logged_in:
    if st.sidebar.button("Fazer login com a Microsoft", use_container_width=True):
        st.login("microsoft")

# This part is executed if the user is logged in - LOGIN DO USUÁRIO
if st.experimental_user.is_logged_in:
    email_logado = st.experimental_user.email
    permission_admin = '@hygge.eco.br' in email_logado and not 'comercial' in email_logado or 'matheus' in email_logado
    
    with st.sidebar:
        if permission_admin: 
            st.info(f'Bem-vindo(a), **{st.experimental_user.name}**!')
            st.info('Este é o ambiente de **admin** para consulta, preenchimento, controle e envio das informações referentes as oportunidades da HYGGE.')
            
            # 1. as sidebar menu
            selected = option_menu(
                f"CRM HYGGE (Admin)",
                ["Home", "Negócios", "Controle de orçamentos", "Templates", "Produtos", "Usuários", "Solicitações", "Indicadores"],
                icons=["house", "currency-dollar", "calculator-fill", "file-earmark-text", "archive", "person-add", "check2-square","speedometer"],
                menu_icon="cast",
                default_index=0,
                styles={
                    #"container": {"background-color": "#3C353F"},  # Background color for the entire menu
                    "menu-title": {"font-size": "16px", "font-weight": "bold"},  # Title styling
                    "nav-link": {"font-size": "12px"},  # Style for links
                    "nav-link-selected": {"font-size": "12px"},  # Style for the selected link
                },
            )
        else:     
            st.info(f'Bem-vindo(a), **{st.experimental_user.name}**!')
            st.info('Este é o ambiente de **vendedor** para consulta, preenchimento, controle e envio das informações referentes as oportunidades da HYGGE.')
            
            # 1. as sidebar menu
            selected = option_menu(
                f"CRM HYGGE (Vendedor)",
                ["Home", "Negócios", "Controle de orçamentos", "Templates", "Produtos", "Usuários", "Solicitações", "Indicadores"],
                icons=["house", "currency-dollar", "calculator-fill", "file-earmark-text", "archive", "person-add", "check2-square","speedometer"],
                menu_icon="cast",
                default_index=0,
                styles={
                    #"container": {"background-color": "#3C353F"},  # Background color for the entire menu
                    "menu-title": {"font-size": "16px", "font-weight": "bold"},  # Title styling
                    "nav-link": {"font-size": "12px"},  # Style for links
                    "nav-link-selected": {"font-size": "12px"},  # Style for the selected link
                },
            )
        if st.button("Logout", use_container_width=True):
            st.logout()

if st.experimental_user.is_logged_in:
    usuario_ativo = st.experimental_user.name
    # informações da empresa razao social "Teste"
    collection_empresas = db.get_collection("empresas")
    
    empresa_Teste = collection_empresas.find_one({"razao_social": "Teste"})
    collection_contatos = db.get_collection("contatos")
    # Cria mapeamentos para acesso rápido
    contatos_map = {}
    for contato in contatos:
        contatos_map.setdefault(contato["empresa_id"], []).append(contato)

    data, columns, options = sl.slickgrid_empresa(empresas, contatos_map)
    if selected == "Home":
        st.title("📜 Tarefas")
        st.info("Acompanhe na tabela abaixo as tarefas relacionadas às suas empresas.")
        with st.expander("Acompanhamento de tarefas", expanded=False):
            if permission_admin: tarefas_lib.gerenciamento_tarefas_por_usuario(usuario_ativo,admin=True)
            else: tarefas_lib.gerenciamento_tarefas_por_usuario(usuario_ativo,admin=False)

        st.write('----')
        st.title("🏢 Empresas")
        st.info("Pesquise e clique em uma empresa dentre as opções abaixo para consultar mais informações a respeito desta empresa.")
        with st.popover("➕ Cadastrar empresa", use_container_width=True):
                if permission_admin: empresas_lib.cadastrar_empresas(usuario_ativo,admin=True)
                else: empresas_lib.cadastrar_empresas(usuario_ativo,admin=False)
        st.write('----')
        out = slickgrid(data, columns, options, key="mygrid", on_click='rerun')
        if out is not None:
            # Persist the selected row index in session_state
            st.session_state.selected_row = out[0]

        # Verifica se já existe uma seleção persistida
        if "selected_row" in st.session_state:
            row = st.session_state.selected_row
            item = data[row]
            tabs = st.tabs(["Informações", "Contatos", "Tarefas e Atividades", "Negócios", "Orçamentos"])
            empresa_obj = next((empresa for empresa in empresas if empresa.get("razao_social", "") == item["empresa"]), None)
            if not empresa_obj:
                st.write("Empresa não encontrada.")
            else:
                empresa_id = empresa_obj["_id"]

                with tabs[0]:
                    st.header("🏢 Informações da empresa")
                    st.info("Consulte e edite as informações da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    if item.get("infos") is None:
                        if permission_admin:
                            with st.expander("Informações da empresa", expanded=True):
                                exibir_dados.infos_empresa(empresa_obj, collection_empresas, collection_usuarios, usuario_ativo, admin=True)
                        else:
                            with st.expander("Informações da empresa", expanded=True):
                                exibir_dados.infos_empresa(empresa_obj, collection_empresas, collection_usuarios, usuario_ativo, admin=False)
                    else:
                        st.write("Informações da empresa não disponíveis para linhas detalhadas.")

                with tabs[1]:
                    st.header("👥 Contatos da empresa")
                    st.info("Consulte e edite os contatos da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    if permission_admin:
                        exibir_dados.infos_contatos(contatos_map.get(empresa_id, []), collection_contatos, collection_empresas, usuario_ativo, admin=True)
                    else:
                        exibir_dados.infos_contatos(contatos_map.get(empresa_id, []), collection_contatos, collection_empresas, usuario_ativo, admin=False)

                with tabs[2]:
                    st.header("📝 Tarefas e Atividades da empresa")
                    st.info("Consulte e edite as tarefas e atividades da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    if permission_admin:
                        tarefas_lib.gerenciamento_tarefas(usuario_ativo, empresa_id, admin=True)
                    else:
                        tarefas_lib.gerenciamento_tarefas(usuario_ativo, empresa_id, admin=False)

                with tabs[3]:
                    st.header("💰 Negócios da empresa")
                    st.info("Consulte e edite os negócios da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    tabs_negocios = st.tabs(["Visualizar negócios", "Adicionar negócio", "Editar negócio"])
                    with tabs_negocios[0]:
                        exibir_dados.infos_negocios(oportunidades_map.get(empresa_id, []), collection_negocios)
                    with tabs_negocios[1]:
                        if permission_admin:
                            negocios_lib.cadastrar_negocio(empresa_obj["_id"], collection_empresas,collection_usuarios, collection_produtos, collection_oportunidades, collection_atividades, usuario_ativo, admin=True)
                        else:
                            negocios_lib.cadastrar_negocio(empresa_obj["_id"], collection_empresas,collection_usuarios, collection_produtos, collection_oportunidades, collection_atividades, usuario_ativo, admin=False)
                    with tabs_negocios[2]:
                        if permission_admin:
                            negocios_lib.editar_negocio(empresa_obj["_id"], collection_oportunidades, collection_empresas,collection_atividades, usuario_ativo, admin=True)
                        else:
                            negocios_lib.editar_negocio(empresa_obj["_id"], collection_oportunidades, collection_empresas,collection_atividades, usuario_ativo, admin=False)
                with tabs[4]:
                    st.header("💰 Orçamentos da empresa")
                    st.info("Consulte e edite os orçamentos da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    orcamentos_lib.gerar_orcamento(empresa_obj["_id"], collection_oportunidades, collection_empresas, collection_produtos, collection_contatos, usuario_ativo, permission_admin, st.experimental_user.email)
    
    elif selected == 'Negócios':
        st.header("💰 Negócios")
        #st.info('Consulte, cadastre e edite os seus negócios aqui.')
        st.write('----')
        if permission_admin: negocios_lib.gerenciamento_oportunidades(usuario_ativo, admin=True)
        else: negocios_lib.gerenciamento_oportunidades(usuario_ativo, admin=False)
        
    elif selected == 'Templates':
        st.header("📎 Templates")
        #st.info('Consulte, cadastre e edite os templates da HYGGE.')
        st.write('----')
        if permission_admin: templates_lib.gerenciamento_templates()
        else: st.warning("Você não tem permissão para alterar templates.")


    elif selected == 'Produtos':
        st.header("📚 Produtos")
        #st.info('Consulte, cadastre e edite os produtos da HYGGE.')
        st.write('----')
        if permission_admin: produtos_lib.gerenciamento_produtos()
        else: st.warning("Você não tem permissão para alterar produtos.")

    elif selected == 'Usuários':
        st.header("🧑‍💻 Usuários")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if permission_admin: usuarios_lib.gerenciamento_usuarios()
        else: st.warning("Você não tem permissão para alterar usuários.")
    
    elif selected == 'Solicitações':
        st.header("✅ Solicitação de aprovação")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if permission_admin: aprovacoes_lib.gerenciamento_aprovacoes()
        else: st.warning("Você não tem permissão para aprovar solicitações.")