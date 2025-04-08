import streamlit as st
from msal import ConfidentialClientApplication
import requests
import smtplib
import pandas as pd
import utils.database as db
from streamlit_slickgrid import slickgrid
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
    atividades as atividades_lib,
)
import modules.css_adicionais as css_adicionais
import modules.slickgrids as sl
import utils.functions as funcs
from streamlit_option_menu import option_menu
from bson import ObjectId
import concurrent.futures

css_adicionais.page_config()

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

def build_map(data_list, key):
    result = {}
    for item in data_list:
        result.setdefault(item[key], []).append(item)
    return result

def get_data():
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

        # Construir os mapeamentos em paralelo
        future_contatos_map = executor.submit(build_map, contatos, "empresa_id")
        future_tarefas_map = executor.submit(build_map, tarefas, "empresa_id")
        future_atividades_map = executor.submit(build_map, atividades, "empresa_id")
        future_oportunidades_map = executor.submit(build_map, oportunidades, "empresa_id")

        contatos_map = future_contatos_map.result()
        tarefas_map = future_tarefas_map.result()
        atividades_map = future_atividades_map.result()
        oportunidades_map = future_oportunidades_map.result()

    return empresas, contatos, tarefas, atividades, oportunidades, contatos_map, tarefas_map, atividades_map, oportunidades_map

empresas, contatos, tarefas, atividades, oportunidades, contatos_map, tarefas_map, atividades_map, oportunidades_map = get_data()

if not st.experimental_user.is_logged_in:
    if st.sidebar.button("Fazer login com a Microsoft", use_container_width=True):
        st.login("microsoft")

# Bloco executado para o usuário logado
if st.experimental_user.is_logged_in and "@hygge.eco.br" in st.experimental_user.email:
    email_logado = st.experimental_user.email
    permission_admin = 'fabricio' in email_logado or 'alexandre' in email_logado or 'admin' in email_logado
    with st.sidebar:
        if permission_admin: 
            st.info(f'Bem-vindo(a), **{st.experimental_user.name}**!')
            st.info('Este é o ambiente de **admin** para consulta, preenchimento, controle e envio das informações referentes as oportunidades da HYGGE.')
            selected = option_menu(
                "CRM HYGGE (Admin)",
                ["Home", "Negócios", "Controle de orçamentos", "Templates", "Produtos", "Usuários", "Solicitações", "Indicadores"],
                icons=["house", "currency-dollar", "calculator-fill", "file-earmark-text", "archive", "person-add", "check2-square","speedometer"],
                menu_icon="cast",
                default_index=0,
                styles={
                    "menu-title": {"font-size": "16px", "font-weight": "bold"},
                    "nav-link": {"font-size": "12px"},
                    "nav-link-selected": {"font-size": "12px"},
                },
            )
        else:     
            st.info(f'Bem-vindo(a), **{st.experimental_user.name}**!')
            st.info('Este é o ambiente de **vendedor** para consulta, preenchimento, controle e envio das informações referentes as oportunidades da HYGGE.')
            selected = option_menu(
                "CRM HYGGE (Vendedor)",
                ["Home", "Negócios", "Contatos", "Indicadores"],
                icons=["house", "currency-dollar", "person-lines-fill","speedometer"],
                menu_icon="cast",
                default_index=0,
                styles={
                    "menu-title": {"font-size": "16px", "font-weight": "bold"},
                    "nav-link": {"font-size": "12px"},
                    "nav-link-selected": {"font-size": "12px"},
                },
            )
        if st.button("Logout", use_container_width=True):
            st.logout()

