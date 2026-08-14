"""
==================================================================================
 SCRIPT DE TRATAMENTO, LIMPEZA E UNIFICAÇÃO DOS MICRODADOS DO ENEM (2024 e 2025)
==================================================================================
Consolida:
  - PARTICIPANTES_2024.csv + PARTICIPANTES_2025.csv -> PARTICIPANTES_TRATADOS.csv
  - RESULTADOS_2024.csv   + RESULTADOS_2025.csv      -> RESULTADOS_TRATADOS.csv

Autor: Pipeline gerado para o projeto de correlação ENEM x IBGE.
==================================================================================
"""

import pandas as pd
from pathlib import Path

# ----------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE CAMINHOS
# ----------------------------------------------------------------------------------
DIRETORIO_ENTRADA = Path("./data/raw")
DIRETORIO_SAIDA = Path("./data/processed")
DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

ARQUIVOS_PARTICIPANTES = {
    2024: DIRETORIO_ENTRADA / "PARTICIPANTES_2024.csv",
    2025: DIRETORIO_ENTRADA / "PARTICIPANTES_2025.csv",
}

ARQUIVOS_RESULTADOS = {
    2024: DIRETORIO_ENTRADA / "RESULTADOS_2024.csv",
    2025: DIRETORIO_ENTRADA / "RESULTADOS_2025.csv",
}

SAIDA_PARTICIPANTES = DIRETORIO_SAIDA / "PARTICIPANTES_TRATADOS.csv"
SAIDA_RESULTADOS = DIRETORIO_SAIDA / "RESULTADOS_TRATADOS.csv"


# ----------------------------------------------------------------------------------
# 2. COLUNAS A MANTER (NOMES ORIGINAIS, PARA LEITURA SELETIVA COM usecols)
# ----------------------------------------------------------------------------------
COLUNAS_ORIGINAIS_PARTICIPANTES = [
    "NU_INSCRICAO", "NU_ANO", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_COR_RACA",
    "CO_MUNICIPIO_PROVA", "NO_MUNICIPIO_PROVA", "SG_UF_PROVA",
    "Q006", "Q007", "Q023",
]
# OBS: CO_UF_PROVA é lido? NÃO — foi removido também da leitura (usecols),
# já que a coluna final não será mais mantida (ver instrução de remoção abaixo).
# SG_UF_PROVA sozinho já é suficiente para identificar a UF da prova.

COLUNAS_ORIGINAIS_RESULTADOS = [
    "NU_SEQUENCIAL", "NU_ANO", "CO_ESCOLA", "CO_MUNICIPIO_ESC", "NO_MUNICIPIO_ESC",
    "CO_UF_ESC", "SG_UF_ESC", "TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC",
    "TP_SIT_FUNC_ESC", "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT",
    "NU_NOTA_REDACAO",
]

# Ordem final desejada de saída (após renomear). CO_UF_PROVA foi REMOVIDA.
ORDEM_FINAL_PARTICIPANTES = [
    "NU_INSCRICAO", "NU_ANO", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_COR_RACA",
    "CO_MUNICIPIO_PROVA", "NO_MUNICIPIO_PROVA", "SG_UF_PROVA",
    "POSSUI_RENDA", "RENDA_FAMILIAR", "TIPO_DE_ESCOLA_EM",
]

# MEDIA_GERAL foi ADICIONADA ao final (coluna calculada).
ORDEM_FINAL_RESULTADOS = [
    "NU_SEQUENCIAL", "NU_ANO", "CO_ESCOLA", "CO_MUNICIPIO_ESC", "NO_MUNICIPIO_ESC",
    "CO_UF_ESC", "SG_UF_ESC", "TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC",
    "TP_SIT_FUNC_ESC", "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT",
    "NU_NOTA_REDACAO", "MEDIA_GERAL",
]

# Colunas de identificação da escola: NaN -> 0 (mantidas numéricas)
COLUNAS_ID_ESCOLA_PREENCHER_ZERO = ["CO_ESCOLA", "CO_MUNICIPIO_ESC"]

# Colunas categóricas/textuais da escola: NaN -> 'Não informado'
# (preenchidas DEPOIS do mapeamento de código -> descrição)
COLUNAS_ESCOLA_PREENCHER_NAO_INFORMADO = [
    "NO_MUNICIPIO_ESC", "CO_UF_ESC", "SG_UF_ESC",
    "TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC", "TP_SIT_FUNC_ESC",
]


