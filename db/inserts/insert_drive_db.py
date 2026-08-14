import os
import gdown
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 1. Carrega as variáveis do .env
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 2. Cria conexão com MySQL (charset utf8mb4 na tabela de destino)
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# 3. Download dos arquivos da pasta do Google Drive
DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1vyX3van3t5t5ZT_2wrxQzj9LWdB7HY4E?usp=drive_link"
PASTA_DESTINO = "./data/processed"

os.makedirs(PASTA_DESTINO, exist_ok=True)

print("--- Baixando arquivos da pasta do Google Drive ---")
gdown.download_folder(url=DRIVE_FOLDER_URL, output=PASTA_DESTINO, quiet=False)

# 4. Mapeamento de arquivos: nome_arquivo -> (nome_tabela, separador)
# O arquivo de censo utiliza ';' como separador
MAPEAMENTO_ARQUIVOS = {
    "RESULTADOS_LIMPO_2.csv": {"tabela": "resultados", "sep": ","},
    "PARTICIPANTES_LIMPO.csv": {"tabela": "participantes", "sep": ","},
    "ibge_agregado.csv": {"tabela": "ibge", "sep": ","},
    "microdados_censo_2024_2025_tecnologia.csv": {"tabela": "censo", "sep": ";"}
}

# 5. Tamanho dos lotes
CHUNK_SIZE_CSV = 100_000
CHUNK_SIZE_SQL = 1_000

# 6. Processamento dos arquivos
for nome_arquivo, config in MAPEAMENTO_ARQUIVOS.items():
    nome_tabela = config["tabela"]
    separador = config["sep"]
    caminho_csv = os.path.join(PASTA_DESTINO, nome_arquivo)
    
    print(f"\n--- Iniciando carga: {nome_arquivo} -> Tabela '{nome_tabela}' ---")

    if not os.path.exists(caminho_csv):
        print(f"ERRO: Arquivo não encontrado: {caminho_csv}")
        continue

    try:
        csv_reader = pd.read_csv(
            caminho_csv,
            sep=separador,
            encoding="utf-8",
            chunksize=CHUNK_SIZE_CSV
        )

        for i, chunk in enumerate(csv_reader):
            # Converte NaN do pandas em None -> vira NULL no MySQL
            chunk = chunk.where(pd.notnull(chunk), None)

            chunk.to_sql(
                name=nome_tabela,
                con=engine,
                if_exists="append",
                index=False,
                chunksize=CHUNK_SIZE_SQL,
                method="multi"
            )
            print(
                f"  └─ Bloco {i + 1} inserido "
                f"({len(chunk)} linhas) na tabela '{nome_tabela}'"
            )

        print(
            f"SUCCESS: Arquivo '{nome_arquivo}' "
            f"carregado com sucesso na tabela '{nome_tabela}'!"
        )

    except UnicodeDecodeError as e:
        print(
            f"ERRO DE ENCODING ao ler '{nome_arquivo}': {e}\n"
            f"  Dica: rode novamente o chardet.detect() nesse arquivo "
            f"específico, o encoding pode variar entre arquivos."
        )
    except Exception as e:
        print(
            f"ERRO ao processar "
            f"'{nome_arquivo}': {e}"
        )

print("\n--- Processo de carga finalizado para todas as tabelas! ---")