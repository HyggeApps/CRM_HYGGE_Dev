import streamlit as st
from utils.database import get_collection
import pandas as pd
import time

@st.fragment
def gerenciamento_usuarios():
    collection = get_collection("usuarios")
    # Abas para gerenciar usuários
    tab1, tab2, tab3, tab4 = st.tabs(["Cadastrar Usuário", "Remover Usuário", "Alterar Usuário", "Exibir Usuários"])

    # Aba: Cadastrar Usuário
    with tab1:
        st.subheader("Cadastrar Usuário")
        with st.form(key="form_cadastro_usuario"):  # Key única para o formulário
            nome = st.text_input("Nome *", key="input_nome_usuario")
            sobrenome = st.text_input("Sobrenome *", key="input_sobrenome_usuario")
            email = st.text_input("Email *", key="input_email_usuario")
            fone = st.text_input("Telefone", key="input_fone_usuario")
            setor = st.text_input("Setor", key="input_setor_usuario")
            hierarquia = st.selectbox("Hierarquia", ["admin", "viewer", "editor"], key="input_hierarquia_usuario")

            submit = st.form_submit_button("Cadastrar")

            if submit:
                if nome and sobrenome and email:
                    # Verificar duplicidade no banco de dados
                    existing_user = collection.find_one({"$or": [{"email": email}]})
                    if existing_user:
                        st.error("Usuário já cadastrado com este email!")
                    else:
                        # Criar o documento
                        document = {
                            "nome": nome,
                            "sobrenome": sobrenome,
                            "email": email,
                            "fone": fone,
                            "setor": setor,
                            "hierarquia": hierarquia,
                        }
                        collection.insert_one(document)
                        
                        st.success("Usuário cadastrado com sucesso!")
                        
                        
                        
                else:
                    st.error("Preencha todos os campos obrigatórios (Nome, Sobrenome e Email).")

    # Aba: Remover Usuário
    with tab2:
        st.subheader("Remover Usuário")

        # Obter todos os usuários cadastrados
        users = list(collection.find({}, {"_id": 0,"nome": 1, "email": 1}))
        opcoes_usuarios = [f"{user['nome']} ({user['email']})" for user in users]

        if not opcoes_usuarios:
            st.warning("Nenhum usuário encontrado. Cadastre usuários antes de tentar removê-los.")
        else:
            with st.form(key="form_remover_usuario"):
                usuario_selecionado = st.selectbox("Selecione o Usuário a Remover", options=opcoes_usuarios, key="select_remover_usuario")
                remove_submit = st.form_submit_button("Remover Usuário")

                if remove_submit:
                    if usuario_selecionado:
                        email = usuario_selecionado.split(" ")[0]
                        result = collection.delete_one({"email": email})
                        if result.deleted_count > 0:
                            st.success(f"Usuário com Email '{email}' removido com sucesso!")
                            
                        else:
                            st.error(f"Nenhum usuário encontrado com o Email '{email}'.")

    # Aba: Alterar Usuário
    with tab3:
        st.subheader("Alterar Usuário")

        # Obter todos os usuários cadastrados
        users = list(collection.find({}, {"_id": 0, "email": 1, "nome": 1, "sobrenome": 1, "fone": 1, "setor": 1, "hierarquia": 1}))
        opcoes_usuarios = [f"{user['email']}" for user in users]

        if not opcoes_usuarios:
            st.warning("Nenhum usuário encontrado. Cadastre usuários antes de tentar alterá-los.")
        else:
            usuario_selecionado = st.selectbox("Selecione o Usuário para Alterar", options=opcoes_usuarios, key="select_alterar_usuario")
            if usuario_selecionado:
                usuario = next(user for user in users if user['email'] == usuario_selecionado)
                with st.form(key="form_alterar_usuario"):
                    nome = st.text_input("Nome", value=usuario['nome'])
                    sobrenome = st.text_input("Sobrenome", value=usuario['sobrenome'])
                    fone = st.text_input("Telefone", value=usuario['fone'])
                    setor = st.text_input("Setor", value=usuario['setor'])
                    hierarquia = st.selectbox("Hierarquia", ["admin", "viewer", "editor"], index=["admin", "viewer", "editor"].index(usuario['hierarquia']))

                    submit = st.form_submit_button("Alterar Usuário")

                    if submit:
                        collection.update_one(
                            {"email": usuario_selecionado},
                            {"$set": {
                                "nome": nome,
                                "sobrenome": sobrenome,
                                "fone": fone,
                                "setor": setor,
                                "hierarquia": hierarquia
                            }}
                        )
                        
                        st.success(f"Usuário '{nome} {sobrenome}' atualizado com sucesso!")
                        
                                                    

    # Aba: Exibir Usuários
    with tab4:
        st.subheader("Usuários Cadastrados")
        users = list(collection.find({}, {"_id": 0}))
        if users:
            import pandas as pd
            df_users = pd.DataFrame(users)
            if 'senha' in df_users.columns:
                df_users = df_users.drop(columns=['senha'])
            st.dataframe(df_users, use_container_width=True)
        else:
            st.write("Nenhum usuário cadastrado ainda.")