# ----------------------------------------------------------------------------------
# 3. DICIONÁRIOS DE MAPEAMENTO (VALORES CATEGÓRICOS)
# ----------------------------------------------------------------------------------
MAPA_POSSUI_RENDA = {  # a partir de Q006
    "A": False,
    "B": True,
}

# --------------------------------------------------------------------------
# RENDA_FAMILIAR (Q007) — mapeamento DINÂMICO por ano, em faixas de
# Salário Mínimo (SM). O INEP reancora as faixas em R$ a cada ano conforme
# o SM vigente, mas em termos de SM as faixas representam a mesma coisa —
# por isso o texto final é o mesmo para 2024 e 2025; o que muda é o SM de
# referência usado para construir essas faixas (guardado aqui só como
# documentação/rastreabilidade, e para futura extensão caso um dia seja
# necessário reexibir o valor em R$).
# --------------------------------------------------------------------------
SALARIO_MINIMO_POR_ANO = {
    2024: 1412.00,
    2025: 1518.00,
}

MAPA_RENDA_FAMILIAR_SM = {  # faixas em SM, já em CAIXA ALTA
    "A": "NENHUMA RENDA",
    "B": "ATÉ 1 SM",
    "C": "DE 1 A 1.5 SM",
    "D": "DE 1.5 A 2 SM",
    "E": "DE 2 A 2.5 SM",
    "F": "DE 2.5 A 3 SM",
    "G": "DE 3 A 4 SM",
    "H": "DE 4 A 5 SM",
    "I": "DE 5 A 6 SM",
    "J": "DE 6 A 7 SM",
    "K": "DE 7 A 8 SM",
    "L": "DE 8 A 9 SM",
    "M": "DE 9 A 10 SM",
    "N": "DE 10 A 12 SM",
    "O": "DE 12 A 15 SM",
    "P": "DE 15 A 20 SM",
    "Q": "ACIMA DE 20 SM",
}

# Mapeamento por ano (chave = NU_ANO do arquivo). Ambos os anos usam o
# mesmo dicionário de faixas em SM (ver explicação acima), mas a estrutura
# em dict-por-ano é mantida para permitir customização futura ano a ano
# sem alterar a lógica de aplicação.
MAPA_RENDA_FAMILIAR_POR_ANO = {
    2024: MAPA_RENDA_FAMILIAR_SM,
    2025: MAPA_RENDA_FAMILIAR_SM,
}


def obter_mapa_renda_familiar(ano: int) -> dict:
    """Retorna o dicionário de mapeamento de RENDA_FAMILIAR (em SM) para o ano informado.
    Se o ano não estiver cadastrado, usa o mapeamento do ano mais recente disponível
    como fallback seguro (evita quebrar o script para anos futuros ainda não mapeados)."""
    if ano in MAPA_RENDA_FAMILIAR_POR_ANO:
        return MAPA_RENDA_FAMILIAR_POR_ANO[ano]
    ano_mais_recente = max(MAPA_RENDA_FAMILIAR_POR_ANO.keys())
    print(
        f"  AVISO: não há mapeamento de RENDA_FAMILIAR cadastrado para o ano {ano}. "
        f"Usando o mapeamento de {ano_mais_recente} como fallback."
    )
    return MAPA_RENDA_FAMILIAR_POR_ANO[ano_mais_recente]

MAPA_FAIXA_ETARIA = {  # a partir de TP_FAIXA_ETARIA
    1: "Menor de 17 anos", 2: "17 anos", 3: "18 anos", 4: "19 anos",
    5: "20 anos", 6: "21 anos", 7: "22 anos", 8: "23 anos", 9: "24 anos",
    10: "25 anos", 11: "Entre 26 e 30 anos", 12: "Entre 31 e 35 anos",
    13: "Entre 36 e 40 anos", 14: "Entre 41 e 45 anos", 15: "Entre 46 e 50 anos",
    16: "Entre 51 e 55 anos", 17: "Entre 56 e 60 anos", 18: "Entre 61 e 65 anos",
    19: "Entre 66 e 70 anos", 20: "Maior de 70 anos",
}

MAPA_COR_RACA = {  # a partir de TP_COR_RACA
    0: "Não declarado",
    1: "Branca",
    2: "Preta",
    3: "Parda",
    4: "Amarela",
    5: "Indígena",
}

MAPA_TIPO_ESCOLA_EM = {  # a partir de Q023
    "A": "Somente em escola pública.",
    "B": "Parte em escola pública e parte em escola privada sem bolsa de estudo integral",
    "C": "Parte em escola pública e parte em escola privada com bolsa de estudo integral",
    "D": "Somente em escola privada sem bolsa de estudo integral",
    "E": "Somente em escola privada com bolsa de estudo integral",
    "F": "Não frequentei escola de Ensino Médio",
}

