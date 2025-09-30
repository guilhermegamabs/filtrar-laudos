import re
import unicodedata
from pymongo import MongoClient
from datetime import datetime
import sys

# --- CONFIGURAÇÕES DO MONGODB (AJUSTE AQUI!) ---
# Credenciais Guilherme (Ajustadas para a conveniência do teste)
MONGO_URI = "mongodb+srv://guilherme_db_user:T8fkkkVcT7K7YMv@cluster0.otygn9m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# O nome do Banco de Dados deve ser o que seu colega configurou.
NOME_BANCO = "AIHO"  
# A Coleção será criada automaticamente se o DB existir.
NOME_COLECAO = "achados_oportunisticos_aorta"

# --- FUNÇÃO DE SALVAMENTO NO MONGODB ---
def salvar_no_mongodb(laudo_id: str, nome_arquivo_origem: str, texto_laudo_bruto: str, achados_filtrados: list):
    """
    Conecta ao MongoDB e insere um documento contendo os achados estruturados.
    """
    status_ao = bool(achados_filtrados)

    documento = {
        "_id_laudo": laudo_id, 
        "data_insercao": datetime.now(),
        "arquivo_origem": nome_arquivo_origem,
        "ao_status_aorta": status_ao, 
        "achados_aorta": achados_filtrados,
        "texto_laudo_bruto": texto_laudo_bruto
    }

    cliente = None
    try:
        # 1. Conexão
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000) 
        cliente.admin.command('ping') 
        
        db = cliente[NOME_BANCO]
        colecao = db[NOME_COLECAO]
        
        # 2. Inserção
        resultado = colecao.insert_one(documento)
        
        print(f"\n✅ Sucesso: Documento inserido no DB '{NOME_BANCO}' / Coleção '{NOME_COLECAO}'.")
        print(f"ID do Documento MongoDB: {resultado.inserted_id}")
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: Falha ao conectar ou inserir no MongoDB.")
        print(f"Detalhes do Erro: {e}")
        sys.exit(1)
        
    finally:
        if cliente:
            cliente.close()

# --- FUNÇÕES E DICIONÁRIOS DO FILTRO ---

def normalizar(texto):
    """
    Converte o texto para minúsculas e remove acentos para facilitar a busca.
    """
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto

# Vocabulário (completo com expansões)
dicionario_aorta = {
    "estrutura": [
        "aorta", "aortica", "raiz", "sinotubular", "ascendente", "arco", 
        "proximal", "medio", "distal", "descendente", "toracica", "abdominal", 
        "iliaca", "iliacas comuns", "ilíaca", "tronco celiaco", "mesenterica superior",
        "mesenterica inferior", "renais", "bifurcacao", "aortopulmonar", 
        "hiato diafragmatico", "vasos", "arteria", 
        "subclávia", "carótida", "vertebral", "femoral", "istmo", "infra-renal", 
        "supraceliaco", "parietal", "íntima", "média", "adventícia" 
    ],
    "patologia": [
        "aneurisma", "ectasia", "dilatacao", "expansao", "saco aneurismatico", "fusiforme", "sacular",
        "coarctacao", "estenose", "estreitamento", "afilamento", "hipoplasia", "reducao de calibre",
        "disseccao", "flap intimal", "falso lumen", "hematoma intramural", "ruptura da intima", "hematoma mural",
        "trombo mural", "trombose", "formacao trombotica", "coagulo", "trombo aderido",
        "calcificacao", "ateromatose", "deposito calcico", "aterosclerose", "placa", "placa ateromatosa", 
        "ateroma", "esclerose", "irregularidade parietal", "ulceracao", "espessamento parietal",
        "ruptura", "perfuracao", "extravasamento", "laceracao", "sangramento ativo", "hematoma periaortico",
        "fistula", "aorto-enterica", "aorto-bronquica", "aorto-cava",
        "dilatacao pos-estenose", "pseudoaneurisma", "endoprótese",
        "tortuosidade", "dolicoartéria", "sinal da dupla luz", "úlcera penetrante", "obliterado", 
        "stent", "graft", "by-pass"
    ],
    "detalhe": [
        "calibre", "aumentado", "dilatado", "irregular", "espessamento", "sinais de", "sugestivo de",
        "compativel com", "obstruido", "estenose", "diametro", "dimensoes", "mm", "cm", "espessura", 
        "extensao", "maior diametro", "medindo", "comprimindo", "estenosa", "grau", "critica", "significativa",
        "paredes integrais", "livre de", "pervio", "normal",
        "leve", "moderado", "acentuado", "parcial", "laminar", "excêntrico", "simétrico", 
        "variando de", "até", "totalizando", "enxerto", "prótese"
    ]
}

negacoes = ["sem", "ausencia de", "negado", "nao ha", "livre de", "nao se observa", "sem sinais de", "nao se evidenciam"]

