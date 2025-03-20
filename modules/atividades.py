from utils.database import get_collection
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import time
import random

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
def exibir_atividades_empresa(user, admin, empresa_nome):
    collection_atividades = get_collection("atividades")
    collection_contatos = get_collection("contatos")

    if not empresa_nome:
        st.error("Erro: Nenhuma empresa selecionada para exibir atividades.")
        return

    # Buscar contatos vinculados à empresa
    contatos_vinculados = list(collection_contatos.find({"empresa": empresa_nome}, {"_id": 0, "nome": 1, "sobrenome": 1, "email": 1}))

    # Criar lista de contatos formatada
    lista_contatos = [""] + [f"{c['nome']} {c['sobrenome']}" for c in contatos_vinculados]

    # Buscar atividades vinculadas **somente** à empresa selecionada
    atividades = list(collection_atividades.find({"empresa": empresa_nome}, {"_id": 0}))

    # Dicionário de meses com valores numéricos para ordenação
    MESES_NUMERICOS = {
        "Janeiro": 1, "Fevereiro": 2, "Março": 3,
        "Abril": 4, "Maio": 5, "Junho": 6,
        "Julho": 7, "Agosto": 8, "Setembro": 9,
        "Outubro": 10, "Novembro": 11, "Dezembro": 12
    }

    # **Permitir que a atividade seja cadastrada sempre**
    if admin or (user == st.session_state["empresa_selecionada"]["Proprietário"]):
        def criar_form_atividade(key, tipo, titulo_form, info_msg, titulo_tarefa=None,
                                with_status=False, status_options=None, extra_fields_fn=None):
            """
            Função genérica para criação de formulários de atividade.
            
            Parâmetros:
            - key: chave única do formulário.
            - tipo: string representando o tipo da atividade (ex.: "Observação", "Whatsapp").
            - titulo_form: título exibido no cabeçalho do formulário.
            - info_msg: mensagem de informação (st.info).
            - titulo_tarefa: título da tarefa vinculada; se None, usa o mesmo valor de 'tipo'.
            - with_status: se True, exibe um selectbox para status.
            - status_options: lista de opções para o status (quando with_status é True).
            - extra_fields_fn: função opcional que insere campos extras (retorna um dicionário com os valores a serem adicionados à atividade).
            """
            with st.form(key):
                st.subheader(titulo_form)
                st.info(info_msg)
                
                # Campo comum para seleção de contatos
                contato = st.multiselect("Contato Vinculado", lista_contatos)
                
                # Se houver campos extras, eles podem ser adicionados aqui
                extra_fields = extra_fields_fn() if extra_fields_fn is not None else {}

                data_execucao = st.date_input("Data de Execução", value=datetime.today().date())
                
                # Se o formulário necessita de status, exibe o campo e captura o valor
                if with_status and status_options:
                    status_value = st.selectbox("Status", status_options)
                else:
                    status_value = None
                
                descricao = st.text_area("Descrição *")
                if tipo != 'Observação':
                    st.markdown("---")
                    st.subheader("📌 Prazo para o acompanhamento")
                    prazo = st.selectbox("Prazo", ["1 dia útil", "2 dias úteis", "3 dias úteis", 
                                                    "1 semana", "2 semanas", "1 mês", "2 meses", "3 meses"], index=3)
                    # Se houver opção "Personalizada", exibe um date_input; caso contrário, calcula a data
                    data_execucao_tarefa = st.date_input("Data de Execução", value=calcular_data_execucao(prazo)) if prazo == "Personalizada" else calcular_data_execucao(prazo)
                    
                submit_atividade = st.form_submit_button("✅ Adicionar Atividade")
                
                if submit_atividade:
                    if descricao:
                        atividade_id = str(datetime.now().timestamp())
                        
                        nova_atividade = {
                            "atividade_id": atividade_id,
                            "tipo_atividade": tipo,
                            "empresa": empresa_nome,
                            "contato": contato,
                            "descricao": descricao,
                            "vendedor_criacao": user,
                            "data_execucao_atividade": data_execucao.strftime("%Y-%m-%d"),
                            "data_criacao_atividade": datetime.now().strftime("%Y-%m-%d")
                        }
                        # Acrescenta o status à atividade se necessário
                        if with_status and status_value:
                            nova_atividade["status"] = status_value
                        # Acrescenta quaisquer campos extras fornecidos
                        nova_atividade.update(extra_fields)
                        
                        collection_atividades.insert_one(nova_atividade)

                        if tipo != 'Observação':
                            
                            random_hex = f"{random.randint(0, 0xFFFF):04x}"
                            nova_tarefa = {
                                "tarefa_id": str(datetime.now().timestamp()),
                                "titulo": f"{titulo_tarefa} ({empresa_nome} - {random_hex})" if titulo_tarefa is not None else tipo,
                                "empresa": empresa_nome,
                                "atividade_vinculada": atividade_id,
                                "data_execucao": data_execucao_tarefa.strftime("%Y-%m-%d"),
                                "status": "🟨 Em andamento",
                                "observacoes": ""
                            }
                            collection_tarefas = get_collection("tarefas")
                            collection_tarefas.insert_one(nova_tarefa)
                            
                            # Atualiza a última atividade da empresa
                            data_hoje = datetime.now().strftime("%Y-%m-%d")
                            collection_empresas = get_collection("empresas")
                            collection_empresas.update_one(
                                {"razao_social": empresa_nome},
                                {"$set": {"ultima_atividade": data_hoje}}
                            )
                        
                        st.success("Atividade adicionada com sucesso! 📌")
                        st.rerun()
                    else:
                        st.error("Preencha os campos obrigatórios: Descrição.")


        # Exemplo de chamadas dos formulários usando a função genérica

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            with st.popover("🟫➕ Obs."):
                criar_form_atividade(
                    key="form_adicionar_observacoes",
                    tipo="Observação",
                    titulo_form="🟫➕ Observação",
                    info_msg="Registrar uma **observação** nas atividades da empresa."
                )

        with col2:
            with st.popover("🟩➕ Whatsapp"):
                criar_form_atividade(
                    key="form_adicionar_whatsapp",
                    tipo="Whatsapp",
                    titulo_form="🟩➕ Whatsapp",
                    info_msg="Registrar um **Whatsapp** nas atividades da empresa.",
                    with_status=True
                )

        with col3:
            with st.popover("🟨➕ Ligação"):
                criar_form_atividade(
                    key="form_adicionar_ligacao",
                    tipo="Ligação",
                    titulo_form="🟨➕ Ligação",
                    info_msg="Registrar uma **Ligação** nas atividades da empresa.",
                    with_status=True,
                    status_options=["Conectado", "Ocupado", "Sem Resposta", "Gatekeeper", "Ligação Positiva", "Ligação Negativa"]
                )

        with col4:
            with st.popover("🟥➕ Email"):
                criar_form_atividade(
                    key="form_adicionar_email",
                    tipo="Email",
                    titulo_form="🟥➕ Email",
                    info_msg="Registrar um envio de **email** nas atividades da empresa."
                )

        with col5:
            with st.popover("🟦➕ Linkedin"):
                criar_form_atividade(
                    key="form_adicionar_linkedin",
                    tipo="Linkedin",
                    titulo_form="🟦➕ Linkedin",
                    info_msg="Registrar um envio de mensagem no **linkedin** nas atividades da empresa."
                )

        with col6:
            with st.popover("🟪➕ Reunião"):
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
                mes_ingles = data_execucao.strftime("%B")  # Nome do mês em inglês
                mes_portugues = MESES_PT.get(mes_ingles, mes_ingles)  # Traduz para PT-BR
                chave_mes_ano = (data_execucao.year, MESES_NUMERICOS[mes_portugues], f"{mes_portugues} {data_execucao.year}")

                atividades_ordenadas[chave_mes_ano].append({
                    "data": data_execucao.strftime("%d/%m/%Y"),
                    "tipo": atividade["tipo_atividade"],
                    "contato": ", ".join(atividade.get("contato", "")) if isinstance(atividade.get("contato", []), list) else atividade.get("contato", ""),
                    "descricao": atividade["descricao"],
                    "data_execucao_timestamp": data_execucao.timestamp()  # Adiciona timestamp para ordenação dentro do mês
                })

            # Ordenar os blocos de meses do mais recente para o mais antigo
            for (ano, mes_num, mes_ano_str), atividades_lista in sorted(atividades_ordenadas.items(), reverse=True):  # Ordena por ano e mês
                st.subheader(f"📅 {mes_ano_str}")  # Título do mês e ano
                
                # Ordena atividades dentro do mês do mais recente para o mais antigo
                atividades_lista.sort(key=lambda x: x["data_execucao_timestamp"], reverse=True)

                with st.container():
                    for atividade in atividades_lista:
                        if atividade["tipo"] != 'Observação':
                            st.write(f'**📆 {atividade["data"]}** - **{atividade["tipo"]}**: {atividade["contato"]}. 📝 {atividade["descricao"]}')
                        else:
                            st.write(f'**📆 {atividade["data"]}** - **{atividade["tipo"]}**: {atividade["contato"]}. 📝 {atividade["descricao"]}')

                    st.write('---')

        else:
            st.warning("Nenhuma atividade cadastrada para esta empresa.")