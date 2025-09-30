import re
import unicodedata
from pymongo import MongoClient
from datetime import datetime
import sys

# --- CONFIGURAÇÕES DO MONGODB ---
# Ajuste as credenciais e nomes de coleções conforme a necessidade
MONGO_URI = "mongodb+srv://guilherme_db_user:T8fkkkVcT7K7YMv@cluster0.otygn9m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
NOME_BANCO = "AIHO" 
NOME_COLECAO = "achados_oportunisticos_aorta"

# --- TERMOS DE EXCLUSÃO (Filtro de Foco Primário) ---
EXAMES_FOCO_AORTA = [
    "angiotomografia da aorta", 
    "angio tc de aorta",
    "angio rm da aorta",
    "protocolo de aorta",
    "aneurisma de aorta",
    "dissecção de aorta"
]

# --- FUNÇÕES AUXILIARES ---

def normalizar(texto):
    """
    Converte o texto para minúsculas e remove acentos para facilitar a busca.
    """
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto

def limpar_string_foco(texto):
    """
    Normaliza a string e remove espaços e pontuações para tornar a comparação robusta.
    """
    texto = normalizar(texto)
    # Remove todos os caracteres não-alfanuméricos e espaços (torna 'angio-tc' em 'angiotc')
    texto = re.sub(r'[\s\W_]+', '', texto) 
    return texto

def verificar_foco_principal(texto):
    """
    Verifica se o laudo parece ser focado diretamente na aorta e retorna True se deve ser excluído.
    """
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

# GRUPOS DE PATOLOGIA PARA CONSISÃO
PATOLOGIAS_FRACAS_ATEROSCLEROSE = [
    "placa", "ateromatose", "deposito calcico", "ateroma", "esclerose", 
    "irregularidade parietal", "espessamento parietal", 
    "estenose", "coarctacao", "estreitamento", "afilamento",
    "calcificado"
]
PATOLOGIAS_FORTES_ATEROSCLEROSE = ["calcificacao", "aterosclerose"]
PATOLOGIAS_FRACAS_DILATACAO = ["ectasia", "dilatacao", "expansao", "fusiforme", "sacular", "proeminente", "alongado"]


def filtrar_laudo_detalhado_conciso(texto):
    texto_norm = normalizar(texto)
    achados_detectados = []
    achados_unicos_set = set()

    for estrutura in dicionario_aorta["estrutura"]:
        for patologia in dicionario_aorta["patologia"]:
            
            # Padrão busca (Estrutura...Patologia) ou (Patologia...Estrutura)
            padrao = rf"({estrutura}.*?{patologia})|({patologia}.*?{estrutura})"
            
            for match in re.finditer(padrao, texto_norm):
                
                # 1. Definir a Janela de Contexto (50 caracteres antes, 50 depois)
                start_contexto = max(0, match.start() - 50)
                end_contexto = min(len(texto_norm), match.end() + 50)
                contexto_match = texto_norm[start_contexto: end_contexto]
                
                # 2. Lógica de Agrupamento: Define a Patologia Agrupada (Concisa)
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
                    
                    # 3. Busca por detalhes no contexto
                    detalhes_encontrados = [det for det in dicionario_aorta["detalhe"] if det in contexto_match]
                    
                    achados_detectados.append({
                        "estrutura": estrutura,
                        "patologia": patologia_agrupada,
                        "detalhe": detalhes_encontrados if detalhes_encontrados else None
                    })
                    achados_unicos_set.add(achado_tuple)

    return achados_detectados

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
        cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000) 
        cliente.admin.command('ping') 
        
        db = cliente[NOME_BANCO]
        colecao = db[NOME_COLECAO]
        
        # Só insere se houver achados detectados
        if achados_filtrados:
            resultado = colecao.insert_one(documento)
            print(f"\n✅ Sucesso: Documento inserido no DB '{NOME_BANCO}' / Coleção '{NOME_COLECAO}'.")
            print(f"ID do Documento MongoDB: {resultado.inserted_id}")
        else:
            print("\n⚠️ Inserção no MongoDB Ignorada: Nenhum Achado Oportunístico detectado.")

    except Exception as e:
        print(f"\n❌ ERRO FATAL: Falha ao conectar ou inserir no MongoDB.")
        print(f"Detalhes do Erro: {e}")
        sys.exit(1)
        
    finally:
        if cliente:
            cliente.close()


# --- FLUXO PRINCIPAL DE EXECUÇÃO ---

if __name__ == "__main__":
    
    # Exemplo de Laudo (Angio-TC de Aorta Abdominal)
    ID_LAUDO_TESTE = "LAUDO_04_BOTAO_FIX"
    TEXTO_LAUDO_BRUTO = """
        TC Abdome. Paciente de 59 anos. Achados: Diverticulite aguda. Aorta abdominal sem alterações.
    """
    
    print(f"Iniciando a verificação do laudo: {ID_LAUDO_TESTE}")
    
    # 1. PASSO DE EXCLUSÃO DE FOCO PRIMÁRIO (Mantido para segurança)
    if verificar_foco_principal(TEXTO_LAUDO_BRUTO):
        print("❌ LAUDO IGNORADO: O foco principal é a AORTA (Angio-TC). Não é Achado Oportunístico.")
    else:
        # Se passar no filtro, prossegue com a filtragem
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