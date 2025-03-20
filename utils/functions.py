import tempfile
import yaml
import bcrypt
from pymongo.collection import Collection

def create_temp_config_from_mongo(collection_users: Collection) -> str:
    """
    Cria um arquivo de configuração temporário a partir dos dados de usuários armazenados no MongoDB.
    
    Parâmetros:
        collection_users (Collection): Conexão com a coleção de usuários no MongoDB.

    Retorna:
        str: Caminho do arquivo de configuração temporário gerado.
    """
    # Buscar todos os usuários no MongoDB
    users_data = collection_users.find()

    # Criar um dicionário para armazenar os dados do config temporário
    temp_config_data = {
        'credentials': {
            'usernames': {}
        }
    }

    # Adicionar usuários do MongoDB ao config temporário
    for user_data in users_data:
        username = user_data.get('email', '')

        # Garantir que a senha está hasheada antes de armazenar (caso ainda não esteja)
        password = user_data.get('senha', '')
        if not password.startswith("$2b$"):  # Se não estiver hasheado, aplicar bcrypt
            password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Estrutura do usuário no formato do config.yaml
        user_yaml_data = {
            'email': username,
            'failed_login_attempts': 0,
            'first_name': user_data.get('nome', ''),
            'last_name': user_data.get('sobrenome', ''),
            'logged_in': False,
            'password': password,
            'roles': [user_data.get('hierarquia', 'viewer')]
        }

        # Adicionar o usuário ao config temporário
        temp_config_data['credentials']['usernames'][username] = user_yaml_data
        print(f"✅ Usuário {username} adicionado ao config temporário.")

    # Criar um arquivo temporário para salvar o config.yaml
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yaml', encoding='utf-8') as temp_file:
        yaml.dump(temp_config_data, temp_file, default_flow_style=False)
        temp_file_path = temp_file.name

    print(f"📁 Arquivo config temporário criado: {temp_file_path}")
    return temp_file_path

def load_config_and_check_or_insert_cookies(config_file_path: str) -> dict:
    """
    Carrega um arquivo de configuração YAML e garante que a seção de cookies exista.

    Parâmetros:
        config_file_path (str): Caminho do arquivo de configuração YAML.

    Retorna:
        dict: Configuração carregada e corrigida.
    """
    # Carregar o arquivo YAML existente
    try:
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file) or {}  # Garante que não seja None
    except FileNotFoundError:
        config_data = {}  # Se o arquivo não existir ainda

    # Garantir que a seção 'cookie' exista
    if 'cookie' not in config_data:
        config_data['cookie'] = {
            'expiry_days': 7,  # Definir um valor padrão de expiração
            'key': 'some_signature_key',
            'name': 'user_session_cookie'
        }
        print("⚠️ Seção 'cookie' criada com valores padrão.")

    # Garantir que a chave 'name' exista na seção 'cookie'
    if 'name' not in config_data['cookie']:
        config_data['cookie']['name'] = 'user_session_cookie'
        print("⚠️ Chave 'name' na seção 'cookie' criada com valor padrão.")

    # Salvar o arquivo atualizado
    with open(config_file_path, 'w', encoding='utf-8') as file:
        yaml.dump(config_data, file, default_flow_style=False)

    print("✅ Configuração carregada e corrigida.")
    return config_data