MAPA_UF_ESC = {  # a partir de CO_UF_ESC
    11: "Rondônia", 12: "Acre", 13: "Amazonas", 14: "Roraima", 15: "Pará",
    16: "Amapá", 17: "Tocantins", 21: "Maranhão", 22: "Piauí", 23: "Ceará",
    24: "Rio Grande do Norte", 25: "Paraíba", 26: "Pernambuco", 27: "Alagoas",
    28: "Sergipe", 29: "Bahia", 31: "Minas Gerais", 32: "Espírito Santo",
    33: "Rio de Janeiro", 35: "São Paulo", 41: "Paraná", 42: "Santa Catarina",
    43: "Rio Grande do Sul", 50: "Mato Grosso do Sul", 51: "Mato Grosso",
    52: "Goiás", 53: "Distrito Federal",
}

MAPA_DEPENDENCIA_ADM_ESC = {  # a partir de TP_DEPENDENCIA_ADM_ESC
    1: "Federal",
    2: "Estadual",
    3: "Municipal",
    4: "Privada",
}

MAPA_LOCALIZACAO_ESC = {  # a partir de TP_LOCALIZACAO_ESC
    1: "Urbana",
    2: "Rural",
}

MAPA_SIT_FUNC_ESC = {  # a partir de TP_SIT_FUNC_ESC
    1: "Em atividade",
    2: "Paralisada",
    3: "Extinta",
    4: "Escola extinta em anos anteriores.",
}


# ----------------------------------------------------------------------------------
# 4. FUNÇÕES AUXILIARES
# ----------------------------------------------------------------------------------
def ler_csv_flexivel(caminho: Path, usecols: list) -> pd.DataFrame:
    """
    Lê um CSV de microdados do ENEM tentando combinações comuns de
    encoding/separador (';' + 'latin1' é o padrão do INEP, mas cobrimos
    variações de exportações manuais também).
    Todas as colunas são lidas como string (dtype=str) para preservar
    códigos e zeros à esquerda; conversões numéricas são feitas depois,
    coluna a coluna, onde fizer sentido.
    """
    tentativas = [
        {"encoding": "utf-8-sig", "sep": ";"},
        {"encoding": "latin1", "sep": ";"},
        {"encoding": "iso-8859-1", "sep": ";"},
        {"encoding": "utf-8-sig", "sep": ","},
        {"encoding": "latin1", "sep": ","},
    ]

    ultimo_erro = None
    for tentativa in tentativas:
        try:
            df = pd.read_csv(
                caminho,
                usecols=usecols,
                dtype=str,
                encoding=tentativa["encoding"],
                sep=tentativa["sep"],
                low_memory=False,
            )
            # Se leu apenas 1 coluna, provavelmente o separador está errado
            if df.shape[1] < 2 and len(usecols) > 1:
                continue
            print(
                f"    -> Lido com sucesso (encoding='{tentativa['encoding']}', "
                f"sep='{tentativa['sep']}')."
            )
            return df
        except Exception as erro:
            ultimo_erro = erro
            continue

    raise RuntimeError(
        f"Não foi possível ler o arquivo '{caminho}' com nenhuma combinação "
        f"de encoding/separador testada. Último erro: {ultimo_erro}"
    )


def mapear_com_seguranca(serie: pd.Series, mapa: dict) -> pd.Series:
    """
    Aplica um dicionário de mapeamento a uma Series, mas preserva o valor
    ORIGINAL quando ele não existir no dicionário (em vez de virar NaN).
    Isso evita perda silenciosa de dado por categoria não prevista.
    """
    mapeado = serie.map(mapa)
    return mapeado.fillna(serie)


def converter_para_numero(serie: pd.Series) -> pd.Series:
    """
    Converte uma coluna de string para número, tratando o caso comum de
    decimal exportado com vírgula (padrão BR) em vez de ponto.
    """
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def converter_para_inteiro_nullable(serie: pd.Series) -> pd.Series:
    """Converte string -> Int64 nullable (aceita NaN, ao contrário de int comum)."""
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


