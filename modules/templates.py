import streamlit as st
from utils.database import get_collection

def gerenciamento_templates():
    collection = get_collection("templates")

    # Abas para gerenciar templates
    tab1, tab2, tab3 = st.tabs(["Cadastrar Template", "Remover Template", "Exibir Templates"])

    # Aba: Cadastrar Template
    with tab1:
        st.subheader("Cadastrar Template")
        with st.form(key="form_cadastro_template"):
            nome = st.text_input("Nome do Template", key="input_nome_template")
            descricao = st.text_area("Descrição", key="input_descricao_template")
            temp_email = st.text_area("Template de Email", key="input_temp_email_template")

            submit = st.form_submit_button("Cadastrar")

            if submit:
                if nome:
                    # Verificar duplicidade no banco de dados
                    existing_template = collection.find_one({"nome": nome})
                    if existing_template:
                        st.error("Template já cadastrado com este nome!")
                    else:
                        # Criar o documento
                        document = {
                            "nome": nome,
                            "descricao": descricao,
                            "temp_email": temp_email,
                        }
                        collection.insert_one(document)
                        st.success("Template cadastrado com sucesso!")
                else:
                    st.error("Preencha todos os campos obrigatórios (Nome).")

    # Aba: Remover Template
    with tab2:
        st.subheader("Remover Template")
        with st.form(key="form_remover_template"):
            remove_nome = st.text_input("Nome do Template a Remover", key="input_remover_nome_template")
            remove_submit = st.form_submit_button("Remover Template")

            if remove_submit:
                if remove_nome:
                    # Verificar se o template existe e remover
                    result = collection.delete_one({"nome": remove_nome})
                    if result.deleted_count > 0:
                        st.success(f"Template '{remove_nome}' removido com sucesso!")
                    else:
                        st.error(f"Nenhum template encontrado com o nome '{remove_nome}'.")
                else:
                    st.error("Por favor, insira o Nome do template para remover.")

    # Aba: Exibir Templates
    with tab3:
        st.subheader("Templates Cadastrados")
        templates = list(collection.find({}, {"_id": 0}))  # Excluir o campo "_id" ao exibir
        if templates:
            st.write("Lista de Templates:")
            for template in templates:
                st.write(
                    f"Nome: {template['nome']}, Descrição: {template['descricao']}, "
                    f"Template de Email: {template['temp_email']}"
                )
        else:
            st.write("Nenhum template cadastrado ainda.")