# CORREÇÃO FINAL: estenose e coarctacao movidos para serem agrupados com aterosclerose/calcificação
PATOLOGIAS_FRACAS_ATEROSCLEROSE = [
    "placa", "ateromatose", "deposito calcico", "ateroma", "esclerose", 
    "irregularidade parietal", "espessamento parietal", 
    "estenose", "coarctacao", "estreitamento" # <--- ESTENOSE E COARCTACAO SÃO TRATADOS COMO FRACAS PARA AGRUPAMENTO
]
PATOLOGIAS_FORTES_ATEROSCLEROSE = ["calcificacao", "aterosclerose"]
PATOLOGIAS_FRACAS_DILATACAO = ["ectasia", "dilatacao", "expansao", "fusiforme", "sacular"]


def filtrar_laudo_detalhado_conciso(texto):
    texto_norm = normalizar(texto)
    achados_detectados = []
    achados_unicos_set = set()

    for estrutura in dicionario_aorta["estrutura"]:
        for patologia in dicionario_aorta["patologia"]:
            
            padrao = rf"({estrutura}.*?{patologia})|({patologia}.*?{estrutura})"
            
            for match in re.finditer(padrao, texto_norm):
                
                # 1. Definir a Janela de Contexto (50 caracteres antes, 50 depois)
                start_contexto = max(0, match.start() - 50)
                end_contexto = min(len(texto_norm), match.end() + 50)
                contexto_match = texto_norm[start_contexto: end_contexto]
                
                # 2. Verificar Negação
                negado = False
                for neg in negacoes:
                    if re.search(rf"{neg}\s+.*{patologia}", contexto_match) or \
                       re.search(rf"{patologia}\s+.*{neg}", contexto_match):
                        negado = True
                        break
                        
                if not negado:
                    
                    # 3. Lógica de Agrupamento: Define a Patologia Agrupada
                    patologia_agrupada = patologia
                    
                    encontrou_termo_aterosclerose = any(
                        termo in contexto_match for termo in PATOLOGIAS_FORTES_ATEROSCLEROSE + PATOLOGIAS_FRACAS_ATEROSCLEROSE
                    )
                    
                    # AGRUPAMENTO 1: Aterosclerose/Calcificação/Estenose
                    if (patologia in PATOLOGIAS_FORTES_ATEROSCLEROSE or patologia in PATOLOGIAS_FRACAS_ATEROSCLEROSE) and encontrou_termo_aterosclerose:
                        patologia_agrupada = "calcificacao/aterosclerose"
                    
                    # AGRUPAMENTO 2: Aneurisma/Dilatação
                    elif patologia in PATOLOGIAS_FRACAS_DILATACAO or patologia == "aneurisma":
                        patologia_agrupada = "aneurisma/dilatacao"
                        
                    
                    achado_tuple = (estrutura, patologia_agrupada)
                    
                    if achado_tuple not in achados_unicos_set:
                        
                        # 4. Busca por detalhes no contexto
                        detalhes_encontrados = [det for det in dicionario_aorta["detalhe"] if det in contexto_match]
                        
                        achados_detectados.append({
                            "estrutura": estrutura,
                            "patologia": patologia_agrupada,
                            "detalhe": detalhes_encontrados if detalhes_encontrados else None
                        })
                        achados_unicos_set.add(achado_tuple)

    return achados_detectados

# --- FLUXO PRINCIPAL DE EXECUÇÃO ---

if __name__ == "__main__":
    
    # 1. Dados de Teste (Texto Embutido)
    ID_LAUDO_TESTE = "LAUDO_MANUAL_001_AOS"
    TEXTO_LAUDO_BRUTO = """
    TOMOGRAFIA COMPUTADORIZADA DE TÓRAX
    INDICAÇÃO: Avaliação de tosse crônica.
    
    ANÁLISE VASCULAR: Aorta torácica descendente e ascendente sem sinais de dissecção.
    No entanto, observa-se discreta ectasia da aorta abdominal, medindo seu maior diâmetro 3.5 cm.
    Também há placas calcificadas difusas nas artérias ilíacas comuns, com leve estenose.
    
    OPINIÃO:
    1. Achados pulmonares inespecíficos.
    2. Achado Oportunístico: Aneurisma/ectasia da aorta abdominal.
    """
    
    # 2. Aplicar o Filtro
    print(f"Iniciando a filtragem do laudo de teste: {ID_LAUDO_TESTE}")
    
    resultado_filtrado = filtrar_laudo_detalhado_conciso(TEXTO_LAUDO_BRUTO)

    print("\n--- Resultados Finais (Conciso e Agrupado) ---")
    if resultado_filtrado:
        for achado in resultado_filtrado:
            print(f"- Estrutura: {achado['estrutura']}, Patologia: {achado['patologia']}, Detalhe: {achado['detalhe']}")
    else:
        print("Nenhum achado relevante de aorta detectado no texto.")

    # 3. Enviar para o MongoDB
    print("\n--- Iniciando a Integração com MongoDB ---")
    
    salvar_no_mongodb(
        laudo_id=ID_LAUDO_TESTE,
        nome_arquivo_origem="TEXTO_EMBUTIDO",
        texto_laudo_bruto=TEXTO_LAUDO_BRUTO,
        achados_filtrados=resultado_filtrado
    )