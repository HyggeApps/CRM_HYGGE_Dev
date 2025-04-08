import streamlit as st
import pandas as pd
from utils.database import get_collection
import re
import datetime
from concurrent.futures import ThreadPoolExecutor

@st.fragment
def exibir_contatos_empresa(user, admin, empresa_id):
    collection_contatos = get_collection("contatos")
    collection_empresas = get_collection("empresas")

    # Executa as buscas em paralelo
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_contatos = executor.submit(collection_contatos.find, {"empresa_id": empresa_id}, {"_id": 0})
        future_empresa = executor.submit(collection_empresas.find_one, {"_id": empresa_id}, {"_id": 0, "razao_social": 1})
        contatos = list(future_contatos.result())
        empresa = future_empresa.result()
    
    nome_empresa = empresa["razao_social"] if empresa else "Empresa não encontrada"

    # Verifica permissão para adicionar, editar ou remover contatos
    if admin or (user == st.session_state["empresa_selecionada"]["Vendedor"]):

        with st.popover('➕ Adicionar Contato'):
            with st.form("form_adicionar_contato"):
                st.subheader("➕ Adicionar Contato")
                
                # Criar duas colunas para organização do formulário
                col1, col2 = st.columns(2)

                with col1:
                    nome = st.text_input("Nome *")
                    cargo = st.text_input("Cargo")
                    telefone = st.text_input("Telefone")
                with col2:
                    sobrenome = st.text_input("Sobrenome")
                    email = st.text_input("E-mail *")

                submit_adicionar = st.form_submit_button("✅ Adicionar Contato")

                if submit_adicionar:
                    # Verificar se o contato já existe em outra empresa
                    contato_existente = collection_contatos.find_one({"email": email})
                    if contato_existente and contato_existente["empresa_id"] != empresa_id:
                        st.error(f"Erro: O contato '{email}' já está vinculado ao banco de dados na empresa '{contato_existente['empresa']}'!")
                    else:
                        # Adicionar contato APENAS à empresa selecionada
                        collection_contatos.insert_one({
                            "nome": nome,
                            "sobrenome": sobrenome,
                            "cargo": cargo,
                            "email": email,
                            "fone": telefone,
                            "empresa": nome_empresa,
                            "empresa_id": empresa_id
                        })
                        # Atualizar a última atividade da empresa
                        collection_empresas.update_one(
                            {"_id": empresa_id},
                            {"$set": {"ultima_atividade": datetime.datetime.now().strftime("%Y-%m-%d")}}
                        )
                        st.success("Contato adicionado com sucesso!")
                        st.rerun()
                        
        # Se houver contatos cadastrados, exibir opções de edição/remoção
        if contatos:
            with st.popover('✏️ Editar contato'):
                contato_selecionado = st.selectbox(
                    "Selecione um contato para editar/remover",
                    options=[f"{c['nome']} {c['sobrenome']}" for c in contatos]
                )

                if contato_selecionado:
                    parts = contato_selecionado.split(" ", 1)
                    nome_selecionado = parts[0]
                    sobrenome_selecionado = parts[1] if len(parts) > 1 else ""

                    contato_dados = collection_contatos.find_one(
                        {"nome": nome_selecionado, "sobrenome": sobrenome_selecionado, "empresa_id": empresa_id},
                        {"_id": 0}
                    )

                    if contato_dados:
                        with st.form("form_editar_contato"):
                            st.subheader("✏️ Editar Contato")
                            col1, col2 = st.columns(2)

                            with col1:
                                nome_edit = st.text_input("Nome", value=contato_dados.get("nome", ""))
                                cargo_edit = st.text_input("Cargo", value=contato_dados.get("cargo", ""))
                                telefone_edit = st.text_input("Telefone", value=contato_dados.get("fone", ""))
                            with col2:
                                sobrenome_edit = st.text_input("Sobrenome", value=contato_dados.get("sobrenome", ""))
                                email_edit = st.text_input("E-mail", value=contato_dados.get("email", ""))

                            submit_editar = st.form_submit_button("💾 Salvar Alterações")

                            if submit_editar:
                                collection_contatos.update_one(
                                    {"nome": contato_dados["nome"], "sobrenome": contato_dados["sobrenome"], "empresa_id": empresa_id},
                                    {"$set": {
                                        "nome": nome_edit,
                                        "sobrenome": sobrenome_edit,
                                        "cargo": cargo_edit,
                                        "fone": telefone_edit,
                                        "email": email_edit
                                    }}
                                )
                                collection_empresas.update_one(
                                    {"_id": empresa_id},
                                    {"$set": {"ultima_atividade": datetime.datetime.now().strftime("%Y-%m-%d")}}
                                )
                                st.success("Contato atualizado com sucesso!")
                                st.rerun()
                                
                    if st.button("🗑️ Remover Contato"):
                        collection_contatos.delete_one(
                            {"nome": contato_dados["nome"], "sobrenome": contato_dados["sobrenome"], "empresa_id": empresa_id}
                        )
                        collection_empresas.update_one(
                            {"_id": empresa_id},
                            {"$set": {"ultima_atividade": datetime.datetime.now().strftime("%Y-%m-%d")}}
                        )
                        st.success(f"Contato {contato_selecionado} removido com sucesso!")
                        st.rerun()
                        
    # Atualiza a lista de contatos após alterações
    contatos = list(collection_contatos.find({"empresa_id": empresa_id}, {"_id": 0}))
    with st.expander("📞 Contatos cadastrados", expanded=True):
        if contatos:
            df_contatos = pd.DataFrame(contatos)
            df_contatos = df_contatos.rename(
                columns={
                    "nome": "Nome",
                    "sobrenome": "Sobrenome",
                    "cargo": "Cargo",
                    "email": "E-mail",
                    "fone": "Telefone"
                }
            )
            df_contatos = df_contatos[["Nome", "Sobrenome", "Cargo", "E-mail", "Telefone"]]
            st.dataframe(df_contatos, hide_index=True, use_container_width=True)
        else:
            st.warning("Nenhum contato cadastrado para esta empresa.")

