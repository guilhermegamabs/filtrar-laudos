import re
import unicodedata
from pymongo import MongoClient
from datetime import datetime
import sys
import os # Novo: Para manipulação de arquivos e diretórios

# --- CONFIGURAÇÕES DO MONGODB ---
MONGO_URI = "mongodb+srv://guilherme_db_user:T8fkkkVcT7K7YMv@cluster0.otygn9m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
NOME_BANCO = "AIHO" 
NOME_COLECAO = "achados_oportunisticos_aorta"

# --- CONFIGURAÇÃO DE PASTA ---
# *** AJUSTE ESTE CAMINHO PARA A PASTA CORRETA DOS SEUS ARQUIVOS TXT ***
# Mude as barras invertidas para barras normais
PASTA_DE_LAUDOS = "C:/Users/zecro/OneDrive/Desktop/laudos_medicos_robustos"
# --- TERMOS DE EXCLUSÃO (Filtro de Foco Primário) ---
EXAMES_FOCO_AORTA = [
    "angiotomografia da aorta", 
    "angio tc de aorta",
    "angio rm da aorta",
    "protocolo de aorta",
    "aneurisma de aorta",
    "dissecção de aorta"
]

# --- FUNÇÕES AUXILIARES (Sem Alterações) ---
def normalizar(texto):
    """Converte o texto para minúsculas e remove acentos."""
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto

def limpar_string_foco(texto):
    """Normaliza a string e remove espaços e pontuações."""
    texto = normalizar(texto)
    texto = re.sub(r'[\s\W_]+', '', texto) 
    return texto

def verificar_foco_principal(texto):
    """Verifica se o laudo parece ser focado diretamente na aorta."""
    cabecalho_limpo = limpar_string_foco(texto[:300])
    
    for termo_exclusao in EXAMES_FOCO_AORTA:
        termo_limpo = limpar_string_foco(termo_exclusao)
        
        if termo_limpo in cabecalho_limpo:
            return True 
    return False


# --- DICIONÁRIOS DE ACHADOS POSITIVOS ---
dicionario_aorta = {
    "estrutura": [
        "aorta", "aortica", "aortico", "raiz", "sinotubular", "ascendente", "arco", 
        "proximal", "medio", "distal", "descendente", "toracica", "abdominal", 
        "iliaca", "iliacas comuns", "ilíaca", "tronco celiaco", "mesenterica superior",
        "mesenterica inferior", "renais", "bifurcacao", "aortopulmonar", 
        "hiato diafragmatico", "vasos", "arteria", 
        "subclávia", "carótida", "vertebral", "femoral", "istmo", "infra-renal", 
        "supraceliaco", "parietal", "íntima", "média", "adventícia",
        "coronaria", "cerebrais", "carotidea", "vertebral"
    ],
    "patologia": [
        "aneurisma", "ectasia", "dilatacao", "expansao", "aneurismatico", "fusiforme", "sacular", "aneurismatica",
        "disseccao", "flap intimal", "falso lumen", "hematoma intramural", "ruptura da intima", "hematoma mural",
        "trombo mural", "trombose", "formacao trombotica", "coagulo", "trombo aderido",
        "sangramento ativo", "hematoma periaortico",
        "pseudoaneurisma", "endoprótese",
        "stent", "graft", "by-pass", "bypass", 
        "calcificacao", "aterosclerose", "placa", "ateromatose", "deposito calcico", "ateroma", "esclerose", 
        "irregularidade parietal", "espessamento parietal", 
        "estenose", "coarctacao", "estreitamento", "afilamento", "calcificado"
    ],
    "detalhe": [
        "calibre", "aumentado", "dilatado", "irregular", "espessamento", "sinais de", "sugestivo de",
        "compativel com", "obstruido", "estenose", "diametro", "dimensoes", "mm", "cm", "espessura", 
        "extensao", "maior diametro", "medindo", "comprimindo", "estenosa", "grau", "critica", "significativa",
        "leve", "moderado", "acentuado", "parcial", "laminar", "excêntrico", "simétrico", 
        "variando de", "até", "totalizando", "enxerto", "prótese"
    ]
}

# GRUPOS DE PATOLOGIA PARA CONSISÃO (Sem Alterações)
PATOLOGIAS_FRACAS_ATEROSCLEROSE = [
    "placa", "ateromatose", "deposito calcico", "ateroma", "esclerose", 
    "irregularidade parietal", "espessamento parietal", 
    "estenose", "coarctacao", "estreitamento", "afilamento",
    "calcificado"
]
PATOLOGIAS_FORTES_ATEROSCLEROSE = ["calcificacao", "aterosclerose"]
PATOLOGIAS_FRACAS_DILATACAO = ["ectasia", "dilatacao", "expansao", "fusiforme", "sacular", "proeminente", "alongado"]


