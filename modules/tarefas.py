import streamlit as st
from utils.database import get_collection
from datetime import datetime, timedelta, date
import pandas as pd
import random

def calcular_data_execucao(opcao):
    """Calcula a data de execução da tarefa com base na opção selecionada, considerando apenas dias úteis."""
    hoje = datetime.today().date()
    
    def adicionar_dias_uteis(dias):
        """Adiciona um número de dias úteis à data de hoje, ignorando finais de semana."""
        data = hoje
        while dias > 0:
            data += timedelta(days=1)
            if data.weekday() < 5:  # Apenas segunda a sexta-feira (0=Segunda, ..., 4=Sexta)
                dias -= 1
        return data

    opcoes_prazo = {
        "Hoje": hoje,
        "1 dia útil": adicionar_dias_uteis(1),  # Agora considera apenas dias úteis
        "2 dias úteis": adicionar_dias_uteis(2),
        "3 dias úteis": adicionar_dias_uteis(3),
        "1 semana": hoje + timedelta(weeks=1),
        "2 semanas": hoje + timedelta(weeks=2),
        "1 mês": hoje + timedelta(days=30),
        "2 meses": hoje + timedelta(days=60),
        "3 meses": hoje + timedelta(days=90)
    }
    
    return opcoes_prazo.get(opcao, hoje)

@st.fragment
def atualizar_status_tarefas(empresa_id):
    collection_tarefas = get_collection("tarefas")
    # 📌 Verificar e atualizar tarefas atrasadas automaticamente
    tarefas = list(collection_tarefas.find({"empresa_id": empresa_id}, {"_id": 0}))
    hoje = datetime.today().date()
    atualizacoes_realizadas = False

    for tarefa in tarefas:
        data_execucao = datetime.strptime(tarefa["data_execucao"], "%Y-%m-%d").date()
        if data_execucao < hoje and tarefa["status"] != "🟩 Concluída":
            
            collection_tarefas.update_one(
                {"empresa_id": empresa_id, "titulo": tarefa["titulo"]},
                {"$set": {"status": "🟥 Atrasado"}}
            )
    
    collection_tarefas = get_collection("tarefas")
    return collection_tarefas

