# -*- coding: utf-8 -*-
"""
Created on Mon Dec  9 19:25:33 2024

@author: mgodi
"""

#%%
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import chardet
#%%
# Caminho do arquivo
file_paths = [
    '/home/mgodi/Documentos/inbox_acad/colaboracoes_pessoas/marinete/'
    'cpam_aerosol/dezembro/data/19990101_20241231_CEILAP-BA.lev15',
    '/home/mgodi/Documentos/inbox_acad/colaboracoes_pessoas/marinete/'
    'cpam_aerosol/dezembro/data/20000101_20241231_Rio_Branco.lev15',
    '/home/mgodi/Documentos/inbox_acad/colaboracoes_pessoas/marinete/'
    'cpam_aerosol/dezembro/data/20000101_20241231_Sao_Paulo.lev15',
    '/home/mgodi/Documentos/inbox_acad/colaboracoes_pessoas/marinete/'
    'cpam_aerosol/dezembro/data/20010101_20241231_CUIABA-MIRANDA.lev15',
    '/home/mgodi/Documentos/inbox_acad/colaboracoes_pessoas/marinete/'
    'cpam_aerosol/dezembro/data/20080101_20171231_Sao_Martinho_SONDA.lev15',
]
#%%
# Função para detectar a codificação de um arquivo
def detect_file_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result['encoding']

# Função para pré-processar e validar o DataFrame
def preprocess_and_validate(file_path):
    df = pd.read_csv(file_path)
    
    # Verificar se a coluna 'Date(dd:mm:yyyy)' existe
    if 'Date(dd:mm:yyyy)' not in df.columns:
        raise ValueError("A coluna 'Date(dd:mm:yyyy)' está ausente no arquivo.")
    
    # Substituir valores -999.000000 por NaN
    df.replace(-999.000000, np.nan, inplace=True)
    
    return df

# Processar múltiplos arquivos
dfs = {}
problematic_files = []

for file_path in file_paths:
    try:
        # Detectar a codificação
        encoding = detect_file_encoding(file_path)
        print(f"Arquivo: {file_path}, Codificação detectada: {encoding}")

        # Localizar a linha do cabeçalho
        header_line = None
        column_names = None
        with open(file_path, 'r', encoding=encoding) as file:
            for i, line in enumerate(file):
                if "Date(dd:mm:yyyy)" in line:  # Adapte o critério de detecção se necessário
                    header_line = i
                    column_names = line.strip().split(",")
                    print(f"Linha do cabeçalho encontrada: {header_line}")
                    print(f"Nomes das colunas: {column_names}")
                    break

        if header_line is None:
            raise ValueError("Linha do cabeçalho não encontrada")

        # Garantir nomes de colunas únicos
        column_name_counts = Counter(column_names)
        unique_column_names = []
        for name in column_names:
            count = column_name_counts[name]
            if count > 1:
                new_name = f"{name}_{column_name_counts[name]}"
                column_name_counts[name] -= 1
            else:
                new_name = name
            unique_column_names.append(new_name)

        # Ler o arquivo em um DataFrame
        with open(file_path, 'r', encoding=encoding) as file:
            df = pd.read_csv(
                file,
                skiprows=header_line,
                names=unique_column_names,
                comment='#'
            ).reset_index(drop=True)

        # Converter colunas para numéricas
        for col in df.columns:
            if col not in ["Date(dd:mm:yyyy)", "Time(hh:mm:ss)"]:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        dfs[file_path] = df
        print(f"Arquivo {file_path} processado com sucesso.")

    except Exception as e:
        print(f"Erro ao processar o arquivo {file_path}: {e}")
        problematic_files.append(file_path)

print(f"Arquivos com problemas: {problematic_files}")
#%%
# Display .info() for each DataFrame in the `dfs` dictionary
for file_path, df in dfs.items():
    print(f"Info for {file_path}:")
    df.info()
    print("\n" + "="*50 + "\n")
