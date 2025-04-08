import streamlit as st
from utils.database import get_collection
from datetime import datetime, timedelta
import pandas as pd
import datetime as dt
import calendar
import modules.gerar_orcamento as gro
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import re
import hashlib
from bson import ObjectId
import ast

def base36encode(number):
    """Converte um número inteiro para uma string em base36 (0-9, A-Z)."""
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if number == 0:
        return alphabet[0]
    base36 = ""
    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36
    return base36

def gerar_hash_6(objid):
    """
    Gera um hash de 6 caracteres (números e letras maiúsculas) a partir do _id.
    """
    # Converte o ObjectId para string antes de codificar
    objid_str = str(objid)
    md5_hash = hashlib.md5(objid_str.encode("utf-8")).hexdigest()
    hash_int = int(md5_hash, 16)
    # 36^6 define o espaço de 6 dígitos em base36
    mod_value = 36**6
    hash_mod = hash_int % mod_value
    hash_base36 = base36encode(hash_mod).zfill(6)
    return hash_base36

def calcular_parcelas_e_saldo(amount, parcela_fixa):
    # Calcula o número máximo de parcelas possíveis
    
    # Cria uma lista para armazenar as combinações
    combinacoes = []
    texto_prop = ". à partir do aceite da proposta ou assinatura do contrato,"
    texto_prop1 = ". após a entrega do serviço contratado,"
    texto_entrada = " e saldo na entrega do serviço contratado,"

    # Adiciona a opção à vista
    
    combinacoes.append(f"Total à vista de R$ {amount:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))
    combinacoes.append(f"Total à vista de R$ {amount:,.2f}{texto_prop1}".replace(",", "X").replace(".", ",").replace("X", "."))
    combinacoes.append(f"50% de entrada no valor de R$ {(amount/2):,.2f}{texto_entrada}".replace(",", "X").replace(".", ",").replace("X", "."))
    combinacoes.append(f"30% de entrada no valor de R$ {(amount*0.3):,.2f}{texto_entrada}".replace(",", "X").replace(".", ",").replace("X", "."))
    combinacoes.append(f"4x de R$ {(amount/4):,.2f} com entrada para 7 dias após a assinatura do contrato".replace(",", "X").replace(".", ",").replace("X", "."))

    if amount >= 12000 and amount < 18000: 
        combinacoes.append(f"2x de R$ {amount/2:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))
    elif amount >= 18000 and amount < 24000: 
        combinacoes.append(f"2x de R$ {amount/2:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))
        combinacoes.append(f"3x de R$ {amount/3:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))
    elif amount >= 24000 and amount <= 30000:
        combinacoes.append(f"2x de R$ {amount/2:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))
        combinacoes.append(f"3x de R$ {amount/3:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))
        combinacoes.append(f"4x de R$ {amount/4:,.2f}{texto_prop}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Calcular a entrada e verificar a condição
    if amount > 30000:
        entrada = amount * 0.2
        saldo_restante = amount - entrada
        
        # Encontrar o menor múltiplo da parcela fixa que seja maior que o saldo restante
        num_parcelas = 10
        if saldo_restante % parcela_fixa != 0:
            num_parcelas += 1
        
        for i in range(1, int(num_parcelas)):
            saldo_a_pagar = saldo_restante / i
            if saldo_a_pagar >= parcela_fixa:
                combinacoes.append(
                    f"Entrada de {entrada:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + 
                    f" e {i}x de R$ {saldo_a_pagar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                                    
    return combinacoes

def format_currency(value):
    """
    Formata um valor numérico no padrão brasileiro de moeda:
    Exemplo: 10900.0 -> "R$ 10.900,00"
    """
    return "R$ " + "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")
                
def elaborar_orcamento(user, email, senha, admin):
    # Obter as coleções necessárias
    collection_empresas = get_collection("empresas")
    collection_oportunidades = get_collection("oportunidades")
    collection_contatos = get_collection("contatos")  # Supondo que exista uma coleção de contatos
    collection_produtos = get_collection("produtos")

    if not admin:
        # 1. Seleção da Empresa
        empresas = list(
            collection_empresas.find(
                {"proprietario": user}, 
                {"_id": 0, "razao_social": 1, "cnpj": 1}
            )
        )
        if not empresas:
            st.warning("Nenhuma empresa encontrada para o usuário.")
            return
    else:
        # Se o usuário for admin, listar todas as empresas
        empresas = list(
            collection_empresas.find(
                {}, 
                {"_id": 0, "razao_social": 1, "cnpj": 1}
            )
        )
        if not empresas:
            st.warning("Nenhuma empresa encontrada.")
            return

    opcoes_empresas = [f"{empresa['razao_social']}" for empresa in empresas]
    
    st.subheader("🏢 Seleção da empresa e negócio")
    selected_empresa = st.selectbox("**Selecione a Empresa:**", opcoes_empresas, key="orcamento_empresa")
    # Extrair o nome da empresa (razao_social) a partir da string
    empresa_nome = selected_empresa

    # 2. Seleção do Negócio (Oportunidade) vinculado à empresa selecionada
    oportunidades = list(
        collection_oportunidades.find(
            {"cliente": empresa_nome},
            {"_id": 1, "cliente": 1, "nome_oportunidade": 1, "proprietario": 1, "produtos": 1, "valor_estimado": 1,"valor_orcamento": 1, "data_criacao": 1, "data_fechamento": 1, "estagio": 1, 'aprovacao_gestor': 1, 'solicitacao_desconto': 1, 'desconto_solicitado': 1, 'desconto_aprovado': 1, 'contatos_selecionados': 1, 'contato_principal': 1, 'condicoes_pagamento': 1, 'prazo_execucao': 1, 'categoria': 1, 'tipo': 1, 'tamanho': 1}
        )
    )
    if not oportunidades:
        st.warning("Nenhum negócio encontrado para essa empresa.")
    else:
        opcoes_negocios = [
            opp["nome_oportunidade"] 
            for opp in oportunidades 
            if opp.get("estagio") not in ["Perdido", "Fechado"]
        ]
        selected_negocio = st.selectbox("**Selecione o Negócio:**", opcoes_negocios, key="orcamento_negocio")

        # Buscar os dados    do negócio selecionado
        negocio_selecionado = next((opp for opp in oportunidades if opp["nome_oportunidade"] == selected_negocio), None)

        st.write('----')
        if negocio_selecionado:
            st.subheader("ℹ️ Informações do Negócio para orçamento")

            objid = ObjectId(negocio_selecionado['_id'])
            negocio_id = gerar_hash_6(objid)

            # Conecta na coleção de produtos
            collection_produtos = get_collection("produtos")

            # Consulta as categorias existentes e monta a lista de opções
            categorias_existentes = collection_produtos.distinct("categoria")
            categoria_options = [''] + categorias_existentes

            # Define a categoria padrão, se disponível
            default_categoria = negocio_selecionado.get("categoria", "")
            default_categoria_index = categoria_options.index(default_categoria) if default_categoria in categoria_options else 0

            categoria_orcamento = st.selectbox("Categoria: *", categoria_options, index=default_categoria_index)

            tipo_empreendimento = None
            tamanho_empreendimento = None

            if categoria_orcamento:
                # Consulta os tipos existentes para a categoria selecionada
                tipos_existentes = collection_produtos.distinct("tipo", {"categoria": categoria_orcamento})
                tipo_options = [''] + tipos_existentes

                # Define o tipo padrão, se disponível
                default_tipo = negocio_selecionado.get("tipo", "")
                default_tipo_index = tipo_options.index(default_tipo) if default_tipo in tipo_options else 0

                tipo_empreendimento = st.selectbox("Tipo do empreendimento: *", tipo_options, index=default_tipo_index)

                if tipo_empreendimento:
                    # Consulta os tamanhos existentes para a combinação de categoria e tipo
                    tamanhos_existentes = collection_produtos.distinct("tamanho", {"categoria": categoria_orcamento, "tipo": tipo_empreendimento})
                    tamanho_options = [''] + tamanhos_existentes

                    # Define o tamanho padrão, se disponível
                    default_tamanho = negocio_selecionado.get("tamanho", "")
                    default_tamanho_index = tamanho_options.index(default_tamanho) if default_tamanho in tamanho_options else 0

                    tamanho_empreendimento = st.selectbox("Tamanho: *", tamanho_options, index=default_tamanho_index)

            # Consulta o documento de produto com base na seleção
            if categoria_orcamento and tipo_empreendimento and tamanho_empreendimento:
                filtro_produto = {
                    "categoria": categoria_orcamento,
                    "tipo": tipo_empreendimento,
                    "tamanho": tamanho_empreendimento
                }
                documento_produto = collection_produtos.find_one(filtro_produto)

                if documento_produto:
                    nome_produto = documento_produto.get("nome", "Consultoria HYGGE")
                    preco_modelagem = documento_produto.get("preco_modelagem", 0)
                    preco_servico = documento_produto.get("preco_servico", 0)
                else:
                    st.write("Nenhum nome/preço encontrado para essa combinação.")

                # Coleta todos os serviços adicionais disponíveis em collection_produtos

                if 'NBR Eco' in tipo_empreendimento: nomes_produtos = ['Laudo NBR Economy']
                elif 'Aditivo' in tipo_empreendimento: nomes_produtos = ['Aditivo de NBR 15.575']
                elif 'NBR Fast' in tipo_empreendimento: nomes_produtos = ['Laudo NBR Fast']
                elif 'NBR' in tipo_empreendimento: nomes_produtos = ['NBR Fast - Laudo diagnóstico normativo da NBR 15.575']
                elif 'Consultoria' in tipo_empreendimento: nomes_produtos = ['Consultoria Hygge']
                elif 'Auditoria' in tipo_empreendimento and 'Certificação' in tipo_empreendimento: nomes_produtos = ['Certificação EDGE', 'Auditoria EDGE']
                elif 'Certificação' in tipo_empreendimento and 'EDGE' in tipo_empreendimento: nomes_produtos = ['Certificação EDGE']
                elif 'Certificação' in tipo_empreendimento and  'Fitwell' in tipo_empreendimento: nomes_produtos = ['Certificação Fitwell']
                elif 'Auditoria' in tipo_empreendimento and 'EDGE' in tipo_empreendimento: nomes_produtos = ['Auditoria EDGE']
                elif 'GBC' in tipo_empreendimento: nomes_produtos = ['GBC Casa Condomínio']
                else: nomes_produtos = [nome_produto]

                lista_escopo = []  # Será uma lista de listas; cada sublista corresponde ao "escopo" de um produto

                # Consulta todos os produtos cujo campo "tipo" seja igual a tipo_empreendimento
                produto = collection_produtos.find({"tipo": tipo_empreendimento})

                # Obtém o campo "escopo" (espera-se que seja uma lista)
                escopo = produto[0].get("escopo", [])
                # Caso o campo não seja uma lista, converte para lista
                if not isinstance(escopo, list):
                    escopo = [escopo]
                lista_escopo.append(escopo)

                #st.write("Lista de escopos com base no tipo:", lista_escopo)

                for produto in collection_produtos.find({}):
                    servicos = produto.get("servicos_adicionais")
                    if servicos:
                        # Se já for um dicionário, utilize-o diretamente
                        if isinstance(servicos, dict):
                            servicos_dict = servicos
                        else:
                            try:
                                servicos_dict = ast.literal_eval(servicos)
                            except Exception as e:
                                servicos_dict = {}
                        # Adiciona as chaves (nomes dos serviços) na lista, se ainda não estiverem presentes
                        for servico in servicos_dict.keys():
                            if servico not in nomes_produtos:
                                nomes_produtos.append(servico)
                                
                #st.write(nomes_produtos)
                #st.write('1')                
                st.text('Selecione o(s) produto(s) para o orçamento:')

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    produtos_selecionado1 = st.multiselect(
                        "Produto 1:",
                        options=nomes_produtos,
                        default=nomes_produtos[0],
                        key="select_produto_oportunidade1",
                        placeholder='Selecione aqui...',
                        disabled=True
                    )

                if 'Certificação EDGE' in nomes_produtos and 'Auditoria EDGE' in nomes_produtos:     
                    with col2:
                        produtos_selecionado2 = st.multiselect(
                            "Produto 2:",
                            options=nomes_produtos,
                            default=nomes_produtos[1],
                            key="select_produto_oportunidade2",
                            placeholder='Selecione aqui...',
                            disabled=True
                        )
                
                else:
                    with col2:
                        produtos_selecionado2 = st.multiselect(
                            "Produto 2:",
                            options=nomes_produtos,
                            #default='',
                            key="select_produto_oportunidade2",
                            placeholder='Selecione aqui...'
                        )
                with col3:
                    produtos_selecionado3 = st.multiselect(
                        "Produto 3:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade3",
                        placeholder='Selecione aqui...'
                    )
                with col4:
                    produtos_selecionado4 = st.multiselect(
                        "Produto 4:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade4",
                        placeholder='Selecione aqui...'
                    )
                with col5:
                    produtos_selecionado5 = st.multiselect(
                        "Produto 5:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade5",
                        placeholder='Selecione aqui...'
                    )
                
                col6, col7, col8, col9, col10 = st.columns(5)
                with col6:
                    produtos_selecionado6 = st.multiselect(
                        "Produto 6:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade6",
                        placeholder='Selecione aqui...'
                    )
                with col7:
                    produtos_selecionado7 = st.multiselect(
                        "Produto 7:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade7",
                        placeholder='Selecione aqui...'
                    )
                with col8:
                    produtos_selecionado8 = st.multiselect(
                        "Produto 8:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade8",
                        placeholder='Selecione aqui...'
                    )
                with col9:
                    produtos_selecionado9 = st.multiselect(
                        "Produto 9:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade9",
                        placeholder='Selecione aqui...'
                    )
                with col10:
                    produtos_selecionado10 = st.multiselect(
                        "Produto 10:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade10",
                        placeholder='Selecione aqui...'
                    )

                produtos_selecionados = [p[0] for p in [produtos_selecionado1, produtos_selecionado2, produtos_selecionado3, produtos_selecionado4, produtos_selecionado5,
                                            produtos_selecionado6, produtos_selecionado7, produtos_selecionado8, produtos_selecionado9, produtos_selecionado10] if p]
                
                negocio_selecionado['produtos'] = produtos_selecionados

                size_produtos = len(produtos_selecionados)-1
                for p in produtos_selecionados:
                    if p == 'Cenário adicional de simulação':
                        lista_escopo.append(['Contempla 1 (uma) simulação computacional térmica e lumínica natural adicional'])
                        size_produtos-=1

                for i in range(size_produtos):
                    lista_escopo.append([])

                if len(produtos_selecionados) > 0:
                    #st.write(negocio_selecionado)

                    # Itera sobre a lista de produtos selecionados, adicionando o objeto correspondente para cada ocorrência
                    produtos_selecionados_obj = produtos_selecionados

                    total = preco_modelagem + preco_servico

                    # Tenta recuperar o dicionário de serviços adicionais do documento de produto
                    servicos_adicionais = documento_produto.get("servicos_adicionais", {})
                    # Caso não seja um dicionário, tenta converter
                    if not isinstance(servicos_adicionais, dict):
                        try:
                            servicos_adicionais = ast.literal_eval(servicos_adicionais)
                        except Exception as e:
                            servicos_adicionais = {}

                    # Itera sobre os produtos selecionados e soma os preços dos serviços adicionais, se existentes
                    for produto in produtos_selecionados:
                        # Verifica se o produto selecionado está no dicionário e se o valor é numérico
                        valor = servicos_adicionais.get(produto)
                        if valor and isinstance(valor, (int, float)):
                            total += valor
                    
                    valor_estimado_formatado = format_currency(total)
                    desconto = st.number_input("Desconto (%)", 0.0, 100.0, format="%.8f")
                    desconto_total = total*(desconto/100)
                    valor_negocio = total - desconto_total
                    valor_negocio_formatado = format_currency(valor_negocio)
                    col1, col2 = st.columns(2)
                    with col1:  st.warning(f"**Preço total dos produtos selecionados:** {valor_estimado_formatado}")
                    with col2:  st.warning(f"**Preço total com descontos:** {valor_negocio_formatado}")
                    #**Preço com o desconto aplicado:** {valor_negocio_formatado}")
                    condicoes = calcular_parcelas_e_saldo(float(valor_negocio), 6000)
                    
                    # Valor salvo no banco para a condição de pagamento (se existir)
                    default_condicao = negocio_selecionado.get('condicoes_pagamento', None)

                    # Se existir e estiver na lista de opções, encontra o índice correspondente;
                    # caso contrário, usa o índice 0 (primeira opção da lista)
                    if default_condicao and default_condicao in condicoes:
                        default_index = condicoes.index(default_condicao)
                    else:
                        default_index = 0

                    condicao_pagamento = st.selectbox('Condições de pagamento:', condicoes, index=default_index)

                    if float(valor_negocio) > 35000:
                        prazos = ['60 dias úteis após o recebimento da documentação completa.',
                                '30 dias úteis após o recebimento da documentação completa.',
                                '20 dias úteis após o recebimento da documentação completa.']
                    
                    else: prazos = ['60 dias úteis após o recebimento da documentação completa.',
                                '30 dias úteis após o recebimento da documentação completa.',
                                '20 dias úteis após o recebimento da documentação completa.',
                                '15 dias úteis após o recebimento da documentação completa.',
                                '10 dias úteis após o recebimento da documentação completa.']

                    # 1. Prazo de execução
                    default_prazo = negocio_selecionado.get('prazo_execucao', None)
                    if default_prazo and default_prazo in prazos:
                        prazo_index = prazos.index(default_prazo)
                    else:
                        prazo_index = 0
                    prazo = st.selectbox("Prazo de execução:", prazos, index=prazo_index)

                    # 2. Seleção dos Contatos da Empresa (pode ser múltiplo)
                    contatos = list(
                        collection_contatos.find(
                            {"empresa": empresa_nome},
                            {"_id": 0, "nome": 1, "email": 1, "sobrenome": 1}  # Incluindo sobrenome para contato principal
                        )
                    )
                    if contatos:
                        opcoes_contatos = [f"{c.get('email', 'Sem email')}" for c in contatos]
                        nomes_contatos = [f"{c.get('nome', 'Sem nome')} {c.get('sobrenome', '')}" for c in contatos]

                        # Valor padrão para contatos selecionados (campo 'contatos_selecionados' da oportunidade)
                        default_contatos = negocio_selecionado.get("contatos_selecionados", [])
                        # Filtra os defaults para que estejam entre as opções disponíveis
                        default_contatos = [d for d in default_contatos if d in opcoes_contatos]

                        selected_contatos = st.multiselect(
                            "Selecione os contatos da empresa que receberão o orçamento:",
                            opcoes_contatos,
                            key="orcamento_contatos",
                            placeholder='Selecione os contatos aqui...',
                            default=default_contatos
                        )

                        # Valor padrão para o contato principal (campo 'contato_principal' da oportunidade)
                        default_contato_principal = negocio_selecionado.get("contato_principal", None)
                        if default_contato_principal and default_contato_principal in nomes_contatos:
                            contato_index = nomes_contatos.index(default_contato_principal)
                        else:
                            contato_index = 0
                        nome_contato_principal = st.selectbox(
                            "Selecione o contato principal (A/C):",
                            nomes_contatos,
                            key="orcamento_contato_principal",
                            index=contato_index
                        )
                    else:
                        st.error("Nenhum contato encontrado para essa empresa.")
                        selected_contatos = []

                    st.write('-----')
                    st.header("📄 Geração de orçamentos")
                    st.info("A geração do orçamento pode levar alguns segundos, aguarde a conclusão de cada etapa, tanto para geração do PDF quanto o upload no OneDrive.")
                    st.write('----')
                    st.subheader("📄 Geração de um orçamento convencional")
                    if st.button("Gerar o orçamento"):
                        if desconto <= negocio_selecionado['desconto_aprovado']:  
                            inicio = time.time()
                            pdf_out_path = gro.generate_proposal_pdf2(selected_empresa, negocio_id, selected_negocio, produtos_selecionados_obj, valor_negocio, desconto_total, condicao_pagamento, prazo, nome_contato_principal, lista_escopo)
                            if pdf_out_path:
                                versao_proposta = gro.upload_onedrive2(pdf_out_path)
                                #st.write(versao_proposta)
                                path_proposta_envio = pdf_out_path.replace('.pdf',f'_v0{versao_proposta}.pdf')
                                fim = time.time()
                                st.info(f"Tempo da operação: {round(fim-inicio,2)}s")
                                novo_nome_arquivo = os.path.basename(path_proposta_envio)

                                # Atualiza o documento da oportunidade com as novas informações
                                collection_oportunidades.update_one(
                                    {"cliente": empresa_nome, "nome_oportunidade": selected_negocio},
                                    {"$set": {
                                        "produtos": produtos_selecionados,
                                        "valor_orcamento": valor_negocio_formatado,
                                        "condicoes_pagamento": condicao_pagamento,
                                        "prazo_execucao": prazo,
                                        "contato_principal": nome_contato_principal,
                                        "contatos_selecionados": selected_contatos
                                    }}
                                )
                            else: st.error('Erro na geração do orçamento, fale com o seu gestor.')
                        
                        else:
                            st.error('⚠️ Desconto ainda não aprovado pelo gestor. Solicite abaixo aprovação do desconto ou aguarde a decisão antes de gerar a proposta.')
                    
                    st.write('-----')
                    st.subheader("📝 Geração de um orçamento com aprovação de desconto adicional")
                    with st.expander('Solicitação de desconto adicional ao gestor', expanded=False):
                        st.error('⚠️ Descontos acima de 20% devem ser aprovados pelo gestor responsável.') 
                        
                        if negocio_selecionado['aprovacao_gestor']: 
                            st.markdown(f"🟩 Desconto aprovado pelo gestor de até {negocio_selecionado['desconto_aprovado']}%.")
                            justificativa = st.text_area("Justificativa para solicitação de novo desconto adicional:")
                            if st.button(f'Solicitar novo desconto de {desconto}%'):
                                receivers = ['fabricio@hygge.eco.br', email]
                                #receivers = [email]
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'Solicitação de desconto adicional - {selected_negocio}'
                                
                                body = f"""<p>Vendedor: {negocio_selecionado['proprietario']}</p>
                                            <p>Empresa: {negocio_selecionado['cliente']}</p>
                                            <p>Projeto: {negocio_selecionado['nome_oportunidade']}</p>
                                            <p>Produto(s): {produtos_selecionados}</p>
                                            <p>Desconto solicitado: {desconto}%</p>
                                            <p>Valor do orçamento inicial: {valor_estimado_formatado}</p>
                                            <p>Novo valor do orçamento: {valor_negocio_formatado}</p>
                                            <p>Justificativa: {justificativa}</p>
                                            <p>Acesse a plataforma integrada para aprovar ou reprovar a solicitação.</p>"""

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")

                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"desconto_solicitado": float(desconto)}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"solicitacao_desconto": True}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"aprovacao_gestor": False}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"condicoes_pagamento": condicao_pagamento}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"prazo_execucao": prazo}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contato_principal": nome_contato_principal}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contatos_selecionados": selected_contatos}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"produtos": produtos_selecionados}})
                                st.success('Solicitação de desconto enviada com sucesso.')
                                st.rerun()

                        elif negocio_selecionado['solicitacao_desconto']: 
                            st.markdown(f"🟨 Em análise pelo gestor a solicitação de um desconto de {negocio_selecionado['desconto_solicitado']}%.")
                        
                        elif not negocio_selecionado['solicitacao_desconto']:
                            st.markdown('🟦 Sem solicitação de desconto.')
                            justificativa = st.text_area("Justificativa para solicitação de desconto adicional:")
                            if st.button(f'Solicitar desconto de {desconto}%'):
                            
                                receivers = ['fabricio@hygge.eco.br', email]
                                #receivers = [email]
                                
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'Solicitação de desconto adicional - {selected_negocio}'
                                
                                body = f"""<p>Vendedor: {negocio_selecionado['proprietario']}</p>
                                            <p>Empresa: {negocio_selecionado['cliente']}</p>
                                            <p>Projeto: {negocio_selecionado['nome_oportunidade']}</p>
                                            <p>Produto(s): {produtos_selecionados}</p>
                                            <p>Desconto solicitado: {desconto}%</p>
                                            <p>Valor do orçamento inicial: {valor_estimado_formatado}</p>
                                            <p>Novo valor do orçamento: {valor_negocio_formatado}</p>
                                            <p>Justificativa: {justificativa}</p>
                                            <p>Acesse a plataforma integrada para aprovar ou reprovar a solicitação.</p>"""

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")
                                
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"desconto_solicitado": float(desconto)}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"solicitacao_desconto": True}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"aprovacao_gestor": False}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"condicoes_pagamento": condicao_pagamento}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"prazo_execucao": prazo}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contato_principal": nome_contato_principal}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contatos_selecionados": selected_contatos}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"produtos": produtos_selecionados}})
                                st.success('Solicitação de desconto enviada com sucesso.')
                                st.rerun()

                        elif not negocio_selecionado['aprovacao_gestor']: 
                            st.markdown('🟥 Desconto não aprovado.')
                    
                    if st.button("Gerar o orçamento com o desconto adicional aprovado"):
                        if desconto <= negocio_selecionado['desconto_aprovado']:  
                            inicio = time.time()
                            pdf_out_path = gro.generate_proposal_pdf2(selected_empresa, negocio_id, selected_negocio, produtos_selecionados_obj, valor_negocio, desconto_total, condicao_pagamento, prazo, nome_contato_principal, lista_escopo)
                            if pdf_out_path:
                                versao_proposta = gro.upload_onedrive2(pdf_out_path)
                                #   versao_proposta)
                                path_proposta_envio = pdf_out_path.replace('.pdf',f'_v0{versao_proposta}.pdf')
                                fim = time.time()
                                st.info(f"Tempo da operação: {round(fim-inicio,2)}s")
                                novo_nome_arquivo = os.path.basename(path_proposta_envio)

                                # Atualiza o documento da oportunidade com as novas informações
                                collection_oportunidades.update_one(
                                    {"cliente": empresa_nome, "nome_oportunidade": selected_negocio},
                                    {"$set": {
                                        "produtos": produtos_selecionados,
                                        "valor_orcamento": valor_negocio_formatado,
                                        "condicoes_pagamento": condicao_pagamento,
                                        "prazo_execucao": prazo,
                                        "contato_principal": nome_contato_principal,
                                        "contatos_selecionados": selected_contatos,
                                        "categoria": categoria_orcamento,
                                        "tipo": tipo_empreendimento,
                                        "tamanho": tamanho_empreendimento
                                    }}
                                )
                            else: st.error('Erro na geração do orçamento.')
                        
                        else:
                            st.error('⚠️ Desconto ainda não aprovado pelo gestor. Solicite abaixo aprovação do desconto ou aguarde a decisão antes de gerar a proposta.')
                    
                    st.write('-----')
                    
                    st.subheader("📨 Envio da proposta para o cliente")

                    if st.button('Enviar orçamento para o cliente'):
                        receivers = selected_contatos + [email,'fabricio@hygge.eco.br','alexandre@hygge.eco.br','rodrigo@hygge.eco.br','paula@hygge.eco.br']
                        
                        message = MIMEMultipart()
                        message["From"] = email
                        message["To"] = ", ".join(receivers)
                        message["Subject"] = f'Proposta Técnico-Comercial Hygge - {selected_negocio}'

                        # Corpo do email original
                        body = f"""<p>Olá {nome_contato_principal},</p>
                        <p>Conforme solicitado, segue em anexo a proposta técnico comercial da Hygge para o empreendimento {selected_negocio}.</p>
                        <p>Estamos à disposição para quaisquer dúvidas ou esclarecimentos.</p>
                        <p>Atenciosamente,</p>"""
                        
                        if email == 'comercial2@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/thiago-lecheta.html"
                        elif email == 'matheus@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-duarte.html"
                        elif email == 'fabricio@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fabricio-lucchesi.html"
                        elif email == 'alexandre@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"
                        #elif email == 'comercial6@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/maria-eduarda-ferreira.html"  
                        elif email == 'comercial5@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-rodrigues.html"  
                        elif email == 'comercial4@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alceu-junior.html"   
                        elif email == 'comercial3@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/victor-oliveira.html"
                        #elif email == 'comercial1@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fernando-tohme.html"
                        elif email == 'rodrigo@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"
                        elif email == 'admin@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"

                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        response = requests.get(url, headers=headers)
                        html_signature = response.text

                        # Concatena o corpo do email com a assinatura HTML
                        full_body = body + html_signature

                        # Anexa o corpo do email completo no formato HTML
                        message.attach(MIMEText(full_body, "html"))

                        path_proposta_envio = gro.get_versao(f"{selected_negocio}_{negocio_id}")
                        if path_proposta_envio:
                            novo_nome_arquivo = os.path.basename(path_proposta_envio)
                            
                            # Attach the PDF file
                            with open(path_proposta_envio, 'rb') as attachment:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(attachment.read())
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', 'attachment', filename=novo_nome_arquivo)
                                message.attach(part)

                            # Sending the email
                            try:
                                server = smtplib.SMTP('smtp.office365.com', 587)
                                server.starttls()
                                server.login(email, senha)
                                server.sendmail(email, receivers, message.as_string())
                                server.quit()
                                st.success(f'Etapa 1 de 1 - Email enviado com sucesso com a proposta {novo_nome_arquivo}!')
                            except Exception as e:
                                st.error(f"Falha no envio do email: {e}")
                        
                        else: st.error("Arquivo não localizado na pasta '11. Orçamentos', gere um orçamento para enviá-lo ao cliente.")

                    st.write('-----')
                
