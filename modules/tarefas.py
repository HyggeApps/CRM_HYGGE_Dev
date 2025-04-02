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
def gerenciamento_tarefas(user, admin, empresa_id):
    collection_tarefas = atualizar_status_tarefas(empresa_id)
    collection_atividades = get_collection("atividades")
    collection_empresas = get_collection("empresas")
    
    if not empresa_id:
        st.error("Erro: Nenhuma empresa selecionada para gerenciar tarefas.")
        return

    # 📌 Verificar e atualizar tarefas atrasadas automaticamente
    tarefas = list(collection_tarefas.find({"empresa_id": empresa_id}, {"_id": 0}))
    # pega o nome da empresa com base no "empresa_id" via collection_empresas
    collection_empresas = get_collection("empresas")
    nome_empresa = collection_empresas.find_one({"empresa_id": empresa_id}, {"_id": 0, "razao_social": 1})   
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

    # 📌 Listagem das tarefas existentes
    if tarefas:
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
        
        # Reordenar as colunas para colocar "Concluir" como a primeira
        df_tarefas = df_tarefas[["Concluir", "Status", "Data de Execução", "Título", "Observações"]]

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
        
        if st.button("Concluir Tarefas Marcadas"):
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
                st.success("Tarefas concluídas com sucesso!")
                st.rerun()

        # 📌 Popover para editar tarefas existentes
        with st.popover('✏️ Editar Tarefa'):
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

                        # Criar duas colunas para organizar os campos
                        col1, col2 = st.columns(2)

                        with col1:
                            titulo_edit = st.text_input("Título", value=tarefa_dados["titulo"])
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
                                        "data_execucao": data_execucao_edit.strftime("%Y-%m-%d"),
                                        "observacoes": observacoes_edit,
                                        "status": status_edit
                                    }}
                                )
                                
                                # 🔄 Atualizar a última atividade da empresa
                                data_hoje = datetime.now().strftime("%Y-%m-%d")  # Data atual
                                collection_empresas = get_collection("empresas")
                                collection_empresas.update_one(
                                    {"empresa_id": empresa_id},
                                    {"$set": {"ultima_atividade": data_hoje}}
                                )
                                st.success("Tarefa atualizada com sucesso! 🔄")
                                st.rerun()

        # 📌 Popover para modificar tarefas (alterar título, data de execução e observações)
        with st.popover('🛠️ Modificar Tarefa'):
            tarefa_modificar = st.selectbox(
                "Selecione uma tarefa para modificar",
                options=[t["titulo"] for t in tarefas],
                key="select_modificar_tarefa"
            )
            if tarefa_modificar:
                tarefa_dados = collection_tarefas.find_one({"empresa_id": empresa_id, "titulo": tarefa_modificar}, {"_id": 0})
                if tarefa_dados:
                    with st.form("form_modificar_tarefa"):
                        st.subheader("🛠️ Modificar Tarefa")
                        col1, col2 = st.columns(2)
                        with col1:
                            novo_titulo = st.text_input("Novo Título", value=tarefa_dados["titulo"])
                        with col2:
                            prazo_modificar = st.selectbox(
                                "Novo Prazo de Execução",
                                ["Personalizada", "Hoje", "1 dia útil", "2 dias úteis", "3 dias úteis", "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"],
                                index=1
                            )
                            if prazo_modificar == "Personalizada":
                                nova_data_execucao = st.date_input(
                                    "Nova Data de Execução",
                                    value=pd.to_datetime(tarefa_dados["data_execucao"], errors="coerce").date()
                                )
                            else:
                                nova_data_execucao = calcular_data_execucao(prazo_modificar)
                        novas_observacoes = st.text_area("Novas Observações", value=tarefa_dados["observacoes"])

                        submit_modificar = st.form_submit_button("💾 Salvar Modificações")

                        if submit_modificar:
                            collection_tarefas.update_one(
                                {"empresa_id": empresa_id, "titulo": tarefa_modificar},
                                {"$set": {
                                    "titulo": novo_titulo,
                                    "data_execucao": nova_data_execucao.strftime("%Y-%m-%d"),
                                    "observacoes": novas_observacoes,
                                }}
                            )
                            st.success("Tarefa modificada com sucesso!")
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

