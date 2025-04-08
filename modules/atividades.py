from utils.database import get_collection
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import time
import random
from concurrent.futures import ThreadPoolExecutor

# Dicionário de meses em português
MESES_PT = {
    "January": "Janeiro", "February": "Fevereiro", "March": "Março",
    "April": "Abril", "May": "Maio", "June": "Junho",
    "July": "Julho", "August": "Agosto", "September": "Setembro",
    "October": "Outubro", "November": "Novembro", "December": "Dezembro"
}

def calcular_data_execucao(opcao):
    """Calcula a data de execução da tarefa com base na opção selecionada, considerando apenas dias úteis."""
    hoje = datetime.today().date()
    
    def adicionar_dias_uteis(dias):
        """Adiciona um número de dias úteis à data de hoje, ignorando finais de semana."""
        data = hoje
        while dias > 0:
            data += timedelta(days=1)
            if data.weekday() < 5:
                dias -= 1
        return data

    opcoes_prazo = {
        "Hoje": hoje,
        "1 dia útil": adicionar_dias_uteis(1),
        "2 dias úteis": adicionar_dias_uteis(2),
        "3 dias úteis": adicionar_dias_uteis(3),
        "1 semana": hoje + timedelta(weeks=1),
        "2 semanas": hoje + timedelta(weeks=2),
        "1 mês": hoje + timedelta(days=30),
        "2 meses": hoje + timedelta(days=60),
        "3 meses": hoje + timedelta(days=90)
    }
    
    return opcoes_prazo.get(opcao, hoje)