@st.fragment
def gerenciamento_tarefas(user, empresa_id, admin):
    collection_tarefas = atualizar_status_tarefas(empresa_id)
    collection_atividades = get_collection("atividades")
    collection_empresas = get_collection("empresas")
    
    if not empresa_id:
        st.error("Erro: Nenhuma empresa selecionada para gerenciar tarefas.")
        return

    # Pega os dados da empresa, incluindo o status "empresa_ativa"
    empresa_info = collection_empresas.find_one(
        {"_id": empresa_id},
        {"_id": 0, "razao_social": 1, "empresa_ativa": 1}
    )
    if empresa_info.get("empresa_ativa", "Ativa") == "Inativa":
        st.info("Empresa inativa. Ignorando tarefas.")
        return
    nome_empresa = empresa_info["razao_social"]

    # 📌 Verificar e atualizar tarefas atrasadas automaticamente
    tarefas = list(collection_tarefas.find({"empresa_id": empresa_id}, {"_id": 0}))
    hoje = datetime.today().date()

    for tarefa in tarefas:
        data_execucao = datetime.strptime(tarefa["data_execucao"], "%Y-%m-%d").date()
        
        if data_execucao < hoje and tarefa["status"] != "🟩 Concluída":
            collection_tarefas.update_one(
                {"empresa_id": empresa_id, "titulo": tarefa["titulo"]},
                {"$set": {"status": "🟥 Atrasado"}}
            )

    # 📌 Botão para adicionar nova tarefa
    collection_empresas = get_collection("empresas")
    empresa = collection_empresas.find_one({"_id": empresa_id}, {"proprietario": 1})

    if not tarefas:
        if admin or (empresa and user == empresa.get("proprietario")):
            with st.popover('➕ Criar Tarefa'):
                with st.form("form_criar_tarefa"):
                    st.subheader("➕ Nova Tarefa")

                    titulo = st.text_input("Título da Tarefa *")
                    
                    prazo = st.selectbox("Prazo", ["Hoje", "1 dia útil", "2 dias úteis", "3 dias úteis", "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"], index=3)
                    
                    data_execucao = st.date_input("Data de Execução", value=calcular_data_execucao(prazo)) if prazo == "Personalizada" else calcular_data_execucao(prazo)
                    hoje = datetime.today().date()
                    status = "🟨 Em andamento"
                    observacoes = st.text_area("Observações da Tarefa")
                    prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], index=1)

                    submit_criar = st.form_submit_button("✅ Criar Tarefa")

                if submit_criar:
                    random_hex = f"{random.randint(0, 0xFFFF):04x}"
                    if titulo:
                        nova_tarefa = {
                            "titulo": f"{titulo} ({nome_empresa} - {random_hex})",
                            "empresa": nome_empresa,
                            "data_execucao": data_execucao.strftime("%Y-%m-%d"),
                            "observacoes": observacoes,
                            "status": status,
                            "hexa": random_hex,
                            "Prioridade": prioridade,
                            "empresa_id": empresa_id
                        }
                        collection_tarefas.insert_one(nova_tarefa)
                        
                        # 🔄 Atualizar a última atividade da empresa
                        data_hoje = datetime.now().strftime("%Y-%m-%d")  # Data atual
                        collection_empresas = get_collection("empresas")
                        collection_empresas.update_one(
                            {"cnpj": nome_empresa},
                            {"$set": {"ultima_atividade": data_hoje}}
                        )

                        st.success("Tarefa criada com sucesso!")
                        st.rerun()
                        
                    else:
                        st.error("Preencha o campo obrigatório: Título da Tarefa.")

    elif tarefas:
        df_tarefas = pd.DataFrame(tarefas)
        df_tarefas = df_tarefas.rename(
            columns={
                "titulo": "Título",
                "data_execucao": "Data de Execução",
                "observacoes": "Observações",
                "status": "Status"
            }
        )
        df_tarefas["Data de Execução"] = pd.to_datetime(df_tarefas["Data de Execução"], errors="coerce").dt.strftime("%d/%m/%Y")
        
        # Se o status já for concluída, define a flag como True (marcada)
        df_tarefas["Concluir"] = df_tarefas["Status"].apply(lambda s: True if s == "🟩 Concluída" else False)
        
        # Reordenar o DataFrame por "Data de Execução" (da mais recente para a mais antiga)
        df_tarefas["Data de Execução_sort"] = pd.to_datetime(df_tarefas["Data de Execução"], format="%d/%m/%Y")
        df_tarefas = df_tarefas.sort_values(by="Data de Execução_sort", ascending=False).drop(columns="Data de Execução_sort")
        
        # Ordenar o DataFrame conforme: atrasadas, depois em andamento e por último concluídas
        status_order = {"🟥 Atrasado": 0, "🟨 Em andamento": 1, "🟩 Concluída": 2}
        df_tarefas["StatusOrder"] = df_tarefas["Status"].map(status_order)
        df_tarefas = df_tarefas.sort_values(by=["StatusOrder", "Data de Execução"], ascending=[True, False]).drop(columns="StatusOrder")

        # Reordenar as colunas para colocar "Concluir" como a primeira
        df_tarefas = df_tarefas[["Concluir", "Status","Prioridade", "Data de Execução", "Título", "Observações"]]

        # Configurar a coluna como checkbox com largura menor
        column_config = {
            "Concluir": st.column_config.CheckboxColumn(
            "Concluir",
            help="Marque se desejar concluir esta tarefa hoje. Tarefas já concluídas aparecem marcadas e não podem ser alteradas.",
            width=5
            )
        }

        # Exibir o data editor com a coluna de checkbox para marcar as tarefas a concluir
        edited_df = st.data_editor(
            df_tarefas,
            hide_index=True,
            use_container_width=True,
            column_config=column_config
        )

        # Garantir que, mesmo que o usuário modifique, as tarefas já concluídas permaneçam com a flag True.
        edited_df.loc[edited_df["Status"] == "🟩 Concluída", "Concluir"] = True
        
        cols = st.columns(7)
        with cols[0]:
            if admin or (empresa and user == empresa.get("proprietario")):
                with st.popover('➕ Criar Tarefa', use_container_width=True):
                    with st.form("form_criar_tarefa"):
                        st.subheader("➕ Nova Tarefa")

                        titulo = st.text_input("Título da Tarefa *")
                        prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], index=1)
                        prazo = st.selectbox("Prazo", ["Hoje", "1 dia útil", "2 dias úteis", "3 dias úteis", "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"], index=3)
                        
                        data_execucao = st.date_input("Data de Execução", value=calcular_data_execucao(prazo)) if prazo == "Personalizada" else calcular_data_execucao(prazo)
                        hoje = datetime.today().date()
                        status = "🟨 Em andamento"
                        observacoes = st.text_area("Observações da Tarefa")

                        submit_criar = st.form_submit_button("✅ Criar Tarefa")

                    if submit_criar:
                        random_hex = f"{random.randint(0, 0xFFFF):04x}"
                        if titulo:
                            nova_tarefa = {
                                "titulo": f"{titulo} ({nome_empresa} - {random_hex})",
                                "empresa": nome_empresa,
                                "data_execucao": data_execucao.strftime("%Y-%m-%d"),
                                "Prioridade": prioridade,
                                "observacoes": observacoes,
                                "status": status,
                                "hexa": random_hex,
                                "empresa_id": empresa_id,
                            }
                            collection_tarefas.insert_one(nova_tarefa)
                            
                            # 🔄 Atualizar a última atividade da empresa
                            data_hoje = datetime.now().strftime("%Y-%m-%d")  # Data atual
                            collection_empresas = get_collection("empresas")
                            collection_empresas.update_one(
                                {"cnpj": nome_empresa},
                                {"$set": {"ultima_atividade": data_hoje}}
                            )

                            st.success("Tarefa criada com sucesso!")
                            st.rerun()
                            
                        else:
                            st.error("Preencha o campo obrigatório: Título da Tarefa.")
        with cols[1]:
            if admin or (empresa and user == empresa.get("proprietario")):
                # 📌 Popover para editar tarefas existentes
                with st.popover('✏️ Editar Tarefa', use_container_width=True):
                    # Filtrar apenas as tarefas que não estão concluídas
                    tarefas_nao_concluidas = [t for t in tarefas if t["status"] != "🟩 Concluída"]

                    tarefa_selecionada = st.selectbox(
                        "Selecione uma tarefa para editar",
                        options=[t["titulo"] for t in tarefas_nao_concluidas],  # Apenas tarefas em andamento ou atrasadas
                        key="select_editar_tarefa"
                    )

                    if tarefa_selecionada:
                        tarefa_dados = collection_tarefas.find_one({"empresa_id": empresa_id, "titulo": tarefa_selecionada}, {"_id": 0})
                        if tarefa_dados:
                            with st.form("form_editar_tarefa",):
                                st.subheader("✏️ Editar Tarefa")
                                titulo_edit = st.text_input("Título", value=tarefa_dados["titulo"])
                                    
                                # Criar duas colunas para organizar os campos
                                col1, col2 = st.columns(2)

                                with col1:
                                    prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], index=["Baixa", "Média", "Alta"].index(tarefa_dados["Prioridade"]))
                                    prazo_edit = st.selectbox(
                                        "Novo Prazo de Execução",
                                        ["Personalizada", "Hoje", "1 dia útil", "2 dias úteis", "3 dias úteis", "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"],
                                        index=1
                                    )
                                    if prazo_edit == "Personalizada":
                                        data_execucao_edit = st.date_input(
                                            "Data de Execução",
                                            value=pd.to_datetime(tarefa_dados["data_execucao"], errors="coerce").date()
                                        )
                                    else:
                                        data_execucao_edit = calcular_data_execucao(prazo_edit)

                                with col2:
                                    st.text_input("Status atual", tarefa_dados["status"], disabled=True)
                                    options = ["🟨 Em andamento", "🟩 Concluída"]
                                    default_status = tarefa_dados["status"] if tarefa_dados["status"] in options else "🟨 Em andamento"
                                    status_edit = st.selectbox(
                                        "Status",
                                        options,
                                        index=options.index(default_status)
                                    )
                                observacoes_edit = st.text_area("Observações", value=tarefa_dados["observacoes"])

                                submit_editar = st.form_submit_button("💾 Salvar Alterações")

                                if submit_editar:
                                    # Verificar se o usuário está tentando concluir todas as tarefas
                                    tarefas_ativas = list(collection_tarefas.find({"empresa_id": empresa_id, "status": {"$in": ["🟨 Em andamento", "🟥 Atrasado"]}}, {"_id": 0}))

                                    if len(tarefas_ativas) == 1 and tarefa_dados["status"] in ["🟨 Em andamento", "🟥 Atrasado"] and status_edit == "🟩 Concluída":
                                        st.error("⚠️ Erro: Pelo menos uma tarefa precisa estar 'Em andamento' ou 'Atrasado'. Cadastre uma nova atividade/tarefa antes de concluir todas.")
                                    else:
                                        if status_edit == "🟩 Concluída":
                                            data_execucao_edit = datetime.today().date()

                                            # Criar uma nova atividade informando que a tarefa foi concluída
                                            nova_atividade = {
                                                "atividade_id": str(datetime.now().timestamp()),  
                                                "tipo_atividade": "Observação",
                                                "status": "Registrado",
                                                "titulo": f"Tarefa '{titulo_edit}' concluída",
                                                "empresa": nome_empresa,
                                                "descricao": f"O vendedor {user} concluiu a tarefa '{titulo_edit}'.",
                                                "data_execucao_atividade": datetime.today().strftime("%Y-%m-%d"),
                                                "data_criacao_atividade": datetime.today().strftime("%Y-%m-%d"),
                                                "empresa_id": empresa_id
                                            }

                                            # Inserir no banco de atividades
                                            collection_atividades.insert_one(nova_atividade)

                                        # Atualizar a tarefa no banco
                                        collection_tarefas.update_one(
                                            {"empresa_id": empresa_id, "titulo": tarefa_selecionada},
                                            {"$set": {
                                                "titulo": titulo_edit,
                                                "Prioridade": prioridade,
                                                "data_execucao": data_execucao_edit.strftime("%Y-%m-%d"),
                                                "observacoes": observacoes_edit,
                                                "status": status_edit
                                            }}
                                        )
                                        
                                        # 🔄 Atualizar a última atividade da empresa
                                        data_hoje = datetime.now().strftime("%Y-%m-%d")  # Data atual
                                        collection_empresas = get_collection("empresas")
                                        collection_empresas.update_one(
                                            {"_id": empresa_id},
                                            {"$set": {"ultima_atividade": data_hoje}}
                                        )
                                        st.success("Tarefa atualizada com sucesso! 🔄")
                                        st.rerun()     
        
        with cols[2]:
            if admin or (empresa and user == empresa.get("proprietario")):
                if st.button("Concluir Tarefas Marcadas", key="concluir_tarefas", use_container_width=True):
                    # Filtrar apenas as tarefas marcadas para concluir e que ainda não estão concluídas
                    tarefas_para_concluir = edited_df[(edited_df["Concluir"] == True) & (edited_df["Status"] != "🟩 Concluída")]
                    # Buscar todas as tarefas ativas (em andamento ou atrasadas) para esta empresa
                    tarefas_ativas = list(collection_tarefas.find(
                    {"empresa_id": empresa_id, "status": {"$in": ["🟨 Em andamento", "🟥 Atrasado"]}},
                    {"_id": 0}
                    ))
                    # Verificar se concluindo as tarefas marcadas não ficará nenhuma tarefa ativa
                    if len(tarefas_ativas) - len(tarefas_para_concluir) < 1:
                        st.error("⚠️ Erro: Pelo menos uma tarefa precisa estar 'Em andamento' ou 'Atrasado'. Cadastre uma nova atividade/tarefa antes de concluir todas.")
                    else:
                        for _, row in tarefas_para_concluir.iterrows():
                            collection_tarefas.update_one(
                            {"titulo": row["Título"]},
                            {"$set": {
                                "status": "🟩 Concluída",
                                "data_execucao": datetime.today().strftime("%Y-%m-%d")
                            }}
                            )
                        
                        collection_empresas.update_one(
                            {"empresa_id": empresa_id},
                            {"$set": {"ultima_atividade": datetime.today().strftime("%Y-%m-%d")}}
                        )
                        st.success("Tarefas concluídas com sucesso!")
                        st.rerun()
    else:
        st.warning("Nenhuma tarefa cadastrada para esta empresa.")

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março",
    4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro",
    10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def atualizar_tarefas_atrasadas(user):
    collection_tarefas = get_collection("tarefas")
    collection_empresas = get_collection("empresas")

    # 🔹 Buscar todas as empresas do usuário
    empresas_usuario = {empresa["razao_social"] for empresa in collection_empresas.find(
        {"proprietario": user}, {"razao_social": 1}
    )}

    if not empresas_usuario:
        return None

    hoje = datetime.today().strftime("%Y-%m-%d")  # Formato compatível com MongoDB

    # 🔹 Atualizar **todas** as tarefas atrasadas de uma só vez
    collection_tarefas.update_many(
        {
            "empresa": {"$in": list(empresas_usuario)},  # Filtra empresas do usuário
            "data_execucao": {"$lt": hoje},             # Data menor que hoje
            "status": {"$ne": "🟩 Concluída"}            # Exclui concluídas
        },
        {"$set": {"status": "🟥 Atrasado"}}
    )