#%%
def clean_dataframes(dfs, outlier_threshold=3):
    """
    Limpa os DataFrames de um dicionário substituindo valores nulos/outliers, removendo colunas vazias
    e descartando a primeira linha (possível metadado residual).

    Args:
    dfs (dict): Dicionário contendo os DataFrames a serem limpos.
    outlier_threshold (int): Número de desvios padrão para identificar outliers.

    Returns:
    dict: Dicionário com os DataFrames limpos.
    """
    cleaned_dfs = {}
    for file_path, df in dfs.items():
        print(f"Processando: {file_path}")
        
        # Remover a primeira linha (possível metadado residual)
        df = df.iloc[1:].reset_index(drop=True)
        
        # Substituir valores específicos como -999 por NaN
        df.replace(-999, np.nan, inplace=True)
        
        # Identificar colunas numéricas
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        # Substituir outliers (> outlier_threshold * std) por NaN
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std != 0:  # Evitar divisão por zero
                outliers = (df[col] < mean - outlier_threshold * std) | (df[col] > mean + outlier_threshold * std)
                df.loc[outliers, col] = np.nan
        
        # Remover colunas com todos os valores NaN
        before_cols = df.shape[1]
        df = df.dropna(axis=1, how='all')
        after_cols = df.shape[1]
        removed_cols = before_cols - after_cols
        print(f"Colunas removidas (todas NaN): {removed_cols}")
        
        # Manter colunas com poucos valores NaN para avaliação
        remaining_nan_cols = df.columns[df.isnull().any()]
        print(f"Colunas com valores NaN restantes: {list(remaining_nan_cols)}")
        
        cleaned_dfs[file_path] = df
        
    return cleaned_dfs

# Aplicar a limpeza nos DataFrames
cleaned_dfs = clean_dataframes(dfs)

# Visualizar as estatísticas de cada DataFrame limpo
for file_path, df in cleaned_dfs.items():
    print(f"Estatísticas após limpeza para {file_path}:")
    print(df.describe())
    print("\n")


#%%
def align_dataframes_by_date(dfs, date_column="Date(dd:mm:yyyy)", time_column="Time(hh:mm:ss)"):
    """
    Alinha todos os DataFrames para garantir que tenham uma linha para cada dia
    dentro do intervalo de datas mínimo e máximo entre todos os DataFrames.
    
    Args:
    dfs (dict): Dicionário contendo os DataFrames a serem alinhados.
    date_column (str): Nome da coluna de data.
    time_column (str): Nome da coluna de tempo.
    
    Returns:
    dict: Dicionário com DataFrames alinhados.
    """
    # Filtrar DataFrames vazios
    non_empty_dfs = {file_path: df for file_path, df in dfs.items() if not df.empty}
    if not non_empty_dfs:
        raise ValueError("Todos os DataFrames estão vazios. Não é possível alinhar os dados.")

    # Converter a coluna de data para datetime
    for file_path, df in non_empty_dfs.items():
        df[date_column] = pd.to_datetime(df[date_column], format="%d:%m:%Y", errors="coerce")
    
    # Encontrar o intervalo de datas global
    min_date = min(df[date_column].min() for df in non_empty_dfs.values())
    max_date = max(df[date_column].max() for df in non_empty_dfs.values())
    print(f"Intervalo global de datas: {min_date} a {max_date}")
    
    # Criar um índice contínuo de datas
    full_date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    aligned_dfs = {}
    for file_path, df in non_empty_dfs.items():
        print(f"Alinhando: {file_path}")
        
        # Remover duplicatas no índice
        df = df.drop_duplicates(subset=date_column)
        
        # Redefinir o índice para a data
        df = df.set_index(date_column)
        
        # Reindexar para incluir todas as datas no intervalo
        df_aligned = df.reindex(full_date_range)
        
        # Restaurar a coluna de data
        df_aligned[date_column] = df_aligned.index
        
        # Preencher a coluna de tempo com valores padrão, se estiver vazia
        if time_column in df.columns:
            df_aligned[time_column] = df_aligned[time_column].fillna("12:00:00")
        
        # Resetar o índice para restaurar a estrutura original
        df_aligned = df_aligned.reset_index(drop=True)
        
        aligned_dfs[file_path] = df_aligned
    
    return aligned_dfs

