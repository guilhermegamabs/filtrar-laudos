import re
import unicodedata
from pymongo import MongoClient
from datetime import datetime
import sys
import os

# --- CONFIGURAÇÕES DO MONGODB ---
MONGO_URI = "mongodb+srv://guilherme_db_user:T8fkkkVcT7K7YMv@cluster0.otygn9m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
NOME_BANCO = "AIHO"
NOME_COLECAO = "achados_oportunisticos_aorta"

# --- CONFIGURAÇÃO DE PASTA ---
PASTA_DE_LAUDOS = "C:/Users/TEC/Desktop/filtrar-laudos-main/laudos"

# --- TERMOS DE EXCLUSÃO (Filtro de Foco Primário) ---
EXAMES_FOCO_AORTA = ["angiotomografia da aorta", "angio tc de aorta", "angio rm da aorta", "angio", "tc", "angio tc"]

# --- FUNÇÕES AUXILIARES (Inalteradas) ---
def normalizar(texto):
    texto = texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpar_string_foco(texto):
    texto = normalizar(texto)
    return re.sub(r'[\s\W_]+', '', texto)

def verificar_foco_principal(texto):
    cabecalho_limpo = limpar_string_foco(texto[:300])
    for termo_exclusao in EXAMES_FOCO_AORTA:
        if limpar_string_foco(termo_exclusao) in cabecalho_limpo:
            return True 
    return False

# ★★★ BASE DE CONHECIMENTO OTIMIZADA ★★★
# A lógica de agrupamento está na própria estrutura dos dicionários.

ESTRUTURAS_MAPEADAS = {
    "aorta": ["aorta", "aortica", "aortico", "raiz", "sinotubular", "ascendente", "arco", "descendente", "toracica", "abdominal", "aortopulmonar", "tronco braquiocefalico"],
    "iliaca": ["iliaca", "iliacas comuns", "ilíaca"],
    "vasos_abdominais": ["tronco celiaco", "mesenterica superior", "mesenterica inferior", "renais"],
    "vasos_cervicais": ["carótida", "carotidea", "vertebral", "subclávia"],
    "outros_vasos": ["vasos", "arteria", "femoral", "coronaria", "cerebrais"],
    "camadas_vasculares": ["parietal", "íntima", "média", "adventícia"],
    "referencia_geral": ["bifurcacao", "hiato diafragmatico", "istmo", "infra-renal", "supraceliaco", "proximal", "medio", "distal"]
}

PATOLOGIAS_MAPEADAS = {
    "aneurisma/dilatacao": ["aneurisma", "ectasia", "dilatacao", "expansao", "aneurismatico", "fusiforme", "sacular", "aneurismatica", "proeminente", "alongado"],
    "disseccao": ["disseccao", "flap intimal", "falso lumen", "hematoma intramural", "ruptura da intima", "hematoma mural"],
    "trombose": ["trombo mural", "trombose", "formacao trombotica", "coagulo", "trombo aderido"],
    "calcificacao/aterosclerose": ["calcificacao", "aterosclerose", "placa", "ateromatose", "deposito calcico", "ateroma", "esclerose", "calcificado"],
    "estenose/coarctacao": ["estenose", "coarctacao", "estreitamento", "afilamento"],
    "variacao_anatomica/anomalia": ["arco bovino", "variacao anatomica", "variacao da normalidade", "anomalia de origem"],
    "sinais_gerais_doenca": ["irregularidade parietal", "espessamento parietal", "sangramento ativo", "hematoma periaortico", "pseudoaneurisma"],
    "procedimento_previo": ["endoprótese", "stent", "graft", "by-pass", "bypass", "prótese", "enxerto"]
}

dicionario_detalhe = ["calibre", "aumentado", "dilatado", "irregular", "espessamento", "sinais de", "sugestivo de", "compativel com", "obstruido", "diametro", "dimensoes", "mm", "cm", "espessura", "extensao", "maior diametro", "medindo", "comprimindo", "estenosa", "grau", "critica", "significativa", "leve", "moderado", "acentuado", "parcial", "laminar", "excêntrico", "simétrico", "variando de", "até", "totalizando", "limite", "superior"]

# ★ NOVO: LISTA DE TERMOS DE NEGAÇÃO ★
# Termos que, se encontrados na mesma expressão do achado, o invalidam.
TERMOS_DE_NEGACAO = [
    "sem evidencia de", "ausencia de", "nao se observa", "nao se observando", 
    "sem sinais de", "afastada a hipotese de", "nao ha", "negativo para", 
    "sem alteracoes", "dentro da normalidade", "nao associado a"
]

