import streamlit as st
from msal import ConfidentialClientApplication
import requests
import smtplib

from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import streamlit as st
from modules import (
    usuarios,
    empresas,
    tarefas,
    meus_numeros,
    contatos,
    templates,
    produtos,
    negocios,
    orcamentos,
    aprovacoes
)
from utils import functions as funcs
from streamlit_authenticator.utilities import (CredentialsError,
                                               ForgotError,
                                               Hasher,
                                               LoginError,
                                               RegisterError,
                                               ResetError,
                                               UpdateError)
import json
from utils.database import get_collection
from streamlit_option_menu import option_menu


# Configuração da página
st.set_page_config(
    page_title='CRM HYGGE', layout='wide',
    page_icon='https://hygge.eco.br/wp-content/uploads/2022/06/Logo_site.png'
)

image1 = 'https://hygge.eco.br/wp-content/uploads/2024/07/white.png'
image_width_percent = 40

html_code1 = f"""
    <div style="display: flex; justify-content: center; align-items: center; height: 100%; ">
        <img src="{image1}" alt="Image" style="width: {image_width_percent}%;"/>
    </div>
"""
st.sidebar.markdown(html_code1, unsafe_allow_html=True)

css = '''
    <style>
        /* Seleciona o container do conteúdo do st.popover */
        [data-testid="stPopover"] > div:nth-child(2) {
            overflow-y: auto;
            max-height: 800px;
        }
    </style>
    '''
st.markdown(css, unsafe_allow_html=True)

css = '''
    <style>
        [data-testid="stExpander"] div:has(>.streamlit-expanderContent) {
            overflow-y: auto;
            max-height: 400px;
        }
    </style>
    '''
st.markdown(css, unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stForm {
        width: 95% !important; /* Ajusta a largura do formulário */
        margin: auto; /* Centraliza o formulário */
        padding: 10px; /* Adiciona mais espaço interno */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Adicionando CSS personalizado
st.markdown(
    """
    <style>
    /* Ajustar o tamanho da fonte global */
    html, body, [class*="css"] {
        font-size: 0.875rem !important; /* Reduz a fonte em 2pt */
    }

    /* Opcional: Ajustar fontes específicas */
    h1 {
        font-size: 2.75rem !important; /* Tamanho para H1 */
    }
    h2 {
        font-size: 2.5rem !important; /* Tamanho para H2 */
    }
    h3 {
        font-size: 1.25rem !important; /* Tamanho para H3 */
    }
    .stButton > button {
        font-size: 0.875rem !important; /* Botões */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Adicionando CSS personalizado para ajustar o tamanho da fonte
st.markdown(
    """
    <style>
    /* Ajustar o tamanho da fonte do menu */
    .nav-link {
        font-size: 8px !important; /* Tamanho da fonte desejado */
    }
    .nav-link i {
        font-size: 10px !important; /* Ajustar o tamanho do ícone, se necessário */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

css = """
<style>
    /* Aplica rolagem ao conteúdo dentro dos expanders */
    div[data-testid="stExpanderDetails"] {
        max-height: 500px !important;  /* Altura máxima antes do scroll */
        overflow-y: auto !important;  /* Força a rolagem vertical */
    }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

st.sidebar.markdown('------')

# Criar um arquivo temporário com os usuários do MongoDB
collection_usuarios = get_collection("usuarios")
temp_config_path = funcs.create_temp_config_from_mongo(collection_usuarios)
config_data = funcs.load_config_and_check_or_insert_cookies(temp_config_path)


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
                ["Tarefas", "Empresas", "Contatos", "Negócios", "Orçamentos", "Aceites", "Templates", "Produtos", "Usuários", "Solicitações", "Indicadores"],
                icons=["list-task", "building", "person-lines-fill", "currency-dollar", "calculator-fill", "bag-check", "file-earmark-text", "archive", "person-add", "check2-square","speedometer"],
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
                f"CRM HYGGE (Admin)",
                ["Tarefas", "Empresas", "Contatos", "Negócios", "Orçamentos", "Aceites", "Templates", "Produtos", "Usuários", "Solicitações", "Indicadores"],
                icons=["list-task", "building", "person-lines-fill", "currency-dollar", "calculator-fill", "bag-check", "file-earmark-text", "archive", "person-add", "check2-square","speedometer"],
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

    if selected == "Tarefas":
        st.header("📜 Tarefas")
        #st.info('Acompanhe aqui suas tarefas e seus números.')

        tela_tarefas, tela_stats = st.tabs(['Minhas tarefas', 'Meus números'])
        with tela_tarefas:
            if 'admin' in st.session_state["roles"]: tarefas.gerenciamento_tarefas_por_usuario(usuario_ativo,admin=True)
            else: tarefas.gerenciamento_tarefas_por_usuario(usuario_ativo,admin=False)
        with tela_stats:
            st.info('Em desenvolvimento...')
            #meus_numeros.compilar_meus_numeros(usuario_ativo)
    elif selected == "Empresas":
        st.header("🏢 Empresas")
        #st.info('Consulte, cadastre e edite suas empresas.')
        st.write('----')

        with st.popover("➕ Cadastrar empresa"):
            if 'admin' in st.session_state["roles"]: empresas.cadastrar_empresas(usuario_ativo,admin=True)
            else: empresas.cadastrar_empresas(usuario_ativo,admin=False)

        if 'admin' in st.session_state["roles"]:  empresas.consultar_empresas(usuario_ativo, admin=True)
        else: empresas.consultar_empresas(usuario_ativo, admin=False)

        
    elif selected == 'Contatos':
        st.header("📞 Contatos")
        #st.info('Consulte contatos aqui.')
        st.warning("⚠️ IMPORTANTE: O cadastro de contatos deve ser feito a partir da tela da 'Empresas'")
        st.write('----')
        contatos.exibir_todos_contatos_empresa()
        
    elif selected == 'Negócios':
        st.header("💰 Negócios")
        #st.info('Consulte, cadastre e edite os seus negócios aqui.')
        st.write('----')
        negocios.gerenciamento_oportunidades(usuario_ativo)
        
    elif selected == 'Orçamentos':
        st.header("📠 Orçamentos")
        #st.info('Consulte, cadastre e edite os seus negócios aqui.')
        st.write('----')
        orcamentos.elaborar_orcamento(usuario_ativo, st.session_state['email'], st.session_state['senha'])
        
    elif selected == 'Templates':
        st.header("📎 Templates")
        #st.info('Consulte, cadastre e edite os templates da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: templates.gerenciamento_templates()
        else: st.warning("Você não tem permissão para alterar templates.")


    elif selected == 'Produtos':
        st.header("📚 Produtos")
        #st.info('Consulte, cadastre e edite os produtos da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: produtos.gerenciamento_produtos()
        else: st.warning("Você não tem permissão para alterar produtos.")

    elif selected == 'Usuários':
        st.header("🧑‍💻 Usuários")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: usuarios.gerenciamento_usuarios()
        else: st.warning("Você não tem permissão para alterar usuários.")
    
    elif selected == 'Solicitações':
        st.header("✅ Solicitação de aprovação")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        if 'admin' in st.session_state["roles"]: aprovacoes.gerenciamento_aprovacoes()
        else: st.warning("Você não tem permissão para aprovar solicitações.")
    
    elif selected == 'Aceites':
        st.header("✒️ Aceite de propostas")
        #st.info('Consulte, cadastre e edite os usuários da HYGGE.')
        st.write('----')
        orcamentos.gerenciamento_aceites(usuario_ativo, st.session_state['email'], st.session_state['senha'])
        
