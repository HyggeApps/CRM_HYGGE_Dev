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
css_adicionais.page_config()

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

# Carrega todas as empresas de uma vez
empresas = list(collection_empresas.find())
empresa_ids = [empresa["_id"] for empresa in empresas]

# Realiza consultas em lote usando "$in" para evitar consultas individuais
contatos = list(collection_contatos.find({"empresa_id": {"$in": empresa_ids}}))
tarefas = list(collection_tarefas.find({"empresa_id": {"$in": empresa_ids}}))
atividades = list(collection_atividades.find({"empresa_id": {"$in": empresa_ids}}))
oportunidades = list(collection_negocios.find({"empresa_id": {"$in": empresa_ids}}))

# Cria mapeamentos para acesso rápido
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

# Verifique se a sessão já tem uma chave 'logado'
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'name' not in st.session_state:     ### NEW OR UPDATED ###
    st.session_state['name'] = None
if 'lastname' not in st.session_state:     ### NEW OR UPDATED ###
    st.session_state['lastname'] = None
if 'email' not in st.session_state:    ### NEW OR UPDATED ###
    st.session_state['email'] = None
if 'roles' not in st.session_state:    ### NEW OR UPDATED ###
    st.session_state['roles'] = None
if 'senha' not in st.session_state:    ### NEW OR UPDATED ###
    st.session_state['senha'] = None

