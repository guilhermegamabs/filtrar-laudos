from pymongo import MongoClient
from datetime import datetime

# --- CONFIGURAÇÕES DO MONGODB (SUBSTITUA AQUI!) ---
# É CRUCIAL que você substitua estas variáveis pelos dados que seu colega forneceu.
MONGO_URI = "mongodb+srv://guilherme_db_user:T8fkkkVcT7K7YMv@cluster0.otygn9m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
NOME_BANCO = "AIHO"
NOME_COLECAO = "achados_oportunisticos_aorta"

def salvar_no_mongodb(laudo_id: str, texto_laudo_bruto: str, achados_filtrados: list):
    """
    Conecta ao MongoDB e insere um documento contendo os achados estruturados.

    Args:
        laudo_id (str): ID único para o laudo (ex: TC_2025_001).
        texto_laudo_bruto (str): O texto completo do laudo (para referência).
        achados_filtrados (list): A lista de dicionários retornada pela sua função de filtro.
    """
    if not achados_filtrados:
        status_ao = False
    else:
        status_ao = True

    # Cria o documento JSON a ser inserido no MongoDB
    documento = {
        "_id": laudo_id,  # Use um ID único para o seu documento
        "data_insercao": datetime.now(),
        "ao_status_aorta": status_ao,  # Flag rápida para saber se achados foram detectados
        "achados_aorta": achados_filtrados,
        "texto_laudo_bruto": texto_laudo_bruto
    }

    try:
        # 1. Conexão ao MongoDB
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # O comando abaixo verifica se o cliente consegue se conectar.
        # Se a conexão falhar, ele levanta uma exceção (timeout).
        cliente.admin.command('ping') 
        
        db = cliente[NOME_BANCO]
        colecao = db[NOME_COLECAO]
        
        # 2. Inserção do Documento
        resultado = colecao.insert_one(documento)
        
        print("\n✅ Sucesso na inserção no MongoDB!")
        print(f"ID do Documento Inserido: {resultado.inserted_id}")
        
    except Exception as e:
        print(f"\n❌ ERRO ao conectar ou inserir no MongoDB. Verifique o URI e IP.")
        print(f"Detalhes do Erro: {e}")
    finally:
        if 'cliente' in locals():
            cliente.close()

# --- EXEMPLO DE INTEGRAÇÃO (Simulação) ---
# Você precisará integrar esta função ao seu fluxo principal (filtrar_laudos.py)

if __name__ == '__main__':
    # 1. Simulação da saída do seu filtro Python (filtrar_laudo_detalhado_conciso)
    laudo_teste_id = "TC_ABD_00123"
    texto_bruto_simulado = "TC Abdomen: Aorta abdominal com placas ateromatosas difusas..."
    
    achados_simulados = [
        {
            "estrutura": "descendente",
            "patologia": "calcificacao/aterosclerose",
            "detalhe": ["placa", "mm"]
        },
        {
            "estrutura": "iliaca",
            "patologia": "aneurisma/dilatacao",
            "detalhe": ["cm", "maior diametro"]
        }
    ]

    # 2. Chamada para salvar
    salvar_no_mongodb(
        laudo_id=laudo_teste_id,
        texto_laudo_bruto=texto_bruto_simulado,
        achados_filtrados=achados_simulados
    )