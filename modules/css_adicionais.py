import streamlit as st

def page_config():
    st.set_page_config(page_title="HYGGE | CRM - Ambiente Comercial",
    page_icon='https://hygge.eco.br/wp-content/uploads/2022/06/Logo_site.png',
    layout="wide")

    image1 = 'https://hygge.eco.br/wp-content/uploads/2025/03/marrom_escolhido.png'
    image_width_percent = 60

    html_code1 = f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 100%; ">
            <img src="{image1}" alt="Image" style="width: {image_width_percent}%;"/>
        </div>
    """
    st.sidebar.markdown(html_code1, unsafe_allow_html=True)


    image2 = 'https://hygge.eco.br/wp-content/uploads/2025/03/RECORTADO-MARROM-SLOGAN.png'
    image_width_percent = 80

    html_code2 = f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 100%; ">
            <img src="{image2}" alt="Image" style="width: {image_width_percent}%;"/>
        </div>
    """
    st.sidebar.markdown(html_code2, unsafe_allow_html=True)

    custom_css = """
        <style>
        .main {
            max-width: 80%;
            margin: 0 auto;
        }
        section[data-testid="stSidebar"] {
            width: 400px !important;
        }
        </style>
    """

    st.sidebar.write('----')
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