@st.fragment
def exibir_todos_contatos_empresa():
    collection_contatos = get_collection("contatos")
    collection_empresas = get_collection("empresas")
    collection_usuarios = get_collection("usuarios")

    # Busca os dados das coleções em paralelo
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_contatos = executor.submit(collection_contatos.find, {}, {"_id": 0})
        future_empresas = executor.submit(
            collection_empresas.find,
            {},
            {"_id": 0, "razao_social": 1, "proprietario": 1, "ultima_atividade": 1}
        )
        contatos = list(future_contatos.result())
        empresas = list(future_empresas.result())

    df_contatos = pd.DataFrame(contatos)
    df_empresas = pd.DataFrame(empresas)

    if "empresa" not in df_contatos.columns:
        df_contatos["empresa"] = "Sem Empresa"
    else:
        df_contatos["empresa"] = df_contatos["empresa"].fillna("Sem Empresa")

    df_empresas.rename(columns={"razao_social": "Empresa", "proprietario": "Usuário"}, inplace=True)
    df_contatos["empresa_lower"] = df_contatos["empresa"].str.lower()
    df_empresas["Empresa_lower"] = df_empresas["Empresa"].str.lower()

    df_merged = df_contatos.merge(
        df_empresas[["Empresa_lower", "Usuário", "ultima_atividade"]],
        left_on="empresa_lower",
        right_on="Empresa_lower",
        how="left"
    )
    df_merged.drop(columns=["empresa_lower", "Empresa_lower"], inplace=True)
    df_merged = df_merged.rename(columns={
        "nome": "Nome",
        "sobrenome": "Sobrenome",
        "cargo": "Cargo",
        "email": "E-mail",
        "fone": "Telefone",
        "ultima_atividade": "Última atividade",
        "empresa": "Empresa"
    })

    col_order = ["Nome", "Sobrenome", "Empresa", "Usuário", "Última atividade", "Cargo", "E-mail", "Telefone"]
    col_order = [col for col in col_order if col in df_merged.columns]
    df_final = df_merged[col_order]

    filtro_busca = st.text_input(
        "🔍 Buscar Contato ou Empresa:",
        placeholder="Digite e pressione Enter",
        key="busca_unica"
    )

    if filtro_busca:
        filtro_normalizado = re.sub(r"\s+", " ", filtro_busca.strip().lower())
        df_final["busca_concat"] = (
            df_final["Nome"].fillna("") + " " +
            df_final["Sobrenome"].fillna("") + " " +
            df_final["Empresa"].fillna("")
        ).str.lower().apply(lambda x: re.sub(r"\s+", " ", x))
        df_final = df_final[df_final["busca_concat"].str.contains(filtro_normalizado, na=False)]
    
    if "busca_concat" in df_final.columns:
        df_final.drop(columns=["busca_concat"], inplace=True)

    # Prepara lista de empresas para o dropdown
    companies_docs = list(collection_empresas.find({}, {"razao_social": 1, "_id": 0}))
    company_list = [c["Empresa"] if "Empresa" in c else c["razao_social"] for c in companies_docs]
    if not company_list:
        company_list = ["Sem Empresa"]

    # Prepara lista de vendedores disponíveis para o dropdown
    vendedores_docs = list(collection_usuarios.find({}, {"nome": 1, "sobrenome": 1, "_id": 0}))
    vendedores = [v["nome"] + " " + v["sobrenome"] for v in vendedores_docs]
    if not vendedores:
        vendedores = [""]
    # Adiciona flag de edição se não existir no DataFrame
    if "Editar" not in df_final.columns:
        df_final["Editar"] = False

    # Reordena as colunas colocando "Editar" como a primeira
    cols = ["Editar"] + [col for col in df_final.columns if col != "Editar"]
    df_final = df_final[cols]

    # retira do DF as colunas Usuário, 

    with st.form("form_edicao_contatos"):
        # Exibe editor com coluna configurada para Empresa, Usuário e flag de edição
        edited_df = st.data_editor(
            df_final,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Empresa": st.column_config.SelectboxColumn(
                    options=company_list,
                    help="Selecione a empresa"
                ),
                "Editar": st.column_config.CheckboxColumn(
                    help="Marque para prosseguir com a edição"
                )
            }
        )

        submit = st.form_submit_button("💾 Salvar alterações")

    if submit:
        # Verifica se existe a coluna de flag "Editar" e filtra apenas os registros marcados
        if "Editar" in edited_df.columns:
            edited_rows = edited_df[edited_df["Editar"] == True]
        else:
            st.warning("Nenhuma linha marcada para edição.")
            edited_rows = pd.DataFrame()

        for index, row in edited_rows.iterrows():
            # Busca o registro da empresa para identificar o empresa_id com base no _id
            empresa_info = collection_empresas.find_one({"razao_social": row["Empresa"]})
            empresa_id_valor = empresa_info["_id"] if empresa_info else None

            # Atualiza o contato na coleção identificando-o pelo e-mail
            collection_contatos.update_one(
                {"email": row["E-mail"]},
                {"$set": {
                    "nome": row["Nome"],
                    "sobrenome": row["Sobrenome"],
                    "cargo": row["Cargo"],
                    "fone": row["Telefone"],
                    "email": row["E-mail"],
                    "empresa": row["Empresa"],
                    "empresa_id": empresa_id_valor
                }}
            )
            # Atualiza o proprietário (Usuário) e a última atividade na empresa associada
            collection_empresas.update_one(
                {"razao_social": row["Empresa"]},
                {"$set": {
                    "ultima_atividade": datetime.datetime.now().strftime("%Y-%m-%d")
                }}
            )
        if not edited_rows.empty:
            st.success("Alterações salvas com sucesso!")
        else:
            st.info("Nenhuma alteração marcada para salvar.")