@st.fragment
def gerenciamento_tarefas_por_usuario(user, admin):
    collection_tarefas = get_collection("tarefas")
    collection_empresas = get_collection("empresas")

    # 🔄 Atualiza as tarefas atrasadas apenas uma vez por sessão
    atualizar_tarefas_atrasadas(user)

    # 🔹 Buscar empresas do usuário logado usando empresa_id
    empresas_usuario = {empresa["_id"] for empresa in collection_empresas.find(
        {"proprietario": user}, {"_id": 1}
    )}

    if not empresas_usuario:
        st.warning("Nenhuma empresa atribuída a você.")
        return

    hoje = datetime.today().date()

    # 🔹 Buscar todas as tarefas diretamente do banco, filtrando por empresa_id
    tarefas = list(collection_tarefas.find(
        {"empresa_id": {"$in": list(empresas_usuario)}},
        {"_id": 0, "titulo": 1, "empresa_id": 1, "empresa": 1, "data_execucao": 1, "status": 1, "observacoes": 1}
    ))

    if not tarefas:
        st.warning("Nenhuma tarefa encontrada.")
        return

    # 🔹 Criar um dicionário com Nome da Empresa baseado no _id da empresa
    empresas_dict = {empresa["_id"]: empresa.get("razao_social", "Não encontrado") for empresa in collection_empresas.find(
        {"_id": {"$in": list(empresas_usuario)}}, {"_id": 1, "razao_social": 1}
    )}

    # 🔹 Converter datas e adicionar nome da empresa usando empresa_id
    for tarefa in tarefas:
        tarefa["Nome da Empresa"] = empresas_dict.get(tarefa["empresa_id"], "Não encontrado")
        tarefa["Data de Execução"] = datetime.strptime(tarefa["data_execucao"], "%Y-%m-%d").date()

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

            st.subheader(f"🟥 Atrasado - {titulo} ({num_tarefas_atrasadas})")

            if tarefas_atrasadas:
                df_atrasadas = pd.DataFrame(tarefas_atrasadas)[["titulo", "Data de Execução", "Nome da Empresa", "empresa_id", "observacoes"]]
                df_atrasadas = df_atrasadas.rename(columns={"titulo": "Título", "empresa_id": "Empresa ID", "observacoes": "Observações"})
                df_atrasadas["Data de Execução"] = df_atrasadas["Data de Execução"].apply(lambda x: x.strftime("%d/%m/%Y"))
                df_atrasadas = df_atrasadas[["Data de Execução", "Nome da Empresa", "Título", "Observações"]]
                st.dataframe(df_atrasadas, hide_index=True, use_container_width=True)

                editar_tarefa_modal(tarefas_atrasadas, key=f"editar_tarefa_atrasada_{titulo}", tipo=f"atrasadas - {titulo}", user=user, empresa_id=tarefa["empresa_id"])
            else:
                st.success(f"Nenhuma tarefa atrasada para {titulo}.")

            st.write('---')

            # 📌 Filtrar e contar tarefas em andamento
            tarefas_em_andamento = [t for t in tarefas if t["status"] == "🟨 Em andamento" and t["Data de Execução"] <= data_limite]
            num_tarefas_andamento = len(tarefas_em_andamento)

            st.subheader(f"🟨 Em andamento - {titulo} ({num_tarefas_andamento})")

            if tarefas_em_andamento:
                df_em_andamento = pd.DataFrame(tarefas_em_andamento)[["titulo", "Data de Execução", "Nome da Empresa", "empresa_id", "observacoes"]]
                df_em_andamento = df_em_andamento.rename(columns={"titulo": "Título", "empresa_id": "Empresa ID", "observacoes": "Observações"})
                df_em_andamento["Data de Execução"] = df_em_andamento["Data de Execução"].apply(lambda x: x.strftime("%d/%m/%Y"))
                df_em_andamento = df_em_andamento[["Data de Execução", "Nome da Empresa", "Título", "Observações"]]
                st.dataframe(df_em_andamento, hide_index=True, use_container_width=True)

                editar_tarefa_modal(tarefas_em_andamento, key=f"editar_tarefa_andamento_{titulo}", tipo=f"em andamento - {titulo}", user=user, empresa_id=tarefa["empresa_id"])
            else:
                st.success(f"Nenhuma tarefa em andamento para {titulo}.")

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