def exibir_atividades_empresa(user, admin, empresa_id):
    collection_atividades = get_collection("atividades")
    collection_contatos = get_collection("contatos")
    collection_empresas = get_collection("empresas")

    if not empresa_id:
        st.error("Erro: Nenhuma empresa selecionada para exibir atividades.")
        return

    # Buscar dados em paralelo
    with ThreadPoolExecutor() as executor:
        future_contatos = executor.submit(list, collection_contatos.find(
            {"empresa_id": empresa_id},
            {"_id": 0, "empresa": 1, "nome": 1, "sobrenome": 1, "email": 1}
        ))
        future_nome_empresa = executor.submit(collection_atividades.find_one,
                                                {"empresa_id": empresa_id},
                                                {"empresa": 1})
        future_proprietario = executor.submit(collection_empresas.find_one,
                                                {"_id": empresa_id},
                                                {"proprietario": 1})
        future_atividades = executor.submit(list, collection_atividades.find({"empresa_id": empresa_id}, {"_id": 0}))

    contatos_vinculados = future_contatos.result()
    result_empresa = future_nome_empresa.result()
    nome_empresa = result_empresa["empresa"] if result_empresa else None
    result_proprietario = future_proprietario.result()
    proprietario = result_proprietario["proprietario"] if result_proprietario else None
    atividades = future_atividades.result()

    # Criar lista de contatos formatada
    lista_contatos = [""] + [f"{c['nome']} {c['sobrenome']}" for c in contatos_vinculados]

    # Dicionário de meses com valores numéricos para ordenação
    MESES_NUMERICOS = {
        "Janeiro": 1, "Fevereiro": 2, "Março": 3,
        "Abril": 4, "Maio": 5, "Junho": 6,
        "Julho": 7, "Agosto": 8, "Setembro": 9,
        "Outubro": 10, "Novembro": 11, "Dezembro": 12
    }

    if admin or (user == proprietario):
        def criar_form_atividade(key, tipo, titulo_form, info_msg, titulo_tarefa=None,
                                   with_status=False, status_options=None, extra_fields_fn=None):
            """
            Função genérica para criação de formulários de atividade.
            """
            with st.form(key):
                st.subheader(titulo_form)
                st.info(info_msg)
                
                contato = st.multiselect("Contato Vinculado *", lista_contatos)
                extra_fields = extra_fields_fn() if extra_fields_fn is not None else {}
                data_execucao = st.date_input("Data de Execução", value=datetime.today().date())
                
                if with_status and status_options:
                    status_value = st.selectbox("Status", status_options)
                else:
                    status_value = None

                descricao = st.text_area("Descrição *")
                if tipo != 'Observação':
                    st.markdown("---")
                    criar_tarefa = st.checkbox("Criar tarefa de acompanhamento para a atividade", value=True)
                    st.subheader("📌 Prazo para o acompanhamento")
                    prazo = st.selectbox("Prazo", ["1 dia útil", "2 dias úteis", "3 dias úteis", 
                                                    "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"], index=3)
                    data_execucao_tarefa = st.date_input("Data de Execução", value=calcular_data_execucao(prazo)) if prazo == "Personalizada" else calcular_data_execucao(prazo)
                    prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"])
                else: criar_tarefa = False 
                submit_atividade = st.form_submit_button("✅ Adicionar Atividade")
                if submit_atividade:
                    if (descricao and contato and tipo != 'Observação') or (descricao and tipo == 'Observação'):
                        atividade_id = str(datetime.now().timestamp())
                        nova_atividade = {
                            "atividade_id": atividade_id,
                            "tipo_atividade": tipo,
                            "empresa": nome_empresa,
                            "contato": contato,
                            "descricao": descricao,
                            "vendedor_criacao": user,
                            "data_execucao_atividade": data_execucao.strftime("%Y-%m-%d"),
                            "data_criacao_atividade": datetime.now().strftime("%Y-%m-%d"),
                            "empresa_id": empresa_id,
                        }
                        if with_status and status_value:
                            nova_atividade["status"] = status_value
                        nova_atividade.update(extra_fields)
                        
                        collection_atividades.insert_one(nova_atividade)
                        if criar_tarefa:
                            if tipo != 'Observação':
                                random_hex = f"{random.randint(0, 0xFFFF):04x}"
                                nova_tarefa = {
                                    "tarefa_id": str(datetime.now().timestamp()),
                                    "titulo": f"{titulo_tarefa} ({nome_empresa} - {random_hex})" if titulo_tarefa is not None else f"{tipo} ({nome_empresa} - {random_hex})",
                                    "empresa": nome_empresa,
                                    "atividade_vinculada": atividade_id,
                                    "data_execucao": data_execucao_tarefa.strftime("%Y-%m-%d"),
                                    "status": "🟨 Em andamento",
                                    "observacoes": "",
                                    "Prioridade": prioridade,
                                    "empresa_id": empresa_id,
                                }
                                collection_tarefas = get_collection("tarefas")
                                collection_tarefas.insert_one(nova_tarefa)
                            
                        data_hoje = datetime.now().strftime("%Y-%m-%d")
                        collection_empresas.update_one(
                            {"_id": empresa_id},
                            {"$set": {"ultima_atividade": data_hoje}}
                        )
                        st.success("Atividade adicionada com sucesso! 📌")
                        st.rerun()
                    else:
                        st.error("Preencha os campos obrigatórios: Descrição e contato* (*exceto para Observação).")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            with st.popover("🟫➕ Observação", use_container_width=True):
                criar_form_atividade(
                    key="form_adicionar_observacoes",
                    tipo="Observação",
                    titulo_form="🟫➕ Observação",
                    info_msg="Registrar uma **observação** nas atividades da empresa."
                )

        with col2:
            with st.popover("🟩➕ Whatsapp", use_container_width=True):
                criar_form_atividade(
                    key="form_adicionar_whatsapp",
                    tipo="Whatsapp",
                    titulo_form="🟩➕ Whatsapp",
                    info_msg="Registrar um **Whatsapp** nas atividades da empresa.",
                    with_status=True
                )

        with col3:
            with st.popover("🟨➕ Ligação", use_container_width=True):
                criar_form_atividade(
                    key="form_adicionar_ligacao",
                    tipo="Ligação",
                    titulo_form="🟨➕ Ligação",
                    info_msg="Registrar uma **Ligação** nas atividades da empresa.",
                    with_status=True,
                    status_options=["Conectado", "Ocupado", "Sem Resposta", "Gatekeeper", "Ligação Positiva", "Ligação Negativa"]
                )

        with col4:
            with st.popover("🟥➕ Email", use_container_width=True):
                criar_form_atividade(
                    key="form_adicionar_email",
                    tipo="Email",
                    titulo_form="🟥➕ Email",
                    info_msg="Registrar um envio de **email** nas atividades da empresa."
                )

        with col5:
            with st.popover("🟦➕ Linkedin", use_container_width=True):
                criar_form_atividade(
                    key="form_adicionar_linkedin",
                    tipo="Linkedin",
                    titulo_form="🟦➕ Linkedin",
                    info_msg="Registrar um envio de mensagem no **linkedin** nas atividades da empresa."
                )

        with col6:
            with st.popover("🟪➕ Reunião", use_container_width=True):
                st.header('🟪➕ Registro de reunião')
                criar_form_atividade(
                    key="form_adicionar_reuniao",
                    tipo="Reunião",
                    titulo_form="Registro de reunião",
                    info_msg="Registrar uma **reunião** nas atividades da empresa.",
                    with_status=True,
                    status_options=["Realizada", "Contato não apareceu", "Remarcada"],
                    titulo_tarefa="Acompanhar Reunião"
                )

    with st.expander("🗓️ Atividades realizadas por período", expanded=False):
        if atividades:
            atividades_ordenadas = defaultdict(list)
            for atividade in atividades:
                data_execucao = datetime.strptime(atividade["data_execucao_atividade"], "%Y-%m-%d")
                mes_ingles = data_execucao.strftime("%B")
                mes_portugues = MESES_PT.get(mes_ingles, mes_ingles)
                chave_mes_ano = (data_execucao.year, 
                                 {"Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
                                  "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
                                  "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12}[mes_portugues],
                                 f"{mes_portugues} {data_execucao.year}")

                atividades_ordenadas[chave_mes_ano].append({
                    "data": data_execucao.strftime("%d/%m/%Y"),
                    "tipo": atividade["tipo_atividade"],
                    "contato": ", ".join(atividade.get("contato", "")) if isinstance(atividade.get("contato", []), list) else atividade.get("contato", ""),
                    "descricao": atividade["descricao"],
                    "data_execucao_timestamp": data_execucao.timestamp()
                })

            for (ano, mes_num, mes_ano_str), atividades_lista in sorted(atividades_ordenadas.items(), reverse=True):
                st.subheader(f"📅 {mes_ano_str}")
                atividades_lista.sort(key=lambda x: x["data_execucao_timestamp"], reverse=True)
                with st.container():
                    for atividade in atividades_lista:
                        st.write(f'**📆 {atividade["data"]}** - **{atividade["tipo"]}**: {atividade["contato"]}. 📝 {atividade["descricao"]}')
                    st.write('---')
        else:
            st.warning("Nenhuma atividade cadastrada para esta empresa.")

    def modificar_atividade(user, admin, empresa_nome):
        collection_atividades = get_collection("atividades")
        atividades = list(collection_atividades.find({"empresa": empresa_nome}, {"_id": 0}))
        if not atividades:
            st.info("Nenhuma atividade encontrada para modificar.")
            return

        opcoes = {}
        for ativ in atividades:
            descricao_curta = ativ["descricao"][:30] + "..." if len(ativ["descricao"]) > 30 else ativ["descricao"]
            chave = f'{ativ["data_execucao_atividade"]} - {ativ["tipo_atividade"]}: {descricao_curta}'
            opcoes[chave] = ativ

        atividade_selecionada_chave = st.selectbox("Selecione a atividade para modificar", list(opcoes.keys()))
        atividade_selecionada = opcoes[atividade_selecionada_chave]

        with st.form("modificar_atividade_form"):
            st.subheader("🔧 Modificar Atividade")
            default_data = datetime.strptime(atividade_selecionada["data_execucao_atividade"], "%Y-%m-%d").date()
            nova_data = st.date_input("Nova Data de Execução", value=default_data)
            nova_descricao = st.text_area("Nova Descrição", value=atividade_selecionada.get("descricao", ""))
            submit_modificacao = st.form_submit_button("Confirmar Modificações")

            if submit_modificacao:
                if nova_descricao:
                    collection_atividades.update_one(
                        {"atividade_id": atividade_selecionada["atividade_id"]},
                        {"$set": {
                            "data_execucao_atividade": nova_data.strftime("%Y-%m-%d"),
                            "descricao": nova_descricao
                        }}
                    )
                    st.success("Atividade modificada com sucesso!")
                    st.rerun()
                else:
                    st.error("A descrição não pode ser vazia.")

    with st.expander("🔧 Modificar Atividade", expanded=False):
        modificar_atividade(user, admin, nome_empresa)