# Aplicar o alinhamento
aligned_dfs = align_dataframes_by_date(cleaned_dfs)

# Verificar as dimensões e amostras após o alinhamento
for file_path, df in aligned_dfs.items():
    print(f"{file_path}: {df.shape}")
    print(df.head())


#%%
# Display .info() for each DataFrame in the `dfs` dictionary
for file_path, df in aligned_dfs.items():
    print(f"Info for {file_path}:")
    df.info()
    print("\n" + "="*50 + "\n")
#%%
import seaborn as sns
import matplotlib.pyplot as plt

def plot_scatter_matrix(dataframes, numeric_columns_per_plot=4):
    """
    Plota gráficos de dispersão em uma matriz scatterplot dividida em grupos de colunas numéricas.
    
    Args:
    dataframes (dict): Dicionário com DataFrames a serem plotados.
    numeric_columns_per_plot (int): Número de colunas numéricas por scatterplot matrix.
    """
    for file_path, df in dataframes.items():
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        print(f"Plotando scatterplot matrix para {file_path}...")
        
        # Dividir as colunas numéricas em grupos menores
        for i in range(3, 7, numeric_columns_per_plot):
            subset_columns = numeric_columns[i:i + numeric_columns_per_plot]
            if len(subset_columns) > 1:
                sns.pairplot(df, vars=subset_columns)
                plt.suptitle(f"Scatterplot Matrix - {file_path[-25:-6]}\n{', '.join(subset_columns)}", y=1.02)
                plt.show()

def plot_time_series(dataframes, date_column="Date(dd:mm:yyyy)", numeric_columns_per_plot=4):
    """
    Plota gráficos de linha para as séries temporais de cada coluna numérica.
    
    Args:
    dataframes (dict): Dicionário com DataFrames a serem plotados.
    date_column (str): Nome da coluna de data.
    numeric_columns_per_plot (int): Número de colunas numéricas por gráfico de linha.
    """
    for file_path, df in dataframes.items():
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        print(f"Plotando gráficos de linha para {file_path[-25:-6]}...")
        
        #for i in range(0, len(numeric_columns), numeric_columns_per_plot):
        for i in range(3, 7, numeric_columns_per_plot):
            subset_columns = numeric_columns[i:i + numeric_columns_per_plot]
            plt.figure(figsize=(12, 6))
            for col in subset_columns:
                plt.plot(df[date_column], df[col], label=col)
            plt.title(f"Séries Temporais - {file_path[-25:-6]}\n{', '.join(subset_columns)}")
            plt.xlabel("Data")
            plt.ylabel("Valor")
            plt.legend()
            plt.tight_layout()
            plt.show()

# Plotar scatterplot matrix e séries temporais para os DataFrames alinhados
plot_scatter_matrix(aligned_dfs, numeric_columns_per_plot=4)
plot_time_series(aligned_dfs, date_column="Date(dd:mm:yyyy)", numeric_columns_per_plot=4)
#%% teste
import matplotlib.pyplot as plt
import pandas as pd

def plot_time_series(diction, date_column="Date(dd:mm:yyyy)"):
    """
    Plota gráficos de linha para as séries temporais com eixos fixos.

    Eixo X: 1990 a 2024
    Eixo Y: 0 a 2.5
    """
    x_min = pd.to_datetime("2000-01-01")
    x_max = pd.to_datetime("2024-12-31")
    y_min = 0
    y_max = 2.5

    for file_path, df in diction.items():
        print(f"Plotando gráficos de linha para {file_path[-25:-6]}...")

        # Converte coluna de data, se necessário
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

        # Seleciona colunas numéricas específicas
        subset = df.iloc[:, 3:10].copy()  # Ajuste esse intervalo conforme necessário

        plt.figure(figsize=(12, 6))
        for col in subset.columns:
            plt.plot(df[date_column], df[col], label=col)

        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)
        plt.title(f"Temporal Series - AOD - {file_path[-25:-6]}")
        plt.xlabel("Date")
        plt.ylabel("AOD")

        # Legenda fora da área do gráfico
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))  # fora à direita
        plt.tight_layout()
        plt.savefig(f'temporal_series_{file_path[-25:-6]}.png',dpi=200)
        plt.show()
