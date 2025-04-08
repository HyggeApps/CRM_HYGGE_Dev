import utils.database as db

# Para todas as tarefas crie um campo chamado 'Priopridade' e adicione o valor 'Baixa' para todas as tarefas
def adicionar_prioridade_tarefas():
    collection_tarefas = db.get_collection("tarefas")
    
    # Adiciona o campo 'Prioridade' com valor 'Baixa' para todas as tarefas
    collection_tarefas.update_many({}, {"$set": {"Prioridade": "Baixa"}})
    print("Campo 'Prioridade' adicionado com valor 'Baixa' para todas as tarefas.")

adicionar_prioridade_tarefas()