if st.experimental_user.is_logged_in and "@hygge.eco.br" in st.experimental_user.email:
    usuario_ativo = st.experimental_user.name
    # Obter informações da empresa com razao_social "Teste"
    collection_empresas = db.get_collection("empresas")
    empresa_Teste = collection_empresas.find_one({"razao_social": "Teste"})
    collection_contatos = db.get_collection("contatos")
    
    data, columns, options = sl.slickgrid_empresa(empresas, contatos_map)
    if selected == "Home":
        st.title("📜 Tarefas")
        st.info("Acompanhe na tabela abaixo as tarefas relacionadas às suas empresas.")
        with st.expander("Acompanhamento de tarefas", expanded=False):
            if permission_admin:
                tarefas_lib.gerenciamento_tarefas_por_usuario(usuario_ativo, admin=True)
            else:
                tarefas_lib.gerenciamento_tarefas_por_usuario(usuario_ativo, admin=False)

        st.write('----')
        st.title("🏢 Empresas")
        st.info("Pesquise e clique em uma empresa dentre as opções abaixo para consultar mais informações a respeito desta empresa.")
        with st.popover("➕ Cadastrar empresa", use_container_width=True):
            if permission_admin:
                empresas_lib.cadastrar_empresas(usuario_ativo, admin=True)
            else:
                empresas_lib.cadastrar_empresas(usuario_ativo, admin=False)
        st.write('----')
        out = slickgrid(data, columns, options, key="mygrid", on_click='rerun')
        if out is not None:
            st.session_state.selected_row = out[0]

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
                        with st.expander("Informações da empresa", expanded=True):
                            exibir_dados.infos_empresa(empresa_obj, collection_empresas, collection_usuarios, usuario_ativo, admin=permission_admin)
                    else:
                        st.write("Informações da empresa não disponíveis para linhas detalhadas.")

                with tabs[1]:
                    st.header("👥 Contatos da empresa")
                    st.info("Consulte e edite os contatos da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    exibir_dados.infos_contatos(contatos_map.get(empresa_id, []), collection_contatos, collection_empresas, usuario_ativo, admin=permission_admin)

                with tabs[2]:
                    st.header("📝 Tarefas e Atividades da empresa")
                    st.info("Consulte e edite as tarefas e atividades da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    tarefas_lib.gerenciamento_tarefas(usuario_ativo, empresa_id, admin=permission_admin)
                    st.write('----')
                    atividades_lib.exibir_atividades_empresa(usuario_ativo, admin=permission_admin, empresa_id=empresa_id)
                    st.write('----')
                with tabs[3]:
                    st.header("💰 Negócios da empresa")
                    st.info("Consulte e edite os negócios da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    tabs_negocios = st.tabs(["Visualizar negócios", "Adicionar negócio", "Editar negócio"])
                    with tabs_negocios[0]:
                        exibir_dados.infos_negocios(oportunidades_map.get(empresa_id, []), collection_negocios)
                    with tabs_negocios[1]:
                        negócios_admin = permission_admin
                        negocios_lib.cadastrar_negocio(
                            empresa_obj["_id"], collection_empresas, collection_usuarios,
                            collection_produtos, collection_oportunidades, collection_atividades,
                            usuario_ativo, admin=negócios_admin
                        )
                    with tabs_negocios[2]:
                        negócios_admin = permission_admin
                        negocios_lib.editar_negocio(
                            empresa_obj["_id"], collection_oportunidades, collection_empresas,
                            collection_atividades, usuario_ativo, admin=negócios_admin
                        )
                with tabs[4]:
                    st.header("💰 Orçamentos da empresa")
                    st.info("Consulte e edite os orçamentos da empresa (caso seja proprietário ou admin) nos campos abaixo.")
                    st.write('----')
                    orcamentos_lib.gerar_orcamento(
                        empresa_obj["_id"], collection_oportunidades, collection_empresas,
                        collection_produtos, collection_contatos, usuario_ativo, permission_admin, st.experimental_user.email
                    )
    
    elif selected == 'Negócios':
        st.header("💰 Negócios")
        st.write('----')
        negócios_admin = permission_admin
        negocios_lib.gerenciamento_oportunidades(usuario_ativo, admin=negócios_admin)
        
    elif selected == 'Templates':
        st.header("📎 Templates")
        st.write('----')
        if permission_admin:
            templates_lib.gerenciamento_templates()
        else:
            st.warning("Você não tem permissão para alterar templates.")

    elif selected == 'Produtos':
        st.header("📚 Produtos")
        st.write('----')
        if permission_admin:
            produtos_lib.gerenciamento_produtos()
        else:
            st.warning("Você não tem permissão para alterar produtos.")

    elif selected == 'Usuários':
        st.header("🧑‍💻 Usuários")
        st.write('----')
        if permission_admin:
            usuarios_lib.gerenciamento_usuarios()
        else:
            st.warning("Você não tem permissão para alterar usuários.")
    
    elif selected == 'Solicitações':
        st.header("✅ Solicitação de aprovação")
        st.write('----')
        if permission_admin:
            aprovacoes_lib.gerenciamento_aprovacoes()
        else:
            st.warning("Você não tem permissão para aprovar solicitações.")
    
    elif selected == 'Contatos':
        st.header("👥 Contatos")
        st.write('----')
        contatos_admin = permission_admin
        contatos_lib.exibir_todos_contatos_empresa()