def gerar_orcamento(empresa_id, collection_oportunidades, collection_empresas, collection_produtos, collection_contatos, user, admin, email):
    
    # busca no banco  empresa com id da empresa_id
    empresa_nome = collection_empresas.find_one({"_id": ObjectId(empresa_id)})['razao_social']

    # 2. Seleção do Negócio (Oportunidade) vinculado à empresa selecionada
    oportunidades = list(
        collection_oportunidades.find(
            {"empresa_id": empresa_id},
            {"_id": 1, "cliente": 1, "nome_oportunidade": 1, "proprietario": 1, "produtos": 1, "valor_estimado": 1,"valor_orcamento": 1, "data_criacao": 1, "data_fechamento": 1, "estagio": 1, 'aprovacao_gestor': 1, 'solicitacao_desconto': 1, 'desconto_solicitado': 1, 'desconto_aprovado': 1, 'contatos_selecionados': 1, 'contato_principal': 1, 'condicoes_pagamento': 1, 'prazo_execucao': 1, 'categoria': 1, 'tipo': 1, 'tamanho': 1, 'desconto_aplicado': 1, 'desconto_aprovado': 1}
        )
    )
    if not oportunidades:
        st.warning("Nenhum negócio encontrado para essa empresa.")
    else:
        opcoes_negocios = [
            opp["nome_oportunidade"] 
            for opp in oportunidades 
            if opp.get("estagio") not in ["Perdido", "Fechado"]
        ]

        st.subheader("ℹ️ Informações do Negócio para orçamento")

        def atualizar_informacoes():
            # Salva a aba atualmente selecionada no st.session_state para que ela seja mantida
            st.fragment()
            st.session_state["selected_tab"] = "Adicionar orçamento"  # substitua pelo nome/índice da aba que deseja manter

        selected_negocio = st.selectbox(
            "Selecione o Negócio: *",
            opcoes_negocios,
            key="orcamento_negocio_gerar",
            on_change=atualizar_informacoes
        )

        # Buscar os dados do negócio selecionado (novamente consultado quando a seleção mudar)
        negocio_selecionado = next((opp for opp in oportunidades if opp["nome_oportunidade"] == selected_negocio), None)
        
        if negocio_selecionado:

            objid = ObjectId(negocio_selecionado['_id'])
            negocio_id = gerar_hash_6(objid)

            # Conecta na coleção de produtos
            collection_produtos = get_collection("produtos")

            # Consulta as categorias existentes e monta a lista de opções
            categorias_existentes = collection_produtos.distinct("categoria")
            categoria_options = [''] + categorias_existentes

            # Se o negócio já possuir a categoria configurada no banco, a pré-preenche
            default_categoria = negocio_selecionado.get("categoria", "")
            default_categoria_index = categoria_options.index(default_categoria) if default_categoria in categoria_options else 0
            
            cols = st.columns(3)
            with cols[0]:
                categoria_orcamento = st.selectbox("Categoria: *", categoria_options, index=default_categoria_index)

            tipo_empreendimento = None
            tamanho_empreendimento = None

            with cols[1]:
                if categoria_orcamento:
                    # Consulta os tipos existentes para a categoria selecionada
                    tipos_existentes = collection_produtos.distinct("tipo", {"categoria": categoria_orcamento})
                    tipo_options = [''] + tipos_existentes

                    # Pré-preenche o tipo se configurado no negócio
                    default_tipo = negocio_selecionado.get("tipo", "")
                    default_tipo_index = tipo_options.index(default_tipo) if default_tipo in tipo_options else 0

                    tipo_empreendimento = st.selectbox("Tipo do empreendimento: *", tipo_options, index=default_tipo_index)

            with cols[2]:
                if categoria_orcamento and tipo_empreendimento:
                    # Consulta os tamanhos existentes para a combinação de categoria e tipo
                    tamanhos_existentes = collection_produtos.distinct("tamanho", {"categoria": categoria_orcamento, "tipo": tipo_empreendimento})
                    tamanho_options = [''] + tamanhos_existentes

                    # Pré-preenche o tamanho se configurado no negócio
                    default_tamanho = negocio_selecionado.get("tamanho", "")
                    default_tamanho_index = tamanho_options.index(default_tamanho) if default_tamanho in tamanho_options else 0

                    tamanho_empreendimento = st.selectbox("Tamanho: *", tamanho_options, index=default_tamanho_index)

            # Consulta o documento de produto com base na seleção
            if categoria_orcamento and tipo_empreendimento and tamanho_empreendimento:
                filtro_produto = {
                    "categoria": categoria_orcamento,
                    "tipo": tipo_empreendimento,
                    "tamanho": tamanho_empreendimento
                }
                documento_produto = collection_produtos.find_one(filtro_produto)

                if documento_produto:
                    nome_produto = documento_produto.get("nome", "Consultoria HYGGE")
                    preco_modelagem = documento_produto.get("preco_modelagem", 0)
                    preco_servico = documento_produto.get("preco_servico", 0)
                else:
                    st.write("Nenhum nome/preço encontrado para essa combinação.")

                # Coleta todos os serviços adicionais disponíveis em collection_produtos

                if 'NBR Eco' in tipo_empreendimento: nomes_produtos = ['Laudo NBR Economy']
                elif 'Aditivo' in tipo_empreendimento: nomes_produtos = ['Aditivo de NBR 15.575']
                elif 'NBR Fast' in tipo_empreendimento: nomes_produtos = ['Laudo NBR Fast']
                elif 'NBR' in tipo_empreendimento: nomes_produtos = ['NBR Fast - Laudo diagnóstico normativo da NBR 15.575']
                elif 'Consultoria' in tipo_empreendimento: nomes_produtos = ['Consultoria Hygge']
                elif 'Auditoria' in tipo_empreendimento and 'Certificação' in tipo_empreendimento: nomes_produtos = ['Certificação EDGE', 'Auditoria EDGE']
                elif 'Certificação' in tipo_empreendimento and 'EDGE' in tipo_empreendimento: nomes_produtos = ['Certificação EDGE']
                elif 'Certificação' in tipo_empreendimento and  'Fitwell' in tipo_empreendimento: nomes_produtos = ['Certificação Fitwell']
                elif 'Auditoria' in tipo_empreendimento and 'EDGE' in tipo_empreendimento: nomes_produtos = ['Auditoria EDGE']
                elif 'GBC' in tipo_empreendimento: nomes_produtos = ['GBC Casa Condomínio']
                else: nomes_produtos = [nome_produto]

                lista_escopo = []  # Será uma lista de listas; cada sublista corresponde ao "escopo" de um produto

                # Consulta todos os produtos cujo campo "tipo" seja igual a tipo_empreendimento
                produto = collection_produtos.find({"tipo": tipo_empreendimento})

                # Obtém o campo "escopo" (espera-se que seja uma lista)
                escopo = produto[0].get("escopo", [])
                # Caso o campo não seja uma lista, converte para lista
                if not isinstance(escopo, list):
                    escopo = [escopo]
                lista_escopo.append(escopo)

                #st.write("Lista de escopos com base no tipo:", lista_escopo)

                for produto in collection_produtos.find({}):
                    servicos = produto.get("servicos_adicionais")
                    if servicos:
                        # Se já for um dicionário, utilize-o diretamente
                        if isinstance(servicos, dict):
                            servicos_dict = servicos
                        else:
                            try:
                                servicos_dict = ast.literal_eval(servicos)
                            except Exception as e:
                                servicos_dict = {}
                        # Adiciona as chaves (nomes dos serviços) na lista, se ainda não estiverem presentes
                        for servico in servicos_dict.keys():
                            if servico not in nomes_produtos:
                                nomes_produtos.append(servico)
                                
                #st.write(nomes_produtos)
                #st.write('1')                
                st.text('Selecione o(s) produto(s) para o orçamento:')

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    produtos_selecionado1 = st.multiselect(
                        "Produto 1:",
                        options=nomes_produtos,
                        default=nomes_produtos[0],
                        key="select_produto_oportunidade1",
                        placeholder='Selecione aqui...',
                        disabled=True
                    )

                if 'Certificação EDGE' in nomes_produtos and 'Auditoria EDGE' in nomes_produtos:     
                    with col2:
                        produtos_selecionado2 = st.multiselect(
                            "Produto 2:",
                            options=nomes_produtos,
                            default=nomes_produtos[1],
                            key="select_produto_oportunidade2",
                            placeholder='Selecione aqui...',
                            disabled=True
                        )
                
                else:
                    with col2:
                        produtos_selecionado2 = st.multiselect(
                            "Produto 2:",
                            options=nomes_produtos,
                            #default='',
                            key="select_produto_oportunidade2",
                            placeholder='Selecione aqui...'
                        )
                with col3:
                    produtos_selecionado3 = st.multiselect(
                        "Produto 3:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade3",
                        placeholder='Selecione aqui...'
                    )
                with col4:
                    produtos_selecionado4 = st.multiselect(
                        "Produto 4:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade4",
                        placeholder='Selecione aqui...'
                    )
                with col5:
                    produtos_selecionado5 = st.multiselect(
                        "Produto 5:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade5",
                        placeholder='Selecione aqui...'
                    )
                
                col6, col7, col8, col9, col10 = st.columns(5)
                with col6:
                    produtos_selecionado6 = st.multiselect(
                        "Produto 6:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade6",
                        placeholder='Selecione aqui...'
                    )
                with col7:
                    produtos_selecionado7 = st.multiselect(
                        "Produto 7:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade7",
                        placeholder='Selecione aqui...'
                    )
                with col8:
                    produtos_selecionado8 = st.multiselect(
                        "Produto 8:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade8",
                        placeholder='Selecione aqui...'
                    )
                with col9:
                    produtos_selecionado9 = st.multiselect(
                        "Produto 9:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade9",
                        placeholder='Selecione aqui...'
                    )
                with col10:
                    produtos_selecionado10 = st.multiselect(
                        "Produto 10:",
                        options=nomes_produtos,
                        #default='',
                        key="select_produto_oportunidade10",
                        placeholder='Selecione aqui...'
                    )

                produtos_selecionados = [p[0] for p in [produtos_selecionado1, produtos_selecionado2, produtos_selecionado3, produtos_selecionado4, produtos_selecionado5,
                                            produtos_selecionado6, produtos_selecionado7, produtos_selecionado8, produtos_selecionado9, produtos_selecionado10] if p]
                
                negocio_selecionado['produtos'] = produtos_selecionados

                size_produtos = len(produtos_selecionados)-1
                for p in produtos_selecionados:
                    if p == 'Cenário adicional de simulação':
                        lista_escopo.append(['Contempla 1 (uma) simulação computacional térmica e lumínica natural adicional'])
                        size_produtos-=1

                for i in range(size_produtos):
                    lista_escopo.append([])

                if len(produtos_selecionados) > 0:
                    #st.write(negocio_selecionado)

                    # Itera sobre a lista de produtos selecionados, adicionando o objeto correspondente para cada ocorrência
                    produtos_selecionados_obj = produtos_selecionados

                    total = preco_modelagem + preco_servico

                    # Tenta recuperar o dicionário de serviços adicionais do documento de produto
                    servicos_adicionais = documento_produto.get("servicos_adicionais", {})
                    # Caso não seja um dicionário, tenta converter
                    if not isinstance(servicos_adicionais, dict):
                        try:
                            servicos_adicionais = ast.literal_eval(servicos_adicionais)
                        except Exception as e:
                            servicos_adicionais = {}

                    # Itera sobre os produtos selecionados e soma os preços dos serviços adicionais, se existentes
                    for produto in produtos_selecionados:
                        # Verifica se o produto selecionado está no dicionário e se o valor é numérico
                        valor = servicos_adicionais.get(produto)
                        if valor and isinstance(valor, (int, float)):
                            total += valor
                    
                    valor_estimado_formatado = format_currency(total)
                    default_desconto = negocio_selecionado.get("desconto_aplicado")
                    desconto_aprovado_bd = negocio_selecionado.get("desconto_aprovado")
                    if default_desconto is None:
                        default_desconto = 0.0
                    if desconto_aprovado_bd is not None and desconto_aprovado_bd > 20:
                        desconto = st.number_input("Desconto (%)", 0.0, 100.0, value=desconto_aprovado_bd, format="%.8f")
                    else:
                        desconto = st.number_input("Desconto (%)", 0.0, 100.0, value=default_desconto, format="%.8f")
                    desconto_total = total*(desconto/100)
                    valor_negocio = total - desconto_total
                    valor_negocio_formatado = format_currency(valor_negocio)
                    col1, col2 = st.columns(2)
                    with col1:  st.warning(f"**Preço total dos produtos selecionados:** {valor_estimado_formatado}")
                    with col2:  st.warning(f"**Preço total com descontos:** {valor_negocio_formatado}")
                    #**Preço com o desconto aplicado:** {valor_negocio_formatado}")
                    condicoes = calcular_parcelas_e_saldo(float(valor_negocio), 6000)
                    
                    # Valor salvo no banco para a condição de pagamento (se existir)
                    default_condicao = negocio_selecionado.get('condicoes_pagamento', None)

                    # Se existir e estiver na lista de opções, encontra o índice correspondente;
                    # caso contrário, usa o índice 0 (primeira opção da lista)
                    if default_condicao and default_condicao in condicoes:
                        default_index = condicoes.index(default_condicao)
                    else:
                        default_index = 0

                    condicao_pagamento = st.selectbox('Condições de pagamento:', condicoes, index=default_index)

                    if float(valor_negocio) > 35000:
                        prazos = ['60 dias úteis após o recebimento da documentação completa.',
                                '30 dias úteis após o recebimento da documentação completa.',
                                '20 dias úteis após o recebimento da documentação completa.']
                    
                    else: prazos = ['60 dias úteis após o recebimento da documentação completa.',
                                '30 dias úteis após o recebimento da documentação completa.',
                                '20 dias úteis após o recebimento da documentação completa.',
                                '15 dias úteis após o recebimento da documentação completa.',
                                '10 dias úteis após o recebimento da documentação completa.']

                    # 1. Prazo de execução
                    default_prazo = negocio_selecionado.get('prazo_execucao', None)
                    if default_prazo and default_prazo in prazos:
                        prazo_index = prazos.index(default_prazo)
                    else:
                        prazo_index = 0
                    prazos.sort()
                    prazo = st.selectbox("Prazo de execução:", prazos, index=prazo_index)

                    # 2. Seleção dos Contatos da Empresa (pode ser múltiplo)
                    contatos = list(
                        collection_contatos.find(
                            {"empresa_id": empresa_id},
                            {"_id": 0, "nome": 1, "email": 1, "sobrenome": 1}  # Incluindo sobrenome para contato principal
                        )
                    )
                    if contatos:
                        opcoes_contatos = [f"{c.get('email', 'Sem email')}" for c in contatos]
                        nomes_contatos = [f"{c.get('nome', 'Sem nome')} {c.get('sobrenome', '')}" for c in contatos]

                        # Valor padrão para contatos selecionados (campo 'contatos_selecionados' da oportunidade)
                        default_contatos = negocio_selecionado.get("contatos_selecionados", [])
                        # Filtra os defaults para que estejam entre as opções disponíveis
                        default_contatos = [d for d in default_contatos if d in opcoes_contatos]

                        selected_contatos = st.multiselect(
                            "Selecione os contatos da empresa que receberão o orçamento:",
                            opcoes_contatos,
                            key="orcamento_contatos",
                            placeholder='Selecione os contatos aqui...',
                            default=default_contatos
                        )

                        # Valor padrão para o contato principal (campo 'contato_principal' da oportunidade)
                        default_contato_principal = negocio_selecionado.get("contato_principal", None)
                        if default_contato_principal and default_contato_principal in nomes_contatos:
                            contato_index = nomes_contatos.index(default_contato_principal)
                        else:
                            contato_index = 0
                        nome_contato_principal = st.selectbox(
                            "Selecione o contato principal (A/C):",
                            nomes_contatos,
                            key="orcamento_contato_principal",
                            index=contato_index
                        )
                    else:
                        st.error("Nenhum contato encontrado para essa empresa.")
                        selected_contatos = []

                    st.write('-----')
                    st.header("📄 Geração e envio de orçamentos")
                    st.info("A geração do orçamento pode levar alguns segundos, aguarde a conclusão de cada etapa, tanto para geração do PDF quanto o upload no OneDrive.")
                    st.write('----')
                    st.subheader("📄 Geração de um orçamento convencional")
                    if st.button("Gerar o orçamento"):
                        if desconto <= negocio_selecionado['desconto_aprovado']:  
                            inicio = time.time()
                            pdf_out_path = gro.generate_proposal_pdf2(empresa_nome, negocio_id, selected_negocio, produtos_selecionados_obj, valor_negocio, desconto_total, condicao_pagamento, prazo, nome_contato_principal, lista_escopo)
                            if pdf_out_path:
                                versao_proposta = gro.upload_onedrive2(pdf_out_path)
                                #st.write(versao_proposta)
                                path_proposta_envio = pdf_out_path.replace('.pdf',f'_v0{versao_proposta}.pdf')
                                fim = time.time()
                                st.info(f"Tempo da operação: {round(fim-inicio,2)}s")
                                novo_nome_arquivo = os.path.basename(path_proposta_envio)

                                # Atualiza o documento da oportunidade com as novas informações
                                collection_oportunidades.update_one(
                                    {"empresa_id": empresa_id, "nome_oportunidade": selected_negocio},
                                    {"$set": {
                                        "produtos": produtos_selecionados,
                                        "valor_orcamento": valor_negocio_formatado,
                                        "condicoes_pagamento": condicao_pagamento,
                                        "prazo_execucao": prazo,
                                        "contato_principal": nome_contato_principal,
                                        "contatos_selecionados": selected_contatos,
                                        "categoria": categoria_orcamento,
                                        "tipo": tipo_empreendimento,
                                        "tamanho": tamanho_empreendimento,
                                        "desconto_aplicado": float(desconto)
                                    }}
                                )
                            else: st.error('Erro na geração do orçamento, fale com o seu gestor.')
                        
                        else:
                            st.error('⚠️ Desconto ainda não aprovado pelo gestor. Solicite abaixo aprovação do desconto ou aguarde a decisão antes de gerar a proposta.')
                    
                    st.write('-----')
                    st.subheader("📝 Geração de um orçamento com aprovação de desconto adicional")
                    with st.expander('Solicitação de desconto adicional ao gestor', expanded=False):
                        st.error('⚠️ Descontos acima de 20% devem ser aprovados pelo gestor responsável.') 
                        
                        if negocio_selecionado['aprovacao_gestor']: 
                            st.markdown(f"🟩 Desconto aprovado pelo gestor de até {negocio_selecionado['desconto_aprovado']}%.")
                            justificativa = st.text_area("Justificativa para solicitação de novo desconto adicional:")
                            senha = st.text_input("Digite sua senha para solicitar o desconto: *", type="password")
                            if st.button(f'Solicitar novo desconto de {desconto}%'):
                                receivers = ['fabricio@hygge.eco.br', email]
                                #receivers = [email]
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'Solicitação de desconto adicional - {selected_negocio}'
                                
                                body = f"""<p>Vendedor: {negocio_selecionado['proprietario']}</p>
                                            <p>Empresa: {negocio_selecionado['cliente']}</p>
                                            <p>Projeto: {negocio_selecionado['nome_oportunidade']}</p>
                                            <p>Produto(s): {produtos_selecionados}</p>
                                            <p>Desconto solicitado: {desconto}%</p>
                                            <p>Valor do orçamento inicial: {valor_estimado_formatado}</p>
                                            <p>Novo valor do orçamento: {valor_negocio_formatado}</p>
                                            <p>Justificativa: {justificativa}</p>
                                            <p>Acesse a plataforma integrada para aprovar ou reprovar a solicitação.</p>"""

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")

                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"desconto_solicitado": float(desconto)}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"solicitacao_desconto": True}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"aprovacao_gestor": False}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"condicoes_pagamento": condicao_pagamento}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"prazo_execucao": prazo}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contato_principal": nome_contato_principal}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contatos_selecionados": selected_contatos}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"produtos": produtos_selecionados}})
                                st.success('Solicitação de desconto enviada com sucesso.')
                                st.rerun()

                        elif negocio_selecionado['solicitacao_desconto']: 
                            st.markdown(f"🟨 Em análise pelo gestor a solicitação de um desconto de {negocio_selecionado['desconto_solicitado']}%.")

                        elif not negocio_selecionado['solicitacao_desconto']:
                            st.markdown('🟦 Sem solicitação de desconto.')
                            justificativa = st.text_area("Justificativa para solicitação de desconto adicional:")
                            senha = st.text_input("Digite sua senha para solicitar o desconto: *", type="password")
                            if st.button(f'Solicitar desconto de {desconto}%'):
                            
                                receivers = ['fabricio@hygge.eco.br', st.experimental_user.email]
                                #receivers = [email]
                                
                                message = MIMEMultipart()
                                message["From"] = st.experimental_user.email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'Solicitação de desconto adicional - {selected_negocio}'
                                
                                body = f"""<p>Vendedor: {negocio_selecionado['proprietario']}</p>
                                            <p>Empresa: {negocio_selecionado['cliente']}</p>
                                            <p>Projeto: {negocio_selecionado['nome_oportunidade']}</p>
                                            <p>Produto(s): {produtos_selecionados}</p>
                                            <p>Desconto solicitado: {desconto}%</p>
                                            <p>Valor do orçamento inicial: {valor_estimado_formatado}</p>
                                            <p>Novo valor do orçamento: {valor_negocio_formatado}</p>
                                            <p>Justificativa: {justificativa}</p>
                                            <p>Acesse a plataforma integrada para aprovar ou reprovar a solicitação.</p>"""

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")
                                
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"desconto_solicitado": float(desconto)}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"solicitacao_desconto": True}})    
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"aprovacao_gestor": False}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"condicoes_pagamento": condicao_pagamento}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"prazo_execucao": prazo}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contato_principal": nome_contato_principal}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"contatos_selecionados": selected_contatos}})
                                collection_oportunidades.update_one({"cliente": empresa_nome, "nome_oportunidade": selected_negocio}, {"$set": {"produtos": produtos_selecionados}})
                                st.success('Solicitação de desconto enviada com sucesso.')
                                st.rerun()

                        elif not negocio_selecionado['aprovacao_gestor']: 
                            st.markdown('🟥 Desconto não aprovado.')
                    
                    if st.button("Gerar o orçamento com o desconto adicional aprovado"):
                        if desconto <= negocio_selecionado['desconto_aprovado']:  
                            inicio = time.time()
                            pdf_out_path = gro.generate_proposal_pdf2(empresa_nome, negocio_id, selected_negocio, produtos_selecionados_obj, valor_negocio, desconto_total, condicao_pagamento, prazo, nome_contato_principal, lista_escopo)
                            if pdf_out_path:
                                versao_proposta = gro.upload_onedrive2(pdf_out_path)
                                #   versao_proposta)
                                path_proposta_envio = pdf_out_path.replace('.pdf',f'_v0{versao_proposta}.pdf')
                                fim = time.time()
                                st.info(f"Tempo da operação: {round(fim-inicio,2)}s")
                                novo_nome_arquivo = os.path.basename(path_proposta_envio)

                                # Atualiza o documento da oportunidade com as novas informações
                                collection_oportunidades.update_one(
                                    {"cliente": empresa_nome, "nome_oportunidade": selected_negocio},
                                    {"$set": {
                                        "produtos": produtos_selecionados,
                                        "valor_orcamento": valor_negocio_formatado,
                                        "condicoes_pagamento": condicao_pagamento,
                                        "prazo_execucao": prazo,
                                        "contato_principal": nome_contato_principal,
                                        "contatos_selecionados": selected_contatos,
                                        "categoria": categoria_orcamento,
                                        "tipo": tipo_empreendimento,
                                        "tamanho": tamanho_empreendimento
                                    }}
                                )
                            else: st.error('Erro na geração do orçamento.')
                        
                        else:
                            st.error('⚠️ Desconto ainda não aprovado pelo gestor. Solicite abaixo aprovação do desconto ou aguarde a decisão antes de gerar a proposta.')

                    st.write('-----')
                    st.subheader("📨 Envio da proposta para o cliente")
                    senha = st.text_input("Digite sua senha para enviar o orçamento: *", type="password")

                    if st.button('Enviar orçamento para o cliente'):
                        #receivers = selected_contatos + [email,'fabricio@hygge.eco.br','alexandre@hygge.eco.br','rodrigo@hygge.eco.br','paula@hygge.eco.br']
                        receivers = [email]
                        message = MIMEMultipart()
                        message["From"] = email
                        message["To"] = ", ".join(receivers)
                        message["Subject"] = f'Proposta Técnico-Comercial Hygge - {selected_negocio}'

                        # Corpo do email original
                        body = f"""<p>Olá {nome_contato_principal},</p>
                        <p>Conforme solicitado, segue em anexo a proposta técnico comercial da Hygge para o empreendimento {selected_negocio}.</p>
                        <p>Estamos à disposição para quaisquer dúvidas ou esclarecimentos.</p>
                        <p>Atenciosamente,</p>"""
                        
                        if email == 'comercial2@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/thiago-lecheta.html"
                        elif email == 'matheus@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-duarte.html"
                        elif email == 'fabricio@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fabricio-lucchesi.html"
                        elif email == 'alexandre@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"
                        #elif email == 'comercial6@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/maria-eduarda-ferreira.html"  
                        elif email == 'comercial5@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-rodrigues.html"  
                        elif email == 'comercial4@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alceu-junior.html"   
                        elif email == 'comercial3@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/victor-oliveira.html"
                        #elif email == 'comercial1@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fernando-tohme.html"
                        elif email == 'rodrigo@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"
                        elif email == 'admin@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"

                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        response = requests.get(url, headers=headers)
                        html_signature = response.text

                        # Concatena o corpo do email com a assinatura HTML
                        full_body = body + html_signature

                        # Anexa o corpo do email completo no formato HTML
                        message.attach(MIMEText(full_body, "html"))

                        path_proposta_envio = gro.get_versao(f"{selected_negocio}_{negocio_id}")
                        if path_proposta_envio:
                            novo_nome_arquivo = os.path.basename(path_proposta_envio)
                            
                            # Attach the PDF file
                            with open(path_proposta_envio, 'rb') as attachment:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(attachment.read())
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', 'attachment', filename=novo_nome_arquivo)
                                message.attach(part)

                            # Sending the email
                            try:
                                server = smtplib.SMTP('smtp.office365.com', 587)
                                server.starttls()
                                server.login(email, senha)
                                server.sendmail(email, receivers, message.as_string())
                                server.quit()
                                st.success(f'Etapa 1 de 1 - Email enviado com sucesso com a proposta {novo_nome_arquivo}!')
                            except Exception as e:
                                st.error(f"Falha no envio do email: {e}")
                        
                        else: st.error("Arquivo não localizado na pasta '11. Orçamentos', gere um orçamento para enviá-lo ao cliente.")

                    st.write('-----')
                    #aceite de propostas
                    st.header("📄 Geração e envio de aceite de proposta")
                    st.info("A geração do aceite de proposta pode levar alguns segundos, aguarde a conclusão de cada etapa, tanto para o envio dos e-mails quanto a criação das pastass no OneDrive.")
                    st.write('----')
                    st.subheader("🤝 Informações relevantes para o técnico/financeiro")
                    st.info('Preencha todos os campos com "*" para habilitar a etapa de criação de pastas e envio de email.')

                    col1, col2, col3 = st.columns(3)
                    with col1: tipo_contrato_answ = st.selectbox('Contrato ou somente proposta?*',options=['-','Contrato', 'Somente proposta'])
                    with col2: resp_contrato_answ = st.selectbox('Quem é responsável pelo contrato?*',options=['-','HYGGE','Contratante','Não definido'])
                    with col3: nro_parcelas_answ = st.selectbox('Número de parcelas?*',options=['-','1x','2x','3x','4x','5x','6x','Não definido'])
    
                    col1, col2, col3 = st.columns(3)
                    with col1: parceria_answ = st.selectbox('Tem parceria?*', options=['-','Sim, Scala','Não'])
                    with col2: entrada_answ = st.selectbox('Haverá o pagamento de entrada?*',options=['-','Sim','Não'])
                    with col3: parcelas_vinc_ent_answ = st.selectbox('Demais parcelas vinculadas às entregas?*',options=['-','Sim','Não'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1: comentarios_answ = st.text_area('Comentários relevantes (condições acordadas):*')
                    with col2: contato_financeiro_answ = st.text_area('Contato financeiro (nome e email) *')
                    with col3: contatos_answ = st.text_area('Contatos adicionais')

                    st.write('---')

                    if tipo_contrato_answ != '-' and nro_parcelas_answ != '-' and parcelas_vinc_ent_answ != '-' and resp_contrato_answ != '-' and entrada_answ != '-' and len(parceria_answ) > 0 and len(comentarios_answ) > 0 and len(contato_financeiro_answ) > 0: 
                        
                        st.subheader("📨 Envio do email de aceite para o cliente")
                        
                        st.error(f"**ALERTA:** Ao clicar no botão abaixo o e-mail de aceite de proposta será enviado para o(s) cliente(s) (**{selected_contatos}**) e a pasta será gerada no servidor, você tem certeza?",icon='🚨')
                        senha = st.text_input("Digite a senha do seu e-mail: *", type="password", key="senha_email")
                        if st.button("Criar pasta no servidor e enviar email de aceite para o cliente"):
                            with st.spinner('Espere a conclusão da operação...'):

                                # Atualiza o documento da oportunidade com as novas informações
                                collection_oportunidades.update_one(
                                    {"cliente": empresa_nome, "nome_oportunidade": selected_negocio},
                                    {"$set": {
                                        "contrato_proposta": tipo_contrato_answ,
                                        "responsavel_contrato": resp_contrato_answ,
                                        "nro_parcelas": nro_parcelas_answ,
                                        "parceria": parceria_answ,
                                        "entrada": entrada_answ,
                                        "parcelas_vinc_ent": parcelas_vinc_ent_answ,
                                        "contato_financeiro": contato_financeiro_answ,
                                        "comentarios_relevantes": comentarios_answ,
                                        "contatos_adicionais": contatos_answ,
                                        "estagio": "Fechado"
                                    }}
                                )

                                # Configuração do email
                                receivers = ['paula@hygge.eco.br','financeiro@hygge.eco.br', 'rodrigo@hygge.eco.br','alexandre@hygge.eco.br','fabricio@hygge.eco.br', email]
                                #receivers = ['rodrigo@hygge.eco.br', 'alexandre@hygge.eco.br']
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'[Hygge & {empresa_nome}] Informações adicionais - {selected_negocio} (EMAIL INTERNO)'

                                # Corpo do email original
                                body = f"""<p>Olá a todos, espero que estejam bem.<br></p>
                                <p>A respeito do fechamento {selected_negocio} (em anexo):<br></p>
                                <p>Contrato ou somente proposta? {tipo_contrato_answ}<br></p>
                                <p>Quem é responsável pelo contrato? {resp_contrato_answ}<br></p>
                                <p>Nro. de parcelas: {nro_parcelas_answ}<br></p>
                                <p>Parceria? {parceria_answ}<br></p>
                                <p>Entrada? {entrada_answ}<br></p>
                                <p>Demais parcelas vinculadas à entrega? {parcelas_vinc_ent_answ}<br></p>
                                <p>Valor do orçamento: {valor_negocio_formatado}<br></p>
                                <p>Condições de pagamento: {condicao_pagamento}<br></p>
                                <p>Prazo informado para entrega: {prazo}<br></p>
                                <p>Comentários relevantes: {comentarios_answ}<br></p>
                                <p>Contato financeiro: {contato_financeiro_answ}<br></p>
                                <p>Contatos adicionais: {contatos_answ}<br></p>
                                
                                <br><p>Detalhes do fechamento:<br></p>
                                <p>Produtos: {produtos_selecionados}<br></p>
                                <p>Categoria: {categoria_orcamento}<br></p>
                                <p>Tipo de empreendimento: {tipo_empreendimento}<br></p>
                                <p>Tamanho: {tamanho_empreendimento}<br></p>

                                <p>Atenciosamente,</p>"""

                                if email == 'comercial2@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/thiago-lecheta.html"
                                elif email == 'matheus@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-duarte.html"
                                elif email == 'fabricio@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fabricio-lucchesi.html"
                                elif email == 'alexandre@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"
                                elif email == 'comercial8@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/renan-bertolini-rozov.html"
                                elif email == 'comercial6@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/maria-eduarda-ferreira.html"  
                                elif email == 'comercial5@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-rodrigues.html"  
                                elif email == 'comercial4@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alceu-junior.html"   
                                elif email == 'comercial3@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/victor-oliveira.html"
                                elif email == 'comercial1@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fernando-tohme.html"
                                elif email == 'rodrigo@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"
                                elif email == 'admin@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"

                                    
                                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                                response = requests.get(url, headers=headers)
                                html_signature = response.text

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body + html_signature

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                path_proposta_envio = gro.get_versao(f"{selected_negocio}_{negocio_id}")
                
                                if path_proposta_envio:
                                    novo_nome_arquivo = os.path.basename(path_proposta_envio)
                                else:
                                    st.error("Erro ao encontrar o arquivo da proposta.")
                                    return

                                # Attach the PDF file
                                with open(path_proposta_envio, 'rb') as attachment:
                                    part = MIMEBase('application', 'octet-stream')
                                    part.set_payload(attachment.read())
                                    encoders.encode_base64(part)
                                    part.add_header('Content-Disposition', 'attachment', filename=novo_nome_arquivo)
                                    message.attach(part)

                                    # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                    st.success("Etapa 1 de 3 - Email 1 enviado com sucesso para a equipe interna!")

                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")

                                # Configuração do email
                                receivers = selected_contatos + ['fabricio@hygge.eco.br','alexandre@hygge.eco.br','rodrigo@hygge.eco.br','paula@hygge.eco.br','financeiro@hygge.eco.br', email]
                                #receivers = ['rodrigo@hygge.eco.br', 'alexandre@hygge.eco.br']
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'[Hygge & {empresa_nome}] Proposta Técnico-Comercial ACEITA - {selected_negocio}'

                                # Corpo do email original
                                body = f"""<p>Olá a todos, espero que estejam bem.<br></p>
                                <p>Conforme tratativas entre {nome_contato_principal} e {user}, recebemos o aceite da proposta {selected_negocio} (em anexo).<br></p>
                                <p>Portanto, é com grande satisfação que se inicia nossa parceria para o empreendimento {selected_negocio}!<br></p>
                                <p>Entro em contato para adicionar a Vanessa Godoi do setor financeiro da Hygge (financeiro@hygge.eco.br), a qual entrará em contato para dar continuidade às tratativas referentes à contratos e pagamentos.<br></p>
                                <p>Também incluo a Paula Alano (paula@hygge.eco.br), sócia e coordenadora de projetos, que liderará a equipe técnica da Hygge e será a sua ponte de comunicação para assuntos técnicos.
                                A Paula entrará em contato solicitando as informações necessárias para darmos início ao processo da Análise Hygge.<br></p>
                                <p>Agradecemos a confiança em nosso trabalho e destaco nosso comprometimento total para que nossa parceria seja bem-sucedida.<br></p>
                                <p>Atenciosamente,</p>"""

                                if email == 'comercial2@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/thiago-lecheta.html"
                                elif email == 'matheus@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-duarte.html"
                                elif email == 'fabricio@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fabricio-lucchesi.html"
                                elif email == 'alexandre@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"
                                elif email == 'comercial8@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/renan-bertolini-rozov.html"
                                elif email == 'comercial6@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/maria-eduarda-ferreira.html"  
                                elif email == 'comercial5@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-rodrigues.html"  
                                elif email == 'comercial4@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alceu-junior.html"   
                                elif email == 'comercial3@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/victor-oliveira.html"
                                elif email == 'comercial1@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fernando-tohme.html"
                                elif email == 'rodrigo@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"
                                elif email == 'admin@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"

                                    
                                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                                response = requests.get(url, headers=headers)
                                html_signature = response.text

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body + html_signature

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                path_proposta_envio = gro.get_versao(f"{selected_negocio}_{negocio_id}")
                
                                if path_proposta_envio:
                                    novo_nome_arquivo = os.path.basename(path_proposta_envio)
                                else:
                                    st.error("Erro ao encontrar o arquivo da proposta.")
                                    return

                                # Attach the PDF file
                                with open(path_proposta_envio, 'rb') as attachment:
                                    part = MIMEBase('application', 'octet-stream')
                                    part.set_payload(attachment.read())
                                    encoders.encode_base64(part)
                                    part.add_header('Content-Disposition', 'attachment', filename=novo_nome_arquivo)
                                    message.attach(part)

                                    # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                    st.success("Etapa 2 de 3 - Email 2 enviado com sucesso para a equipe interna e para o cliente!")
                                    for i in range(10):
                                        st.balloons()
                                        time.sleep(1)
                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")
                                
                                gro.upload_to_3projetos_v02(f'{selected_negocio}'.upper())
                                
                                st.success("Etapa 3 de 3 - Parabéns pela venda! Informações atualizadas no servidor e pastas criadas.")
                                for i in range(10):
                                    st.balloons()
                                    time.sleep(1)

                        st.write('------')

                        st.subheader("📨 Envio do email de aceite interno")

                        st.error(f"**ALERTA:** Ao clicar no botão abaixo a pasta será gerada no servidor **e um email de notificação será enviado para a equipe interna da Hygge, sem o envio do email para o cliente**, você tem certeza?",icon='🚨')
                        if st.button("Criar pasta no servidor e enviar email interno"):#, #disabled=st.session_state['button_disabled']):
                            with st.spinner('Espere a conclusão da operação...'):
                                
                                # Atualiza o documento da oportunidade com as novas informações
                                collection_oportunidades.update_one(
                                    {"cliente": empresa_nome, "nome_oportunidade": selected_negocio},
                                    {"$set": {
                                        "contrato_proposta": tipo_contrato_answ,
                                        "responsavel_contrato": resp_contrato_answ,
                                        "nro_parcelas": nro_parcelas_answ,
                                        "parceria": parceria_answ,
                                        "entrada": entrada_answ,
                                        "parcelas_vinc_ent": parcelas_vinc_ent_answ,
                                        "contato_financeiro": contato_financeiro_answ,
                                        "comentarios_relevantes": comentarios_answ,
                                        "contatos_adicionais": contatos_answ,
                                        "estagio": "Fechado"
                                    }}
                                )
                                
                                # st.session_state['button_disabled'] = True
                                # Configuração do email
                                receivers = ['paula@hygge.eco.br','financeiro@hygge.eco.br', 'rodrigo@hygge.eco.br','alexandre@hygge.eco.br','fabricio@hygge.eco.br', email]
                                #receivers = ['rodrigo@hygge.eco.br']
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'[Hygge & {empresa_nome}] Informações adicionais - {selected_negocio} (EMAIL INTERNO)'

                                # Corpo do email original
                                body = f"""<p>Olá a todos, espero que estejam bem.<br></p>
                                <p>A respeito do fechamento {selected_negocio} (em anexo):<br></p>
                                <p>Contrato ou somente proposta? {tipo_contrato_answ}<br></p>
                                <p>Quem é responsável pelo contrato? {resp_contrato_answ}<br></p>
                                <p>Nro. de parcelas: {nro_parcelas_answ}<br></p>
                                <p>Parceria? {parceria_answ}<br></p>
                                <p>Entrada? {entrada_answ}<br></p>
                                <p>Demais parcelas vinculadas à entrega? {parcelas_vinc_ent_answ}<br></p>
                                <p>Valor do orçamento: {valor_negocio_formatado}<br></p>
                                <p>Condições de pagamento: {condicao_pagamento}<br></p>
                                <p>Prazo informado para entrega: {prazo}<br></p>
                                <p>Comentários relevantes: {comentarios_answ}<br></p>
                                <p>Contato financeiro: {contato_financeiro_answ}<br></p>
                                <p>Contatos adicionais: {contatos_answ}<br></p>
                                
                                <br><p>Detalhes do fechamento:<br></p>
                                <p>Produtos: {produtos_selecionados}<br></p>
                                <p>Categoria: {categoria_orcamento}<br></p>
                                <p>Tipo de empreendimento: {tipo_empreendimento}<br></p>
                                <p>Tamanho: {tamanho_empreendimento}<br></p>

                                <p>Atenciosamente,</p>"""

                                if email == 'comercial2@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/thiago-lecheta.html"
                                elif email == 'matheus@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-duarte.html"
                                elif email == 'fabricio@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fabricio-lucchesi.html"
                                elif email == 'alexandre@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"
                                elif email == 'comercial8@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/renan-bertolini-rozov.html"
                                elif email == 'comercial6@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/maria-eduarda-ferreira.html"  
                                elif email == 'comercial5@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-rodrigues.html"  
                                elif email == 'comercial4@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alceu-junior.html"   
                                elif email == 'comercial3@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/victor-oliveira.html"
                                elif email == 'comercial1@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fernando-tohme.html"
                                elif email == 'rodrigo@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"
                                elif email == 'admin@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"

                                    
                                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                                response = requests.get(url, headers=headers)
                                html_signature = response.text

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body + html_signature

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                st.write(selected_negocio, negocio_id)
                                path_proposta_envio = gro.get_versao(f"{selected_negocio}_{negocio_id}")
                                st.write(path_proposta_envio)
                                
                                if path_proposta_envio:
                                    novo_nome_arquivo = os.path.basename(path_proposta_envio)
                                else:
                                    st.error("Erro ao encontrar o arquivo da proposta.")
                                    return

                                # Attach the PDF file
                                with open(path_proposta_envio, 'rb') as attachment:
                                    part = MIMEBase('application', 'octet-stream')
                                    part.set_payload(attachment.read())
                                    encoders.encode_base64(part)
                                    part.add_header('Content-Disposition', 'attachment', filename=novo_nome_arquivo)
                                    message.attach(part)

                                    # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                    st.success("Etapa 1 de 3 - Email 1 enviado com sucesso para a equipe interna!")

                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")


                                # Configuração do email
                                receivers = ['fabricio@hygge.eco.br','admin@hygge.eco.br','rodrigo@hygge.eco.br','paula@hygge.eco.br','financeiro@hygge.eco.br', email]
                                message = MIMEMultipart()
                                message["From"] = email
                                message["To"] = ", ".join(receivers)
                                message["Subject"] = f'[Hygge & {empresa_nome}] Proposta Técnico-Comercial ACEITA - {selected_negocio} (EMAIL INTERNO)'

                                # Corpo do email original
                                body = f"""<p>Olá a todos, espero que estejam bem.<br></p>
                                <p>Conforme tratativas entre {nome_contato_principal} e {user}, recebemos o aceite da proposta {selected_negocio} (em anexo).<br></p>
                                <p>Atenciosamente,</p>"""

                                if email == 'comercial2@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/thiago-lecheta.html"
                                elif email == 'matheus@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-duarte.html"
                                elif email == 'fabricio@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fabricio-lucchesi.html"
                                elif email == 'alexandre@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"
                                elif email == 'comercial8@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/renan-bertolini-rozov.html"
                                elif email == 'comercial6@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/maria-eduarda-ferreira.html"  
                                elif email == 'comercial5@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/matheus-rodrigues.html"  
                                elif email == 'comercial4@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alceu-junior.html"   
                                elif email == 'comercial3@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/victor-oliveira.html"
                                elif email == 'comercial1@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/fernando-tohme.html"
                                elif email == 'rodrigo@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/rodrigo-leitzke.html"
                                elif email == 'admin@hygge.eco.br': url = "https://www.hygge.eco.br/assinatura-email/2024/alexandre-castagini.html"

                                    
                                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                                response = requests.get(url, headers=headers)
                                html_signature = response.text

                                # Concatena o corpo do email com a assinatura HTML
                                full_body = body + html_signature

                                # Anexa o corpo do email completo no formato HTML
                                message.attach(MIMEText(full_body, "html"))

                                # Attach the PDF file
                                with open(path_proposta_envio, 'rb') as attachment:
                                    part = MIMEBase('application', 'octet-stream')
                                    part.set_payload(attachment.read())
                                    encoders.encode_base64(part)
                                    part.add_header('Content-Disposition', 'attachment', filename=novo_nome_arquivo)
                                    message.attach(part)

                                    # Sending the email
                                try:
                                    server = smtplib.SMTP('smtp.office365.com', 587)
                                    server.starttls()
                                    server.login(email, senha)
                                    server.sendmail(email, receivers, message.as_string())
                                    server.quit()
                                    st.success("Etapa 2 de 3 - Email 2 enviado com sucesso para a equipe interna!")
                                    for i in range(10):
                                        st.balloons()
                                        time.sleep(1)

                                except Exception as e:
                                    st.error(f"Falha no envio do email: {e}")
                                
                                gro.upload_to_3projetos_v02(f'{selected_negocio}'.upper())
                                st.success("Etapa 3 de 3 - Parabéns pela venda! Informações atualizadas no servidor e pastas criadas.")
                                for i in range(10):
                                    st.balloons()
                                    time.sleep(1)    

            
    