# ----------------------------------------------------------------------------------
# 5. TRATAMENTO — TABELA PARTICIPANTES
# ----------------------------------------------------------------------------------
def tratar_participantes(caminho: Path, ano: int) -> pd.DataFrame:
    print(f"Carregando PARTICIPANTES_{ano}...")
    df = ler_csv_flexivel(caminho, usecols=COLUNAS_ORIGINAIS_PARTICIPANTES)

    print(f"  Mapeando colunas de PARTICIPANTES_{ano}...")

    # Renomeações (todas em CAIXA ALTA)
    df = df.rename(columns={
        "Q006": "POSSUI_RENDA",
        "Q007": "RENDA_FAMILIAR",
        "Q023": "TIPO_DE_ESCOLA_EM",
    })

    # RENDA_FAMILIAR: mapeamento DINÂMICO em faixas de SM, conforme o ano do arquivo
    mapa_renda_do_ano = obter_mapa_renda_familiar(ano)
    df["RENDA_FAMILIAR"] = mapear_com_seguranca(df["RENDA_FAMILIAR"], mapa_renda_do_ano)

    df["TIPO_DE_ESCOLA_EM"] = mapear_com_seguranca(df["TIPO_DE_ESCOLA_EM"], MAPA_TIPO_ESCOLA_EM)

    # TP_FAIXA_ETARIA e TP_COR_RACA: convertidos para número e mapeados para texto
    df["TP_FAIXA_ETARIA"] = converter_para_inteiro_nullable(df["TP_FAIXA_ETARIA"])
    df["TP_FAIXA_ETARIA"] = mapear_com_seguranca(df["TP_FAIXA_ETARIA"], MAPA_FAIXA_ETARIA)

    df["TP_COR_RACA"] = converter_para_inteiro_nullable(df["TP_COR_RACA"])
    df["TP_COR_RACA"] = mapear_com_seguranca(df["TP_COR_RACA"], MAPA_COR_RACA)

    # POSSUI_RENDA -> tipo booleano ESTRITO ('A'->False, 'B'->True).
    # Aqui NÃO usamos o "mapeamento seguro" (que preserva valor original em
    # caso de código desconhecido), porque um código fora do padrão A/B não
    # tem como virar um bool válido — nesse caso vira <NA> (nulo), que é o
    # comportamento correto para o dtype "boolean" nullable do pandas.
    df["POSSUI_RENDA"] = df["POSSUI_RENDA"].map(MAPA_POSSUI_RENDA).astype("boolean")

    # Tipagem básica das demais colunas (mantidas com valor original, sem mapeamento)
    df["NU_ANO"] = converter_para_inteiro_nullable(df["NU_ANO"])
    df["CO_MUNICIPIO_PROVA"] = converter_para_inteiro_nullable(df["CO_MUNICIPIO_PROVA"])

    # CO_UF_PROVA: coluna REMOVIDA conforme instrução (não é lida nem mantida).

    # Reordena colunas conforme especificação
    df = df[ORDEM_FINAL_PARTICIPANTES]

    print(f"  PARTICIPANTES_{ano}: {len(df):,} linhas tratadas.".replace(",", "."))
    return df