def filtrar_laudo_detalhado_conciso(texto):
    """
    Função principal que busca e agrupa achados positivos no texto.
    (Lógica interna inalterada em relação à sua última versão corrigida)
    """
    texto_norm = normalizar(texto)
    achados_detectados = []
    achados_unicos_set = set()

    for estrutura in dicionario_aorta["estrutura"]:
        for patologia in dicionario_aorta["patologia"]:
            
            padrao = rf"({estrutura}.*?{patologia})|({patologia}.*?{estrutura})"
            
            for match in re.finditer(padrao, texto_norm):
                
                start_contexto = max(0, match.start() - 50)
                end_contexto = min(len(texto_norm), match.end() + 50)
                contexto_match = texto_norm[start_contexto: end_contexto]
                
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
                    
                    detalhes_encontrados = [det for det in dicionario_aorta["detalhe"] if det in contexto_match]
                    
                    achados_detectados.append({
                        "estrutura": estrutura,
                        "patologia": patologia_agrupada,
                        "detalhe": detalhes_encontrados if detalhes_encontrados else None
                    })
                    achados_unicos_set.add(achado_tuple)

    return achados_detectados

# --- FUNÇÃO DE SALVAMENTO NO MONGODB (Inalterada) ---
def salvar_no_mongodb(laudo_id: str, nome_arquivo_origem: str, texto_laudo_bruto: str, achados_filtrados: list):
    """Conecta ao MongoDB e insere um documento contendo os achados estruturados."""
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
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000) 
        cliente.admin.command('ping') 
        
        db = cliente[NOME_BANCO]
        colecao = db[NOME_COLECAO]
        
        if achados_filtrados:
            resultado = colecao.insert_one(documento)
            print(f"  ✅ Sucesso: Documento inserido (ID: {laudo_id})")
        else:
            print(f"  ⚠️ Ignorado: Nenhum AO detectado (ID: {laudo_id})")

    except Exception as e:
        print(f"\n❌ ERRO FATAL ao tentar conectar ou inserir o arquivo {nome_arquivo_origem}: {e}")
        # Não usamos sys.exit(1) aqui para não parar o processamento do lote inteiro
        # mas você pode querer logar esse erro separadamente.
        
    finally:
        if cliente:
            cliente.close()

# --- NOVO FLUXO DE PROCESSAMENTO EM LOTE ---

def processar_pasta_laudos(caminho_pasta):
    """
    Itera sobre todos os arquivos TXT em uma pasta, processa cada laudo 
    e envia os resultados para o MongoDB.
    """
    if not os.path.isdir(caminho_pasta):
        print(f"\n❌ ERRO: O caminho '{caminho_pasta}' não é uma pasta válida ou não existe.")
        return

    arquivos = [f for f in os.listdir(caminho_pasta) if f.endswith('.txt')]
    
    if not arquivos:
        print(f"\n⚠️ Aviso: Nenhuma arquivo .txt encontrado na pasta: '{caminho_pasta}'")
        return

    print(f"\n--- Iniciando Processamento de {len(arquivos)} Laudo(s) ---")
    
    for nome_arquivo in arquivos:
        caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
        laudo_id = nome_arquivo.replace('.txt', '') # Usa o nome do arquivo como ID

        print(f"\n[Processando] -> {nome_arquivo}")

        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                texto_laudo_bruto = f.read()
            
            # 1. Filtro de Foco Primário
            if verificar_foco_principal(texto_laudo_bruto):
                print("  ❌ Laudo Ignorado: Foco primário na Aorta.")
                continue

            # 2. Filtragem de Achados Oportunísticos
            resultado_filtrado = filtrar_laudo_detalhado_conciso(texto_laudo_bruto)

            # 3. Envio para o MongoDB
            salvar_no_mongodb(
                laudo_id=laudo_id,
                nome_arquivo_origem=nome_arquivo,
                texto_laudo_bruto=texto_laudo_bruto,
                achados_filtrados=resultado_filtrado
            )
            
        except FileNotFoundError:
            print(f"  ❌ ERRO: Arquivo não encontrado: {caminho_completo}")
        except Exception as e:
            print(f"  ❌ ERRO INESPERADO ao ler ou processar o arquivo {nome_arquivo}: {e}")

    print("\n--- Processamento de Lote Concluído ---")


# --- FLUXO PRINCIPAL DE EXECUÇÃO ---

if __name__ == "__main__":
    # Executa a função de processamento em lote usando o caminho definido acima
    processar_pasta_laudos(PASTA_DE_LAUDOS)