def gerenciamento_tarefas_por_usuario(user, admin):
    collection_tarefas = get_collection("tarefas")
    collection_empresas = get_collection("empresas")
    collection_atividades = get_collection("atividades")

    # 🔄 Atualiza as tarefas atrasadas apenas uma vez por sessão
    atualizar_tarefas_atrasadas(user)

    # Se for admin, permitir alternar a visualização das tarefas
    if admin:
        view_option = st.selectbox(
            "Visualizar Tarefas",
            ["Minhas Tarefas", "Por Vendedor", "Todas as Tarefas"]
        )
        if view_option == "Minhas Tarefas":
            empresas_usuario = {empresa["_id"] for empresa in collection_empresas.find(
                {"proprietario": user}, {"_id": 1, "razao_social": 1}
            )}
        elif view_option == "Por Vendedor":
            vendedores = {empresa["proprietario"] for empresa in collection_empresas.find(
                {}, {"proprietario": 1}
            ) if "proprietario" in empresa}
            vendedor_selecionado = st.selectbox("Selecione o Vendedor", sorted(vendedores))
            empresas_usuario = {empresa["_id"] for empresa in collection_empresas.find(
                {"proprietario": vendedor_selecionado}, {"_id": 1, "razao_social": 1}
            )}
        else:  # Todas as Tarefas
            empresas_usuario = {empresa["_id"] for empresa in collection_empresas.find(
                {}, {"_id": 1, "razao_social": 1}
            )}
    else:
        # Para usuários não-admin apenas as suas empresas
        empresas_usuario = {empresa["_id"] for empresa in collection_empresas.find(
            {"proprietario": user}, {"_id": 1}
        )}

    # Determinar se a visualização é "Todas as Tarefas"
    is_todas = admin and ("view_option" in locals() and view_option == "Todas as Tarefas")

    if is_todas:
        vendedores_dict = {empresa["_id"]: empresa.get("proprietario", "Não encontrado") for empresa in collection_empresas.find(
            {"_id": {"$in": list(empresas_usuario)}}, {"_id": 1, "proprietario": 1}
        )}

    if not empresas_usuario:
        st.warning("Nenhuma empresa atribuída a você.")
        return

    hoje = datetime.today().date()

    # 🔹 Buscar os _id das empresas ativas (empresa_ativa diferente de "Inativa")
    active_empresas = [
        empresa["_id"] for empresa in get_collection("empresas").find(
            {"_id": {"$in": list(empresas_usuario)}, "empresa_ativa": {"$ne": "Inativa"}},
            {"_id": 1}
        )
    ]
    # 🔹 Buscar todas as tarefas diretamente do banco, filtrando por empresa_id ativa
    tarefas = list(get_collection("tarefas").find(
        {"empresa_id": {"$in": active_empresas}},
        {"_id": 0, "titulo": 1, "empresa_id": 1, "empresa": 1, "data_execucao": 1, "status": 1, "observacoes": 1, "Prioridade": 1, "hexa": 1}
    ))

    # 🔹 Criar um dicionário com Nome da Empresa baseado no _id da empresa
    empresas_dict = {empresa["_id"]: empresa.get("razao_social", "Não encontrado") for empresa in collection_empresas.find(
        {"_id": {"$in": list(empresas_usuario)}}, {"_id": 1, "razao_social": 1}
    )}

    # 🔹 Converter datas e adicionar nome da empresa usando empresa_id
    for tarefa in tarefas:
        tarefa["Nome da Empresa"] = empresas_dict.get(tarefa["empresa_id"], "Não encontrado")
        tarefa["Data de Execução"] = datetime.strptime(tarefa["data_execucao"], "%Y-%m-%d").date()
        if is_todas:
            tarefa["Vendedor"] = vendedores_dict.get(tarefa["empresa_id"], "Não encontrado")

    # 📌 Criar abas para filtros rápidos
    abas = st.tabs([
        f"Hoje ({hoje.strftime('%d/%m')})",
        f"Amanhã ({(hoje + timedelta(days=1)).strftime('%d/%m')})",
        f"Nesta semana (até {(hoje + timedelta(days=7)).strftime('%d/%m')})",
        f"Neste mês (até {(hoje + timedelta(days=30)).strftime('%d/%m')})"
    ])

    def filtrar_tarefas(data_inicio, data_fim):
        return [t for t in tarefas if data_inicio <= t["Data de Execução"] <= data_fim]

    tarefas_hoje = filtrar_tarefas(hoje, hoje)
    tarefas_amanha = filtrar_tarefas(hoje + timedelta(days=1), hoje + timedelta(days=1))
    tarefas_semana = filtrar_tarefas(hoje, hoje + timedelta(days=7))
    tarefas_mes = filtrar_tarefas(hoje, hoje + timedelta(days=30))

    # 📌 Criar abas para Hoje, Amanhã, Semana, Mês
    for aba, tarefas_periodo, titulo, data_limite in zip(
        abas,
        [tarefas_hoje, tarefas_amanha, tarefas_semana, tarefas_mes],
        ["Hoje", "Amanhã", "Nesta Semana", "Neste Mês"],
        [hoje, hoje + timedelta(days=1), hoje + timedelta(days=7), hoje + timedelta(days=30)]
    ):
        with aba:
            # Garantir que todas as datas estejam no formato correto antes da filtragem
            for t in tarefas_periodo:
                t["Data de Execução"] = pd.to_datetime(t["Data de Execução"], errors="coerce").date()

            # 📌 Filtrar e contar tarefas atrasadas
            tarefas_atrasadas = [t for t in tarefas if t["status"] == "🟥 Atrasado" and t["Data de Execução"] < hoje]
            num_tarefas_atrasadas = len(tarefas_atrasadas)
            # Seção de Tarefas Atrasadas
            st.subheader(f"🟥 Atrasado - {titulo} ({num_tarefas_atrasadas})")

            if tarefas_atrasadas:
                df_atrasadas = pd.DataFrame(tarefas_atrasadas)
                # Formatar a data para exibição (dd/mm/aaaa)
                df_atrasadas["Data de Execução"] = df_atrasadas["Data de Execução"].apply(lambda x: x.strftime("%d/%m/%Y"))
                df_atrasadas = df_atrasadas.rename(
                    columns={
                        "titulo": "Título",
                        "observacoes": "Observações",
                        "status": "Status"
                    }
                )
                if "Nome da Empresa" not in df_atrasadas.columns and "empresa" in df_atrasadas.columns:
                    df_atrasadas["Nome da Empresa"] = df_atrasadas["empresa"]

                # Certificar que a coluna 'empresa_id' seja mantida
                if "empresa_id" not in df_atrasadas.columns and tarefas_atrasadas:
                    df_atrasadas["empresa_id"] = [t.get("empresa_id") for t in tarefas_atrasadas]

                # Adicionar coluna de editar com flag False por padrão
                df_atrasadas["Editar"] = False
                df_atrasadas["original_titulo"] = df_atrasadas["Título"]

                # Reordenar as colunas para que fiquem com a flag 'Editar' e 'Prioridade'
                if is_todas:
                    cols = ["Editar", "Status", "Prioridade", "Data de Execução", "Título", "Observações", "Nome da Empresa", "Vendedor", "empresa_id", "original_titulo"]
                else:
                    cols = ["Editar", "Status", "Prioridade", "Data de Execução", "Título", "Observações", "Nome da Empresa", "empresa_id", "original_titulo"]
                df_atrasadas = df_atrasadas[[c for c in cols if c in df_atrasadas.columns]]
                hidden_cols_atrasadas = df_atrasadas[["original_titulo", "empresa_id"]].copy()
                df_atrasadas_display = df_atrasadas.drop(columns=["original_titulo", "empresa_id"])

                # Configurar as colunas: 'Editar' como checkbox, 'Status' como selectbox e 'Prioridade' também como selectbox
                column_config = {
                    "Editar": st.column_config.CheckboxColumn(
                        "Editar",
                        help="Marque para editar esta tarefa"
                    ),
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["🟥 Atrasado", "🟩 Concluída"],
                        help="Selecione o status"
                    ),
                    "Prioridade": st.column_config.SelectboxColumn(
                        "Prioridade",
                        options=["Baixa", "Média", "Alta"],
                        help="Selecione a prioridade"
                    )
                }
                if is_todas:
                    column_config["Vendedor"] = st.column_config.TextColumn(
                        "Vendedor",
                        help="Vendedor",
                        disabled=True
                    )

                edited_df_atrasadas = st.data_editor(
                    df_atrasadas_display,
                    hide_index=True,
                    key=f"atrasadas_{titulo}",
                    use_container_width=True,
                    height=200,  # Altura máxima reduzida para 300 pixels
                    column_config=column_config
                )

                if st.button(f"Salvar alterações", key=f"save_atrasadas_{titulo}"):
                    collection = get_collection("tarefas")
                    for idx, row in edited_df_atrasadas.iterrows():
                        # Atualiza apenas se a flag 'Editar' estiver marcada
                        if row.get("Editar"):
                            try:
                                if row["Status"] == "🟩 Concluída":
                                    nova_data_db = datetime.today().strftime("%Y-%m-%d")
                                    nova_data_display = datetime.today().strftime("%d/%m/%Y")
                                else:
                                    nova_data_db = datetime.strptime(row["Data de Execução"], "%d/%m/%Y").strftime("%Y-%m-%d")
                                original_titulo = hidden_cols_atrasadas.iloc[idx]["original_titulo"]
                                empresa_id_val = hidden_cols_atrasadas.iloc[idx]["empresa_id"]
                                # Se a nova data for depois de hoje, status será "🟨 Em andamento"
                                status = "🟨 Em andamento" if nova_data_db >= hoje.strftime("%Y-%m-%d") else row["Status"]
                                if row["Status"] == "🟩 Concluída":
                                    nova_atividade = {
                                        "atividade_id": str(datetime.now().timestamp()),
                                        "tipo_atividade": "Observação",
                                        "status": "Registrado",
                                        "titulo": f"Tarefa '{row['Título']}' concluída",
                                        "empresa": row["Nome da Empresa"],
                                        "descricao": f"O vendedor {user} concluiu a tarefa '{row['Título']}'.",
                                        "data_execucao_atividade": nova_data_db,
                                        "data_criacao_atividade": nova_data_db,
                                        "empresa_id": empresa_id_val
                                    }
                                    collection_atividades.insert_one(nova_atividade)
                                collection.update_one(
                                    {"empresa_id": empresa_id_val, "titulo": original_titulo},
                                    {"$set": {
                                        "titulo": row["Título"],
                                        "data_execucao": nova_data_db,
                                        "observacoes": row["Observações"],
                                        "status": status,
                                        "Prioridade": row["Prioridade"]
                                    }}
                                )
                                st.success(f"Tarefa '{row['Título']}' atualizada com sucesso!")
                            except Exception as e:
                                st.error(f"Erro ao atualizar a tarefa '{row['Título']}': {e}")
                    else:
                        st.success(f"Nenhuma tarefa atrasada para {titulo} marcada para edição.")
                    st.rerun()
            else:
                st.warning("Nenhuma tarefa atrasada para o período selecionado.")
            st.write('---')

            # Seção de Tarefas em Andamento
            tarefas_em_andamento = [t for t in tarefas if t["status"] == "🟨 Em andamento" and t["Data de Execução"] <= data_limite]
            num_tarefas_andamento = len(tarefas_em_andamento)

            st.subheader(f"🟨 Em andamento - {titulo} ({num_tarefas_andamento})")
            if tarefas_em_andamento:
                df_andamento = pd.DataFrame(tarefas_em_andamento)
                df_andamento = df_andamento.rename(
                    columns={
                        "titulo": "Título",
                        "observacoes": "Observações",
                        "status": "Status"
                    }
                )
                df_andamento["Data de Execução"] = df_andamento["Data de Execução"].apply(lambda x: x.strftime("%d/%m/%Y"))
                
                # Adicionar coluna de editar com flag False por padrão
                df_andamento["Editar"] = False

                # Certificar que a coluna 'empresa_id' seja mantida
                if "empresa_id" not in df_andamento.columns and tarefas_em_andamento:
                    df_andamento["empresa_id"] = [t.get("empresa_id") for t in tarefas_em_andamento]

                df_andamento["original_titulo"] = df_andamento["Título"]
                if is_todas:
                    cols = ["Editar", "Status", "Prioridade", "Data de Execução", "Título", "Observações", "Nome da Empresa", "Vendedor", "empresa_id", "original_titulo"]
                else:
                    cols = ["Editar", "Status", "Prioridade", "Data de Execução", "Título", "Observações", "Nome da Empresa", "empresa_id", "original_titulo"]
                df_andamento = df_andamento[[c for c in cols if c in df_andamento.columns]]
                hidden_cols_andamento = df_andamento[["original_titulo", "empresa_id"]].copy()
                df_andamento_display = df_andamento.drop(columns=["original_titulo", "empresa_id"])
                if is_todas:
                    df_andamento_display = df_andamento_display[["Editar", "Status", "Prioridade", "Data de Execução", "Título", "Observações", "Nome da Empresa", "Vendedor"]]
                else:
                    df_andamento_display = df_andamento_display[["Editar", "Status", "Prioridade", "Data de Execução", "Título", "Observações", "Nome da Empresa"]]

                column_config = {
                    "Editar": st.column_config.CheckboxColumn(
                        "Editar",
                        help="Marque para editar esta tarefa"
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status",
                        help="Selecione o status",
                        disabled=True
                    ),
                    "Prioridade": st.column_config.SelectboxColumn(
                        "Prioridade",
                        options=["Baixa", "Média", "Alta"],
                        help="Selecione a prioridade"
                    ),
                    "Nome da Empresa": st.column_config.TextColumn(
                        "Nome da Empresa",
                        help="Nome da Empresa cadastrada",
                        disabled=True
                    )
                }
                if is_todas:
                    column_config["Vendedor"] = st.column_config.TextColumn(
                        "Vendedor",
                        help="Vendedor",
                        disabled=True
                    )

                edited_df_andamento = st.data_editor(
                    df_andamento_display,
                    hide_index=True,
                    key=f"andamento_{titulo}",
                    use_container_width=True,
                    height=200,  # Altura máxima reduzida para 300 pixels
                    column_config=column_config
                )

                if st.button(f"Salvar alterações", key=f"save_andamento_{titulo}"):
                    collection = get_collection("tarefas")
                    for idx, row in edited_df_andamento.iterrows():
                        # Atualiza somente se a flag 'Editar' estiver True
                        if row.get("Editar"):
                            try:
                                if row["Status"] == "🟩 Concluída":
                                    nova_data_db = datetime.today().strftime("%Y-%m-%d")
                                    nova_data_display = datetime.today().strftime("%d/%m/%Y")
                                else:
                                    nova_data_db = datetime.strptime(row["Data de Execução"], "%d/%m/%Y").strftime("%Y-%m-%d")
                                original_titulo = hidden_cols_andamento.iloc[idx]["original_titulo"]
                                empresa_id_val = hidden_cols_andamento.iloc[idx]["empresa_id"]
                                if row["Status"] == "🟩 Concluída":
                                    nova_atividade = {
                                        "atividade_id": str(datetime.now().timestamp()),
                                        "tipo_atividade": "Observação",
                                        "status": "Registrado",
                                        "titulo": f"Tarefa '{row['Título']}' concluída",
                                        "empresa": row["Nome da Empresa"],
                                        "descricao": f"O vendedor {user} concluiu a tarefa '{row['Título']}'.",
                                        "data_execucao_atividade": nova_data_db,
                                        "data_criacao_atividade": nova_data_db,
                                        "empresa_id": empresa_id_val
                                    }
                                    collection_atividades.insert_one(nova_atividade)
                                    collection.update_one(
                                        {"empresa_id": empresa_id_val, "titulo": original_titulo},
                                        {"$set": {
                                            "titulo": row["Título"],
                                            "data_execucao": nova_data_db,
                                            "observacoes": row["Observações"],
                                            "status": row["Status"],
                                            "Prioridade": row["Prioridade"]
                                        }}
                                    )
                                    collection_empresas.update_one(
                                        {"_id": empresa_id_val},
                                        {"$set": {"ultima_atividade": datetime.today().strftime("%Y-%m-%d")}}
                                    )
                                    st.success(f"Tarefa '{row['Título']}' atualizada com data de conclusão {nova_data_display}!")
                                    st.rerun()
                                else:
                                    collection.update_one(
                                        {"empresa_id": empresa_id_val, "titulo": original_titulo},
                                        {"$set": {
                                            "titulo": row["Título"],
                                            "data_execucao": nova_data_db,
                                            "observacoes": row["Observações"],
                                            "status": row["Status"],
                                            "Prioridade": row["Prioridade"]
                                        }}
                                    )
                                    st.success(f"Tarefa '{row['Título']}' atualizada com sucesso!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar a tarefa '{row['Título']}': {e}")
            else:
                st.warning(f"Nenhuma tarefa em andamento para o período selecionado.")

