import streamlit as st
import plotly.graph_objects as go
import utils.database as db
import datetime

st.set_page_config(layout="wide")

collection_empresas = db.get_collection("empresas")
collection_tarefas = db.get_collection("tarefas")
collection_atividades = db.get_collection("atividades")
collection_oportunidades = db.get_collection("oportunidades")
collection_usuarios = db.get_collection("usuarios")
cols = st.columns(3)

periodo = st.selectbox(
    "Selecione o período",
    options=["Ultima semana", "Ultimo mês", "Ultimo trimestre", "Ultimo semestre", "Ultimo ano"],
)

def exibir_atividades(tamanho_total, tamanho_selecao, vendedor, periodo, tipo_atividade, key):
    if periodo == "Ultima semana" and tipo_atividade == "Todas": 
        max_val = 200
    elif periodo == "Ultimo mês" and tipo_atividade == "Todas": 
        max_val = 800
    elif periodo == "Ultimo trimestre" and tipo_atividade == "Todas": 
        max_val = 2000
    elif periodo == "Ultimo semestre" and tipo_atividade == "Todas": 
        max_val = 5000
    elif periodo == "Ultimo ano" and tipo_atividade == "Todas": 
        max_val = 10000
    elif periodo == "Ultima semana" and tipo_atividade == "Ligação": 
        max_val = 100
    elif periodo == "Ultimo mês" and tipo_atividade == "Ligação": 
        max_val = 400
    elif periodo == "Ultimo trimestre" and tipo_atividade == "Ligação": 
        max_val = 1000
    elif periodo == "Ultimo semestre" and tipo_atividade == "Ligação": 
        max_val = 2500
    elif periodo == "Ultimo ano" and tipo_atividade == "Ligação": 
        max_val = 5000
    else:
        max_val = 1000

    fig1 = go.Figure(go.Indicator(
        mode="gauge",
        value=tamanho_selecao,
        delta={'reference': 100},
        number={'suffix': "%"},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [None, max_val], 'tickvals': [max_val/2], 'ticktext': [f'{max_val/2}']},
               'bar': {'color': '#B26A1F', 'thickness': 1},
               'threshold': {'line': {'color': '#000000', 'width': 2}, 'thickness': 1, 'value': tamanho_selecao}
              },
    ))

    fig1.add_annotation(
        x=0.5,
        y=0.35,
        text=f"{tamanho_selecao} ({tamanho_selecao/max_val*100:.0f}%)",
        showarrow=False,
        font=dict(size=30),
    )

    fig1.add_annotation(
        x=0.5,
        y=-0.1,
        text="Média: 50%",
        showarrow=False,
        font=dict(size=19),
    )

    fig1.update_layout(height=220, margin=dict(t=30))
    st.plotly_chart(fig1, use_container_width=True, key=key)

def exibir_por_tipo_atividade(collection_atividades, collection_usuarios):
    # Determinar o número de dias correspondentes ao período selecionado
    if periodo == "Ultima semana":
        delta_days = 7
    elif periodo == "Ultimo mês":
        delta_days = 30
    elif periodo == "Ultimo trimestre":
        delta_days = 90
    elif periodo == "Ultimo semestre":
        delta_days = 180
    elif periodo == "Ultimo ano":
        delta_days = 365

    now = datetime.datetime.now()

    # Filtrar as atividades gerais dentro do período selecionado
    todas_atividades = list(collection_atividades.find())
    atividades_geral = []
    for atividade in todas_atividades:
        data_atividade = atividade.get("data_execucao_atividade")
        if data_atividade:
            data_atividade = datetime.datetime.strptime(data_atividade, "%Y-%m-%d")
            if data_atividade >= now - datetime.timedelta(days=delta_days):
                atividades_geral.append(atividade)

    # Agrupar as atividades gerais por "tipo_atividade"
    geral_por_tipo = {}
    for atividade in atividades_geral:
        tipo = atividade.get("tipo_atividade", "Desconhecido")
        geral_por_tipo[tipo] = geral_por_tipo.get(tipo, 0) + 1

    # Selecionar os usuários (excluindo nomes específicos)
    todos_usuarios = list(collection_usuarios.find())
    usuarios_filtrados = [
        usuario for usuario in todos_usuarios
        if usuario.get("nome") not in ["Rodrigo", "Alexandre", "Fabricio", "admin", "Paula", "Vanessa", "Edson", "Thiago"]
    ]

    # Para cada vendedor, filtrar suas atividades e agrupar por "tipo_atividade"
    for usuario in usuarios_filtrados:
        usuario_nome = usuario.get("nome", "")
        usuario_sobrenome = usuario.get("sobrenome", "")
        usuario_id = f"{usuario_nome} {usuario_sobrenome}"
        
        # Buscar atividades deste vendedor
        atividades_usuario = list(collection_atividades.find({"vendedor_criacao": usuario_id}))
        atividades_periodo = []
        for atividade in atividades_usuario:
            data_atividade = atividade.get("data_execucao_atividade")
            if data_atividade:
                data_atividade = datetime.datetime.strptime(data_atividade, "%Y-%m-%d")
                if data_atividade >= now - datetime.timedelta(days=delta_days):
                    atividades_periodo.append(atividade)
        
        # Agrupar as atividades do vendedor por tipo, ou definir 0 se não houver dados
        vendor_por_tipo = {}
        for atividade in atividades_periodo:
            tipo = atividade.get("tipo_atividade", "Desconhecido")
            vendor_por_tipo[tipo] = vendor_por_tipo.get(tipo, 0) + 1

        # Unir os tipos das atividades gerais e os do vendedor para que sempre sejam exibidos
        union_tipos = set(geral_por_tipo.keys()).union(vendor_por_tipo.keys())
        
        with st.expander(f"{usuario_nome} {usuario_sobrenome}", expanded=False):
            if union_tipos:
                col_list = st.columns(len(union_tipos))
                for i, tipo in enumerate(sorted(union_tipos)):
                    qtd = vendor_por_tipo.get(tipo, 0)
                    total_geral = geral_por_tipo.get(tipo, 0)
                    with col_list[i]:
                        exibir_atividades(total_geral, qtd, usuario_id, periodo, tipo, key=f"gauge-{usuario_id}-{tipo}")
            else:
                st.write("Sem atividades no período.")

# Chamada da função (assegurando que as coleções estejam previamente definidas)
exibir_por_tipo_atividade(collection_atividades, collection_usuarios)