#for name, x in aligned_dfs.items():
plot_time_series(aligned_dfs, date_column="Date(dd:mm:yyyy)")
#%%
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

def plot_time_series(diction, date_column="Date(dd:mm:yyyy)"):
    """
    Plota gráficos de dispersão para as séries temporais com eixos fixos.
    Eixo X: 2000 a 2024
    Eixo Y: 0 a 2.5
    """
    x_min = pd.to_datetime("2000-01-01")
    x_max = pd.to_datetime("2024-12-31")
    y_min = 0
    y_max = 2.5

    for file_path, df in diction.items():
        print(f"Plotando gráficos de linha para {file_path[-25:-6]}...")

        # Converte coluna de data, se necessário
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

        # Seleciona colunas numéricas específicas
        subset = df.iloc[:, 3:10].copy()  # Ajuste conforme necessário

        plt.figure(figsize=(12, 6))

        # Cores diferentes para cada série
        colors = plt.get_cmap('tab10').colors  # outras opções: 'Set1', 'Dark2', etc.

        for i, col in enumerate(subset.columns):
            plt.scatter(df[date_column], df[col], label=col, s=10, color=colors[i % len(colors)])  # s=10 ajusta o tamanho do ponto

        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)
        plt.title(f"Temporal Series - AOD - {file_path[-25:-6]}")
        plt.xlabel("Date")
        plt.ylabel("AOD")

        # Legenda fora da área do gráfico
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
        plt.tight_layout()
        plt.savefig(f'temporal_series_{file_path[-25:-6]}.png', dpi=200)
        plt.show()
plot_time_series(aligned_dfs, date_column="Date(dd:mm:yyyy)")
#%%
import pandas as pd
import matplotlib.pyplot as plt

def plot_time_series(diction, date_column="Date(dd:mm:yyyy)"):
    """
    Plota gráficos de dispersão para as séries temporais com eixos fixos.
    Eixo X: 2000 a 2024
    Eixo Y: 0 a 2.5
    """
    x_min = pd.to_datetime("2000-01-01")
    x_max = pd.to_datetime("2024-12-31")
    y_min = 0
    y_max = 2.2

    # Lista de cores e marcadores personalizados
    cores = ['darkblue', 'crimson', 'orange', 'green', 'purple', 'brown', 'gold', 'teal']
    marcadores = ['o', 's', 'D', '^', 'v', 'P', '*', 'X']

    for file_path, df in diction.items():
        print(f"Plotando gráfico de dispersão para {file_path[-25:-6]}...")

        # Converte coluna de data, se necessário
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

        # Seleciona colunas numéricas específicas
        subset = df.iloc[:, 3:10].copy()

        plt.figure(figsize=(12, 6))

        for i, col in enumerate(subset.columns):
            cor = cores[i % len(cores)]
            marcador = marcadores[i % len(marcadores)]
            plt.scatter(
                df[date_column], df[col],
                label=col,
                s=8,               # Tamanho do marcador menor
                alpha=0.6,         # Transparência leve
                color=cor,
                marker=marcador
            )

        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)
        plt.title(f"Time Series - AOD - {file_path[-25:-6]}")
        plt.xlabel("Time")
        plt.ylabel("AOD")

        # Legenda fora da área do gráfico
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
        plt.tight_layout()
        plt.savefig(f'temporal_series_{file_path[-25:-6]}.png', dpi=200)
        plt.show()

plot_time_series(aligned_dfs, date_column="Date(dd:mm:yyyy)")