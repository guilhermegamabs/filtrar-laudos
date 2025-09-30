import pdfplumber
import os

def ler_pdf_e_salvar_texto(caminho_pdf, nome_arquivo_txt="laudo_extraido.txt"):
    """
    Extrai o texto de um arquivo PDF e salva o conteúdo em um novo arquivo .txt.

    Args:
        caminho_pdf (str): O caminho completo para o arquivo PDF de entrada.
        nome_arquivo_txt (str): O nome do arquivo de texto de saída.
    """
    if not os.path.exists(caminho_pdf):
        print(f"ERRO: Arquivo PDF não encontrado em: {caminho_pdf}")
        return

    texto_completo = ""
    try:
        print(f"Iniciando leitura do PDF: {caminho_pdf}...")
        with pdfplumber.open(caminho_pdf) as pdf:
            for i, page in enumerate(pdf.pages):
                texto_completo += page.extract_text() + "\n"
                print(f"  Página {i+1} processada.")
        
        # Salva o texto extraído no arquivo .txt
        with open(nome_arquivo_txt, 'w', encoding='utf-8') as f:
            f.write(texto_completo)
            
        print(f"\nSUCESSO: Texto extraído e salvo em: {nome_arquivo_txt}")
        
    except Exception as e:
        print(f"\nERRO ao processar o PDF com pdfplumber: {e}")

# --- INSTRUÇÕES DE USO ---
# 1. Instale a biblioteca necessária: pip install pdfplumber
# 2. **SUBSTITUA** o caminho abaixo pelo caminho real do seu arquivo PDF.
CAMINHO_DO_SEU_LAUDO_PDF = "C:/Users/seu_usuario/Desktop/AIHO/laudo_exemplo.pdf" 

if __name__ == "__main__":
    ler_pdf_e_salvar_texto(CAMINHO_DO_SEU_LAUDO_PDF)