st.session_state['logado'] = True
st.session_state['name'] = "Alexandre"
st.session_state['lastname'] = "Castagini"
st.session_state['roles'] = "admin"
if not st.session_state['logado']:
    
    CLIENT_ID = str(st.secrets["azure"]["client_id"])
    CLIENT_SECRET = str(st.secrets["azure"]["client_secret"])
    TENANT_ID = str(st.secrets["azure"]["tenant_id"])

    AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
    SCOPE = ['https://graph.microsoft.com/.default']
    # Criar uma instância de aplicação
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY_URL, client_credential=CLIENT_SECRET)

    # Adquirir token
    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        # Usar o token de acesso para chamar o Microsoft Graph API
        token = result['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        url = 'https://graph.microsoft.com/v1.0/users'
        response = requests.get(url, headers=headers)
        users = response.json()
        emails = []
        for user in users.get('value', []):
            # Imprimir o endereço de e-mail do usuário
            emails.append(user.get('mail', 'No email found'))
    else:
        print(result.get("error"))
        print(result.get("error_description"))
    

    #st.sidebar.error('EM MANUTENÇÃO, AGUARDE...')
    #emails = ['rodrigo@hygge.eco.br']

    if 'AgendadoMatheus@hygge.eco.br' in emails:
        emails.remove('AgendadoMatheus@hygge.eco.br')
    if 'FabricioHygge@hygge.eco.br' in emails:
        emails.remove('FabricioHygge@hygge.eco.br')
    if 'ThiagoHygge@hygge.eco.br' in emails:
        emails.remove('ThiagoHygge@hygge.eco.br')

    #st.sidebar.error('🚨 EM MANUTENÇÃO!')
    
    email_principal = st.sidebar.selectbox("Email", emails)
    #email_principal = st.sidebar.selectbox("Email", ['admin@hygge.eco.br', 'rodrigo@hygge.eco.br'])
    senha_principal = st.sidebar.text_input("Senha", type="password")
    
    # If the user is not logged in, show the login button and login process
    if st.sidebar.button('Entrar'):
        try:
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(email_principal, senha_principal)
            st.sidebar.success("Login realizado com sucesso!")
            
            # Update the session state to logged in
            st.session_state['logado'] = True
            st.session_state['email'] = email_principal
            st.session_state['senha'] = senha_principal
            
            # ─────────────────────────────────────────────────────────────
            # Query your "usuarios" collection to map the email to a user
            # ─────────────────────────────────────────────────────────────
            user_data = collection_usuarios.find_one({"email": email_principal})
            if user_data:
                # e.g., user_data might contain { "username": "...", "name": "Rodrigo", "roles": ["admin"] }
                st.session_state["name"] = user_data.get("nome", "Sem Nome")
                st.session_state["lastname"] = user_data.get("sobrenome", "Sem sobreome")
                st.session_state["roles"] = user_data.get("hierarquia", "viewer")
                st.session_state["email"] = user_data.get("email", "Sem Email")
            else:
                # If no document found, set defaults
                st.session_state["name"] = "Usuário Desconhecido"
                st.session_state["lastname"] = "--"
                st.session_state["roles"] = "viewer"
                st.session_state["email"] = email_principal

        except Exception as e:
            st.sidebar.error("Falha no login, senha incorreta.")

# This part is executed if the user is logged in - LOGIN DO USUÁRIO
if st.session_state.get('logado', False):
    with st.sidebar:
        if 'admin' in st.session_state["roles"]: 
            st.info(f'Bem-vindo(a), **{st.session_state["name"]}**!')
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
            st.info(f'Bem-vindo(a), **{st.session_state["name"]}**!')
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
    usuario_ativo = f'{st.session_state["name"]} {st.session_state["lastname"]}'
    data, columns, options = sl.slickgrid_empresa(empresas, contatos, contatos_map)
    if selected == "Home":
        st.title("📜 Tarefas")
        st.info("Acompanhe na tabela abaixo as tarefas relacionadas às suas empresas.")
        with st.expander("Minhas tarefas", expanded=False):
            if 'admin' in st.session_state["roles"]: tarefas_lib.gerenciamento_tarefas_por_usuario(usuario_ativo,admin=True)
            else: tarefas_lib.gerenciamento_tarefas_por_usuario(usuario_ativo,admin=False)

        st.write('----')
        st.title("🏢 Empresas")
        st.info("Pesquise e clique em uma empresa dentre as opções abaixo para consultar mais informações a respeito desta empresa.")
        with st.popover("➕ Cadastrar empresa", use_container_width=True):
                if 'admin' in st.session_state["roles"]: empresas_lib.cadastrar_empresas(usuario_ativo,admin=True)
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
            tabs = st.tabs(["Informações", "Contatos", "Tarefas", "Atividades", "Negócios", "Orçamentos"])
            empresa_obj = next((empresa for empresa in empresas if empresa.get("razao_social", "") == item["empresa"]), None)
            if not empresa_obj:
                st.write("Empresa não encontrada.")
            else:
                empresa_id = empresa_obj["_id"]

                with tabs[0]:
                    if item.get("infos") is None:
                        if 'admin' in st.session_state["roles"]:
                            exibir_dados.infos_empresa(empresa_obj, collection_empresas, collection_usuarios, usuario_ativo, admin=True)
                        else:
                            exibir_dados.infos_empresa(empresa_obj, collection_empresas, collection_usuarios, usuario_ativo, admin=False)
                    else:
                        st.write("Informações da empresa não disponíveis para linhas detalhadas.")

                with tabs[1]:
                    if 'admin' in st.session_state["roles"]:
                        exibir_dados.infos_contatos(contatos_map.get(empresa_id, []), collection_contatos, collection_empresas, usuario_ativo, admin=True)
                    else:
                        exibir_dados.infos_contatos(contatos_map.get(empresa_id, []), collection_contatos, collection_empresas, usuario_ativo, admin=False)

                with tabs[2]:
                    exibir_dados.infos_tarefas(tarefas_map.get(empresa_id, []), collection_tarefas)

                with tabs[3]:
                    exibir_dados.infos_atividades(atividades_map.get(empresa_id, []), collection_atividades)

                with tabs[4]:
                    tabs_negocios = st.tabs(["Visualizar negócios", "Adicionar negócio", "Editar negócio"])
                    with tabs_negocios[0]:
                        exibir_dados.infos_negocios(oportunidades_map.get(empresa_id, []), collection_negocios)
                    with tabs_negocios[1]:
                        if 'admin' in st.session_state["roles"]:
                            negocios_lib.cadastrar_negocio(empresa_obj["_id"], collection_empresas,collection_usuarios, collection_produtos, collection_oportunidades, collection_atividades, usuario_ativo, admin=True)
                        else:
                            negocios_lib.cadastrar_negocio(empresa_obj["_id"], collection_empresas,collection_usuarios, collection_produtos, collection_oportunidades, collection_atividades, usuario_ativo, admin=False)
                    with tabs_negocios[2]:
                        if 'admin' in st.session_state["roles"]:
                            negocios_lib.editar_negocio(empresa_obj["_id"], collection_oportunidades, collection_empresas,collection_atividades, usuario_ativo, admin=True)
                        else:
                            negocios_lib.editar_negocio(empresa_obj["_id"], collection_oportunidades, collection_empresas,collection_atividades, usuario_ativo, admin=False)
                with tabs[5]:
                    tabs_orcamentos = st.tabs(["Visualizar orçamentos", "Adicionar orçamento", "Editar orçamento", "Aceite de orçamento"])
            
    elif selected == 'Negócios':
        st.header("💰 Negócios")
        #st.info('Consulte, cadastre e edite os seus negócios aqui.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: negocios_lib.gerenciamento_oportunidades(usuario_ativo, admin=True)
        else: negocios_lib.gerenciamento_oportunidades(usuario_ativo, admin=False)
        
    elif selected == 'Templates':
        st.header("📎 Templates")
        #st.info('Consulte, cadastre e edite os templates da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: templates_lib.gerenciamento_templates()
        else: st.warning("Você não tem permissão para alterar templates.")


    elif selected == 'Produtos':
        st.header("📚 Produtos")
        #st.info('Consulte, cadastre e edite os produtos da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: produtos_lib.gerenciamento_produtos()
        else: st.warning("Você não tem permissão para alterar produtos.")

    elif selected == 'Usuários':
        st.header("🧑‍💻 Usuários")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: usuarios_lib.gerenciamento_usuarios()
        else: st.warning("Você não tem permissão para alterar usuários.")
    
    elif selected == 'Solicitações':
        st.header("✅ Solicitação de aprovação")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: aprovacoes_lib.gerenciamento_aprovacoes()
        else: st.warning("Você não tem permissão para aprovar solicitações.")
    
    elif selected == 'Aceites':
        st.header("✒️ Aceite de propostas")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: orcamentos_lib.gerenciamento_aceites(usuario_ativo, st.session_state['email'], st.session_state['senha'], admin=True)
        else: orcamentos_lib.gerenciamento_aceites(usuario_ativo, st.session_state['email'], st.session_state['senha'], admin=False)