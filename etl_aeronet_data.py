# -*- coding: utf-8 -*-
"""
Created on Mon Dec  9 19:25:33 2024

@author: mgodi
"""

#%% Imports
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import chardet
import os
import gc

#%% Define Functions
def detect_file_encoding(file_path, sample_size=10000):
    """
    Detect the encoding of a file by reading a sample of its content.
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(sample_size)
        result = chardet.detect(raw_data)
        return result['encoding']

def clean_dataframes(dfs, outlier_threshold=3):
    """
    Clean DataFrames by removing outliers, replacing invalid values, and dropping empty columns.
    """
    cleaned_dfs = {}
    for file_path, df in dfs.items():
        try:
            print(f"Cleaning DataFrame for: {file_path}")

            # Remove the first row (possible metadata)
            df = df.iloc[1:].reset_index(drop=True)

            # Replace specific invalid values with NaN
            df.replace(-999, np.nan, inplace=True)

            # Identify numeric columns
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns

            # Replace outliers with NaN
            for col in numeric_cols:
                mean = df[col].mean()
                std = df[col].std()
                if std != 0:
                    outliers = (df[col] < mean - outlier_threshold * std) | (df[col] > mean + outlier_threshold * std)
                    df.loc[outliers, col] = np.nan

            # Drop columns with all NaN values
            df = df.dropna(axis=1, how='all')

            cleaned_dfs[file_path] = df
        except Exception as e:
            print(f"Error cleaning DataFrame for {file_path}: {e}")
    return cleaned_dfs

def align_dataframes_by_date(dfs, date_column="Date(dd:mm:yyyy)", time_column="Time(hh:mm:ss)"):
    """
    Align DataFrames by ensuring they have a row for each day in the global date range.
    """
    for file_path, df in dfs.items():
        # Verificar se a coluna de data existe
        if date_column not in df.columns:
            print(f"Erro: A coluna '{date_column}' não foi encontrada no arquivo '{file_path}'.")
            continue

        df[date_column] = pd.to_datetime(df[date_column], format="%d:%m:%Y", errors="coerce")
    
    # Filtrar DataFrames com dados válidos
    valid_dfs = {fp: df for fp, df in dfs.items() if date_column in df.columns and not df[date_column].isna().all()}
    if not valid_dfs:
        print("Erro: Nenhum DataFrame contém dados válidos para alinhar.")
        return {}

    min_date = min(df[date_column].min() for df in valid_dfs.values())
    max_date = max(df[date_column].max() for df in valid_dfs.values())
    print(f"Global date range: {min_date} to {max_date}")
    
    full_date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    aligned_dfs = {}
    for file_path, df in valid_dfs.items():
        df = df.drop_duplicates(subset=date_column)
        df = df.set_index(date_column)
        df_aligned = df.reindex(full_date_range)
        df_aligned[date_column] = df_aligned.index
        if time_column in df.columns:
            df_aligned[time_column] = df_aligned[time_column].fillna("12:00:00")
        df_aligned = df_aligned.reset_index(drop=True)
        aligned_dfs[file_path] = df_aligned
    
    return aligned_dfs

def plot_time_series(diction, date_column="Date(dd:mm:yyyy)"):
    """
    Plot time series for each DataFrame in the dictionary with fixed axes and aesthetic configurations.

    X-axis: 1995 to 2024
    Y-axis: 0 to 2.5
    """
    x_min = pd.to_datetime("1995-01-01")
    x_max = pd.to_datetime("2024-12-31")
    y_min = 0
    y_max = 2.5

    # Custom colors and markers
    colors = ['darkblue', 'crimson', 'orange', 'green', 'purple', 'brown', 'gold', 'teal']
    markers = ['o', 's', 'D', '^', 'v', 'P', '*', 'X']

    for file_path, df in diction.items():
        try:
            print(f"Plotting time series for {file_path}...")

            # Convert date column if necessary
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

            # Check for sparse data
            if df.dropna().shape[0] < 10:
                print(f"Warning: Sparse data for {file_path}. Plot may not be meaningful.")

            # Select specific numeric columns
            subset = df.iloc[:, 3:10].copy()

            plt.figure(figsize=(12, 6))

            for i, col in enumerate(subset.columns):
                color = colors[i % len(colors)]
                marker = markers[i % len(markers)]
                plt.scatter(
                    df[date_column], df[col],
                    label=col,
                    s=8,               # Smaller marker size
                    alpha=0.6,         # Slight transparency
                    color=color,
                    marker=marker
                )

            plt.xlim(x_min, x_max)
            plt.ylim(y_min, y_max)
            plt.title(f"Time Series - AOD - {os.path.basename(file_path)}")
            plt.xlabel("Time")
            plt.ylabel("AOD")

            # Legend outside the plot area
            plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
            plt.tight_layout()

            # Save the figure with a unique filename
            safe_filename = os.path.basename(file_path).replace(" ", "_").replace(":", "_")
            plt.savefig(f'temporal_series_{safe_filename}.png', dpi=200)
            print(f"Figure saved as: temporal_series_{safe_filename}.png")
            plt.close()  # Close the figure to avoid overlapping plots
        except Exception as e:
            print(f"Error plotting time series for {file_path}: {e}")

def identify_gaps(df, date_column="Date(dd:mm:yyyy)", start_date=None, end_date=None):
    """
    Identify gaps in the data by comparing the expected date range with the actual dates in the DataFrame.

    Parameters:
    - df: DataFrame containing the data.
    - date_column: Name of the column containing dates.
    - start_date: Start date for the analysis (optional).
    - end_date: End date for the analysis (optional).

    Returns:
    - A list of gaps, where each gap is represented as a tuple (start_date, end_date, duration_in_days).
    """
    # Convert the date column to datetime
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")

    # Filter the DataFrame to the specified date range
    if start_date:
        start_date = pd.to_datetime(start_date)
    else:
        start_date = df[date_column].min()

    if end_date:
        end_date = pd.to_datetime(end_date)
    else:
        end_date = df[date_column].max()

    # Generate the full date range
    full_date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # Identify missing dates
    actual_dates = df[date_column].dropna().unique()
    missing_dates = sorted(set(full_date_range) - set(actual_dates))

    # Group consecutive missing dates into gaps
    gaps = []
    if missing_dates:
        gap_start = missing_dates[0]
        for i in range(1, len(missing_dates)):
            if (missing_dates[i] - missing_dates[i - 1]).days > 1:
                gap_end = missing_dates[i - 1]
                gaps.append((gap_start, gap_end, (gap_end - gap_start).days + 1))
                gap_start = missing_dates[i]
        # Add the last gap
        gap_end = missing_dates[-1]
        gaps.append((gap_start, gap_end, (gap_end - gap_start).days + 1))

    return gaps

def calculate_statistics(dfs, date_column="Date(dd:mm:yyyy)"):
    """
    Calculate statistics for each DataFrame, including:
    - Number of valid and empty data points.
    - Number of long gaps (>= 1 year) in the data.
    - Descriptive statistics (mean, std, max, min, etc.).
    - Detailed gap analysis.
    """
    results = {}

    for file_path, df in dfs.items():
        print(f"Calculating statistics for: {file_path}")

        # Convert date column to datetime
        df[date_column] = pd.to_datetime(df[date_column], format="%d:%m:%Y", errors="coerce")

        # Count valid and empty data points
        valid_data_count = df.dropna().shape[0]
        empty_data_count = df.shape[0] - valid_data_count

        # Identify gaps
        gaps = identify_gaps(df, date_column)
        long_gaps = [gap for gap in gaps if gap[2] >= 365]

def generate_figures(data):
    # Certifique-se de que os dados estão no formato correto antes de gerar as figuras
    if data.empty:
        raise ValueError("Os dados fornecidos estão vazios. Não é possível gerar figuras.")
    
    # Código para gerar figuras
    # ...existing code for figure generation...

if __name__ == "__main__":
    # Exemplo de execução do script
    try:
        # Diretório contendo os arquivos de entrada
        input_dir = "AOD_data_lvl10"
        input_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".txt")]

        # Verificar se os arquivos existem
        if not input_files:
            print(f"Erro: Nenhum arquivo encontrado no diretório '{input_dir}'.")
        else:
            print(f"Arquivos encontrados: {len(input_files)}")

        # Detectar encoding e carregar os DataFrames
        dfs = {}
        for file_path in input_files:
            if os.path.exists(file_path):  # Verifique novamente antes de processar
                encoding = detect_file_encoding(file_path)
                try:
                    # Corrigir separador para vírgula e ignorar linhas de metadados
                    df = pd.read_csv(
                        file_path,
                        encoding=encoding,
                        sep=",",
                        skiprows=6  # Ignorar as 6 primeiras linhas de metadados
                    )

                    # Listar as colunas do DataFrame
                    print(f"Colunas no arquivo '{file_path}': {df.columns.tolist()}")

                    # Verificar se a coluna de data está presente
                    if "Date(dd:mm:yyyy)" not in df.columns:
                        print(f"Erro: A coluna 'Date(dd:mm:yyyy)' não foi encontrada no arquivo '{file_path}'.")
                        continue

                    dfs[file_path] = df
                except Exception as e:
                    print(f"Erro ao carregar o arquivo '{file_path}': {e}")
                    continue

        # Limpar os DataFrames
        cleaned_dfs = clean_dataframes(dfs)

        # Alinhar os DataFrames por data
        aligned_dfs = align_dataframes_by_date(cleaned_dfs, date_column="Date(dd:mm:yyyy)")

        # Plotar séries temporais
        plot_time_series(aligned_dfs, date_column="Date(dd:mm:yyyy)")

        # Calcular estatísticas
        for file_path, df in aligned_dfs.items():
            stats = calculate_statistics({file_path: df}, date_column="Date(dd:mm:yyyy)")
            print(f"Estatísticas para {file_path}: {stats}")

    except Exception as e:
        print(f"Erro ao executar o script: {e}")