def editar_tarefa_modal(tarefas, key, tipo, user, empresa_id): 
    """
    Exibe um pop-up/modal para edição de tarefas do tipo especificado (Atrasadas ou Em Andamento).
    """
    collection_tarefas = get_collection("tarefas")
    collection_atividades = get_collection("atividades")
    collection_empresas = get_collection("empresas")

    with st.popover(f"✏️ Editar tarefas {tipo}"):
        if not tarefas:
            st.warning(f"Não há tarefas {tipo.lower()} para editar.")
            return

        tarefa_selecionada = st.selectbox(
            "Selecione uma tarefa para editar",
            options=[t["titulo"] for t in tarefas],  
            key=f"select_editar_tarefa_{key}"
        )

        if tarefa_selecionada:
            tarefa_dados = next((t for t in tarefas if t["titulo"] == tarefa_selecionada), None)
            
            if not tarefa_dados:
                st.error("Erro ao encontrar a tarefa selecionada.")
                return

            with st.form(f"form_editar_tarefa_{key}"):
                st.subheader(f"✏️ Editando: {tarefa_selecionada}")

                col1, col2 = st.columns(2)

                with col1:
                    titulo_edit = st.text_input("Título", value=tarefa_dados["titulo"])
                    prazo_edit = st.selectbox(
                        "Novo Prazo de Execução",
                        ["Hoje", "1 dia útil", "2 dias úteis", "3 dias úteis", "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"],
                        index=3
                    )
                    data_execucao_edit = st.date_input(
                        "Data de Execução",
                        value=pd.to_datetime(tarefa_dados["Data de Execução"], errors="coerce").date()
                    ) if prazo_edit == "Personalizada" else calcular_data_execucao(prazo_edit)

                with col2:
                    status_edit = st.selectbox(
                        "Status",
                        ["🟨 Em andamento", "🟩 Concluída"],
                        index=["🟥 Atrasado","🟨 Em andamento", "🟩 Concluída"].index(tarefa_dados["status"])
                    )
                    observacoes_edit = st.text_area("Observações", value=tarefa_dados["observacoes"])

                submit_editar = st.form_submit_button("💾 Salvar Alterações")

                if submit_editar:
                    # Buscar todas as tarefas ativas (atrasadas ou em andamento) dessa empresa
                    tarefas_ativas = list(collection_tarefas.find(
                        {"empresa": tarefa_dados["empresa"], "status": {"$in": ["🟨 Em andamento", "🟥 Atrasado"]}},
                        {"_id": 0}
                    ))

                    # Se for a única tarefa ativa e o usuário tentar concluir, exibe erro
                    if len(tarefas_ativas) == 1 and tarefa_dados["status"] in ["🟨 Em andamento", "🟥 Atrasado"] and status_edit == "🟩 Concluída":
                        st.error("⚠️ Erro: Pelo menos uma tarefa precisa estar 'Em andamento' ou 'Atrasada'. Cadastre uma nova atividade/tarefa antes de concluir todas.")
                        return

                    # 🚀 Atualizar os dados da tarefa no banco
                    collection_tarefas.update_one(
                        {"empresa": tarefa_dados['empresa'], "titulo": tarefa_dados["titulo"]},
                        {"$set": {
                            "titulo": titulo_edit,
                            "data_execucao": data_execucao_edit.strftime("%Y-%m-%d"),
                            "observacoes": observacoes_edit,
                            "status": status_edit
                        }}
                    )

                    # 🟩 Se concluída, criar uma atividade no histórico
                    if status_edit == "🟩 Concluída":
                        data_execucao_edit = datetime.today().date()
                        nova_atividade = {
                            "atividade_id": str(datetime.now().timestamp()),  
                            "tipo_atividade": "Observação",
                            "status": "Registrado",
                            "titulo": f"Tarefa '{titulo_edit}' concluída",
                            "empresa": tarefa_dados['empresa'],
                            "descricao": f"O vendedor {user} concluiu a tarefa '{titulo_edit}'.",
                            "data_execucao_atividade": datetime.today().strftime("%Y-%m-%d"),
                            "data_criacao_atividade": datetime.today().strftime("%Y-%m-%d"),
                            "empresa_id": empresa_id,
                        }
                        collection_atividades.insert_one(nova_atividade)

                    # 🔄 Atualizar a última atividade da empresa
                    data_hoje = datetime.now().strftime("%Y-%m-%d")
                    collection_empresas.update_one(
                        {"cnpj": tarefa_dados['empresa']},
                        {"$set": {"ultima_atividade": data_hoje}}
                    )

                    st.success("Tarefa atualizada com sucesso! 🔄")
                    st.rerun()