# ★★★ FUNÇÃO DE FILTRAGEM COM NEGAÇÃO PRECISA ★★★
def filtrar_laudo_detalhado_conciso(texto):
    texto_norm = normalizar(texto)
    achados_agrupados = {}
    achados_unicos_set = set()

    # Itera sobre os termos RAIZ e suas variações
    for estrutura_raiz, variacoes_estrutura in ESTRUTURAS_MAPEADAS.items():
        for patologia_raiz, variacoes_patologia in PATOLOGIAS_MAPEADAS.items():
            
            # Cria um padrão regex que busca qualquer variação da estrutura próxima a qualquer variação da patologia
            padrao_estrutura_str = "|".join(variacoes_estrutura)
            padrao_patologia_str = "|".join(variacoes_patologia)
            padrao = rf"({padrao_estrutura_str}).*?({padrao_patologia_str})|({padrao_patologia_str}).*?({padrao_estrutura_str})"
            
            for match in re.finditer(padrao, texto_norm):
                achado_tuple = (estrutura_raiz, patologia_raiz)
                
                if achado_tuple not in achados_unicos_set:

                    # --- LÓGICA DE NEGAÇÃO PRECISA ---
                    # Pega a string exata que o regex encontrou (de estrutura a patologia)
                    trecho_encontrado = match.group(0)
                    
                    # Verifica se algum termo de negação está DENTRO deste trecho específico.
                    if any(negacao in trecho_encontrado for negacao in TERMOS_DE_NEGACAO):
                        continue # Pula este achado, pois ele está sendo negado diretamente.

                    # Se não encontrou negação, o resto do código continua...
                    start_contexto = max(0, match.start() - 50)
                    end_contexto = min(len(texto_norm), match.end() + 50)
                    contexto_match = texto_norm[start_contexto:end_contexto]
                    
                    detalhes_encontrados = [det for det in dicionario_detalhe if det in contexto_match]
                    
                    info_patologia = {
                        "patologia": patologia_raiz,
                        "detalhe": detalhes_encontrados if detalhes_encontrados else None
                    }
                    
                    if estrutura_raiz not in achados_agrupados:
                        achados_agrupados[estrutura_raiz] = []
                    
                    achados_agrupados[estrutura_raiz].append(info_patologia)
                    achados_unicos_set.add(achado_tuple)

    resultado_final = []
    for estrutura_chave, lista_de_achados in achados_agrupados.items():
        resultado_final.append({"estrutura": estrutura_chave, "achados": lista_de_achados})
    return resultado_final

# --- FUNÇÃO DE SALVAMENTO NO MONGODB (Inalterada) ---
def salvar_no_mongodb(laudo_id: str, nome_arquivo_origem: str, texto_laudo_bruto: str, achados_filtrados: list):
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
        resultado = colecao.insert_one(documento)
        print(f"   ✅ Sucesso: Documento processado e inserido (ID: {laudo_id}) - Achados: {status_ao}")
    except Exception as e:
        print(f"\n❌ ERRO FATAL ao tentar conectar ou inserir o arquivo {nome_arquivo_origem}: {e}")
    finally:
        if cliente:
            cliente.close()

# --- FLUXO DE PROCESSAMENTO EM LOTE (Inalterado) ---
def processar_pasta_laudos(caminho_pasta):
    if not os.path.isdir(caminho_pasta):
        print(f"\n❌ ERRO: O caminho '{caminho_pasta}' não é uma pasta válida ou não existe.")
        return
    arquivos = [f for f in os.listdir(caminho_pasta) if f.endswith('.txt')]
    if not arquivos:
        print(f"\n⚠️ Aviso: Nenhum arquivo .txt encontrado na pasta: '{caminho_pasta}'")
        return
    print(f"\n--- Iniciando Processamento de {len(arquivos)} Laudo(s) ---")
    for nome_arquivo in arquivos:
        caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
        laudo_id = nome_arquivo.replace('.txt', '')
        print(f"\n[Processando] -> {nome_arquivo}")
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                texto_laudo_bruto = f.read()
            if verificar_foco_principal(texto_laudo_bruto):
                print("   ❌ Laudo Ignorado: Foco primário na Aorta.")
                continue
            resultado_filtrado = filtrar_laudo_detalhado_conciso(texto_laudo_bruto)
            salvar_no_mongodb(laudo_id=laudo_id, nome_arquivo_origem=nome_arquivo, texto_laudo_bruto=texto_laudo_bruto, achados_filtrados=resultado_filtrado)
        except FileNotFoundError:
            print(f"   ❌ ERRO: Arquivo não encontrado: {caminho_completo}")
        except Exception as e:
            print(f"   ❌ ERRO INESPERADO ao ler ou processar o arquivo {nome_arquivo}: {e}")
    print("\n--- Processamento de Lote Concluído ---")

# --- FLUXO PRINCIPAL DE EXECUÇÃO (Inalterado) ---
if __name__ == "__main__":
    processar_pasta_laudos(PASTA_DE_LAUDOS)