# ----------------------------------------------------------------------------------
# 6. TRATAMENTO — TABELA RESULTADOS
# ----------------------------------------------------------------------------------
def tratar_resultados(caminho: Path, ano: int) -> pd.DataFrame:
    print(f"Carregando RESULTADOS_{ano}...")
    df = ler_csv_flexivel(caminho, usecols=COLUNAS_ORIGINAIS_RESULTADOS)

    print(f"  Mapeando colunas de RESULTADOS_{ano}...")

    # CO_UF_ESC precisa virar número antes de mapear (o dicionário usa chaves int)
    df["CO_UF_ESC"] = converter_para_inteiro_nullable(df["CO_UF_ESC"])
    df["CO_UF_ESC"] = mapear_com_seguranca(df["CO_UF_ESC"], MAPA_UF_ESC)

    df["TP_DEPENDENCIA_ADM_ESC"] = converter_para_inteiro_nullable(df["TP_DEPENDENCIA_ADM_ESC"])
    df["TP_DEPENDENCIA_ADM_ESC"] = mapear_com_seguranca(
        df["TP_DEPENDENCIA_ADM_ESC"], MAPA_DEPENDENCIA_ADM_ESC
    )

    df["TP_LOCALIZACAO_ESC"] = converter_para_inteiro_nullable(df["TP_LOCALIZACAO_ESC"])
    df["TP_LOCALIZACAO_ESC"] = mapear_com_seguranca(df["TP_LOCALIZACAO_ESC"], MAPA_LOCALIZACAO_ESC)

    df["TP_SIT_FUNC_ESC"] = converter_para_inteiro_nullable(df["TP_SIT_FUNC_ESC"])
    df["TP_SIT_FUNC_ESC"] = mapear_com_seguranca(df["TP_SIT_FUNC_ESC"], MAPA_SIT_FUNC_ESC)

    # Demais colunas: tipagem, sem mapeamento de valores (mantidas originais)
    df["NU_ANO"] = converter_para_inteiro_nullable(df["NU_ANO"])
    df["CO_MUNICIPIO_ESC"] = converter_para_inteiro_nullable(df["CO_MUNICIPIO_ESC"])
    df["CO_ESCOLA"] = converter_para_inteiro_nullable(df["CO_ESCOLA"])

    print(f"  Tratando valores nulos de RESULTADOS_{ano}...")

    # Colunas de identificação numérica da escola: NaN -> 0
    for coluna in COLUNAS_ID_ESCOLA_PREENCHER_ZERO:
        df[coluna] = df[coluna].fillna(0).astype("int64")

    # Colunas categóricas/textuais da escola: NaN -> 'Não informado'
    # (aplicado DEPOIS do mapeamento de código -> descrição feito acima)
    for coluna in COLUNAS_ESCOLA_PREENCHER_NAO_INFORMADO:
        df[coluna] = df[coluna].astype("object").fillna("Não informado")
        df[coluna] = df[coluna].replace(["", "nan", "None"], "Não informado")

    # Notas: garantir tipo float antes do cálculo da média
    colunas_notas = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
    for coluna_nota in colunas_notas:
        df[coluna_nota] = converter_para_numero(df[coluna_nota])

    print(f"  Calculando MEDIA_GERAL de RESULTADOS_{ano}...")

    # MEDIA_GERAL: média aritmética simples das 5 notas.
    # skipna=True (padrão do pandas) -> quem faltou alguma prova (NaN) tem a média
    # calculada só com as notas presentes; quem faltou a TODAS fica com NaN.
    df["MEDIA_GERAL"] = df[colunas_notas].mean(axis=1, skipna=True).round(2)

    # Reordena colunas conforme especificação
    df = df[ORDEM_FINAL_RESULTADOS]

    print(f"  RESULTADOS_{ano}: {len(df):,} linhas tratadas.".replace(",", "."))
    return df


# ----------------------------------------------------------------------------------
# 7. EXECUÇÃO PRINCIPAL
# ----------------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("INICIANDO TRATAMENTO DOS MICRODADOS DO ENEM (2024 e 2025)")
    print("=" * 70)

    # ---- PARTICIPANTES ----
    print("\n[1/2] Processando base de PARTICIPANTES...")
    dfs_participantes = []
    for ano, caminho in ARQUIVOS_PARTICIPANTES.items():
        if not caminho.exists():
            print(f"  AVISO: arquivo não encontrado, pulando -> {caminho}")
            continue
        dfs_participantes.append(tratar_participantes(caminho, ano))

    if not dfs_participantes:
        raise FileNotFoundError("Nenhum arquivo de PARTICIPANTES foi encontrado. Verifique os caminhos.")

    print("Unificando dados de PARTICIPANTES (2024 + 2025)...")
    participantes_final = pd.concat(dfs_participantes, ignore_index=True)

    print(f"Salvando '{SAIDA_PARTICIPANTES}'...")
    participantes_final.to_csv(SAIDA_PARTICIPANTES, index=False, encoding="utf-8-sig")

    # ---- RESULTADOS ----
    print("\n[2/2] Processando base de RESULTADOS...")
    dfs_resultados = []
    for ano, caminho in ARQUIVOS_RESULTADOS.items():
        if not caminho.exists():
            print(f"  AVISO: arquivo não encontrado, pulando -> {caminho}")
            continue
        dfs_resultados.append(tratar_resultados(caminho, ano))

    if not dfs_resultados:
        raise FileNotFoundError("Nenhum arquivo de RESULTADOS foi encontrado. Verifique os caminhos.")

    print("Unificando dados de RESULTADOS (2024 + 2025)...")
    resultados_final = pd.concat(dfs_resultados, ignore_index=True)

    print(f"Salvando '{SAIDA_RESULTADOS}'...")
    resultados_final.to_csv(SAIDA_RESULTADOS, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 70)
    print("CONCLUÍDO COM SUCESSO!")
    print(f"  -> {SAIDA_PARTICIPANTES}  ({len(participantes_final):,} linhas)".replace(",", "."))
    print(f"  -> {SAIDA_RESULTADOS}  ({len(resultados_final):,} linhas)".replace(",", "."))
    print("=" * 70)


if __name__ == "__main__":
    main()