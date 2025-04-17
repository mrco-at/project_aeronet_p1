#--------------------------------------------------------------
# %% importações
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import chardet
import matplotlib.pyplot as plt  # Importar biblioteca para gráficos

#--------------------------------------------------------------
# %% Diretórios dos níveis de qualidade
data_dirs = {
    'lvl10': 'AOD_data_lvl10',
    'lvl15': 'AOD_data_lvl15',
    'lvl20': 'AOD_data_lvl20'
}

#--------------------------------------------------------------
# %% Função para validar e limpar os dados
def validate_and_clean_data(file_path):
    """
    Validate and clean the data by handling encodings, skipping metadata rows, and ensuring required columns exist.
    """
    try:
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
            encoding = chardet.detect(raw_data)['encoding']

        # Log encoding detection
        print(f"Processando arquivo: {file_path} | Codificação detectada: {encoding}")

        # Check if the file has only one line (no data available)
        with open(file_path, 'r', encoding=encoding if encoding else 'utf-8') as f:
            lines = f.readlines()
            if len(lines) <= 1:
                print(f"Arquivo ignorado (sem dados): {file_path}")
                return None

        # Load the data with fixed separator and correct header row
        df = pd.read_csv(
            file_path,
            encoding=encoding if encoding else 'utf-8',  # Use utf-8 as fallback
            sep=",",  # Assuming comma as the separator
            header=5,  # Correct header row (6th line, index 5)
            low_memory=False  # Avoid dtype warnings for large files
        )

        # Check if the file contains data
        if df.empty:
            raise ValueError(f"O arquivo {file_path} está vazio ou não contém dados válidos.")

        # Log the first few rows for debugging
        print(f"Primeiras linhas do arquivo {file_path}:\n{df.head()}")

        # Check if the required columns exist
        required_columns = ['Date(dd:mm:yyyy)', 'AOD_500nm']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"A coluna '{col}' está ausente no arquivo {file_path}.")

        # Replace invalid values with NaN
        df.replace(-999.000000, np.nan, inplace=True)

        return df
    except Exception as e:
        raise ValueError(f"Erro ao processar o arquivo {file_path}: {e}")

#--------------------------------------------------------------
# %% Função para processar os dados de um diretório
def process_aeronet_data(data_dir):
    """
    Process all files in a directory, validate and clean them, and compute data availability.
    """
    results = []
    all_cities_data = []  # Store data for all cities
    error_log = []  # Log errors for debugging
    frequency_distributions = {}  # Store frequency distributions for each city

    for city_file in os.listdir(data_dir):
        city_path = os.path.join(data_dir, city_file)
        if city_file.endswith('.txt'):
            try:
                # Validate and clean the data
                data = validate_and_clean_data(city_path)
                if data is None:  # Skip files with no data
                    continue

                data['Date'] = pd.to_datetime(data['Date(dd:mm:yyyy)'], format='%d:%m:%Y', errors='coerce')

                # Filter data within the period 1995-2024
                data = data[(data['Date'] >= '1995-01-01') & (data['Date'] <= '2024-12-31')]

                # Group by date and count valid measurements per day
                daily_counts = data.groupby('Date')['AOD_500nm'].apply(lambda x: x.dropna().count())

                # Define a day as valid if it has at least 30% of 24 measurements (i.e., 8 measurements)
                valid_days = daily_counts[daily_counts >= 8].index

                # Calculate the total number of days in the period
                total_days = (datetime(2024, 12, 31) - datetime(1995, 1, 1)).days + 1

                # Calculate the percentage of valid days
                valid_days_percentage = (len(valid_days) / total_days) * 100

                # Store data for all cities
                all_cities_data.append({
                    'city': city_file.replace('.txt', ''),
                    'valid_days_count': len(valid_days),
                    'valid_days_percentage': valid_days_percentage
                })

                # Store frequency distribution of valid measurements per day
                frequency_distributions[city_file.replace('.txt', '')] = daily_counts.value_counts().sort_index()

                # Check if the station has at least 30% of valid days
                if valid_days_percentage >= 30:
                    results.append({
                        'city': city_file.replace('.txt', ''),
                        'valid_days_count': len(valid_days),
                        'valid_days_percentage': valid_days_percentage
                    })
            except Exception as e:
                error_log.append(f"{city_file}: {e}")

    # Display error log
    if error_log:
        print("\nLog de erros:")
        for error in error_log:
            print(error)

    return results, all_cities_data, frequency_distributions

#--------------------------------------------------------------
# %% Processar os dados para cada nível de qualidade
final_results = {}
all_cities_results = {}
frequency_distributions_results = {}
for level, directory in data_dirs.items():
    if os.path.exists(directory):
        print(f"\nProcessando dados para o nível: {level}")
        results, all_cities_data, frequency_distributions = process_aeronet_data(directory)
        final_results[level] = results
        all_cities_results[level] = all_cities_data
        frequency_distributions_results[level] = frequency_distributions

# Exibir os resultados
for level, results in final_results.items():
    print(f"\nResultados para {level}:")
    if results:
        for result in results:
            print(f"Cidade: {result['city']}")
            print(f"  Dias válidos: {result['valid_days_count']}")
            print(f"  Percentual de dias válidos: {result['valid_days_percentage']:.2f}%")
    else:
        print("Nenhuma cidade atendeu ao critério de disponibilidade.")

# Exibir os dados de todas as cidades
print("\nResumo de todas as cidades (independente do critério):")
for level, cities_data in all_cities_results.items():
    print(f"\nDados para {level}:")
    for city_data in cities_data:
        print(f"Cidade: {city_data['city']}")
        print(f"  Dias válidos: {city_data['valid_days_count']}")
        print(f"  Percentual de dias válidos: {city_data['valid_days_percentage']:.2f}%")

# Exibir a distribuição de frequência de valores válidos por dia
print("\nDistribuição de frequência de valores válidos por dia:")
for level, distributions in frequency_distributions_results.items():
    print(f"\nDistribuições para {level}:")
    level_data = []  # Acumular dados de todas as cidades para o nível
    for city, distribution in distributions.items():
        print(f"Cidade: {city}")
        print(distribution)

        # Gerar gráfico para a distribuição de frequência
        plt.figure(figsize=(10, 6))
        distribution.plot(kind='bar', color='skyblue', edgecolor='black')
        title = f"Distribuição de Frequência - {city} ({level})"
        plt.title("\n".join(title.split(" - ")), fontsize=14)  # Quebra o título em múltiplas linhas
        plt.xlabel("Número de Medições Válidas por Dia", fontsize=12)
        plt.ylabel("Frequência", fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Salvar o gráfico como imagem
        output_dir = "frequency_distribution_plots"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f"{city}_{level}_frequency_distribution.png"))
        plt.close()

        print(f"Gráfico salvo em: {os.path.join(output_dir, f'{city}_{level}_frequency_distribution.png')}")

        # Adicionar dados para o boxplot da cidade
        level_data.extend(distribution.index.repeat(distribution.values))

        # Gerar boxplot para a cidade
        plt.figure(figsize=(8, 5))
        plt.boxplot(distribution.index.repeat(distribution.values), vert=False, patch_artist=True, boxprops=dict(facecolor='lightblue'))
        title = f"Boxplot - {city} ({level})"
        plt.title("\n".join(title.split(" - ")), fontsize=14)  # Quebra o título em múltiplas linhas
        plt.xlabel("Número de Medições Válidas por Dia", fontsize=12)
        plt.tight_layout()

        # Salvar o boxplot como imagem
        plt.savefig(os.path.join(output_dir, f"{city}_{level}_boxplot.png"))
        plt.close()

        print(f"Boxplot salvo em: {os.path.join(output_dir, f'{city}_{level}_boxplot.png')}")

    # Gerar boxplot acumulado para o nível
    if level_data:
        plt.figure(figsize=(8, 5))
        plt.boxplot(level_data, vert=False, patch_artist=True, boxprops=dict(facecolor='lightgreen'))
        title = f"Boxplot Acumulado - {level}"
        plt.title("\n".join(title.split(" - ")), fontsize=14)  # Quebra o título em múltiplas linhas
        plt.xlabel("Número de Medições Válidas por Dia", fontsize=12)
        plt.tight_layout()

        # Salvar o boxplot acumulado como imagem
        plt.savefig(os.path.join(output_dir, f"{level}_cumulative_boxplot.png"))
        plt.close()

        print(f"Boxplot acumulado salvo em: {os.path.join(output_dir, f'{level}_cumulative_boxplot.png')}")

#--------------------------------------------------------------
# %% Análise considerando o universo total de dias com medidas válidas
print("\nAnálise do universo total de dias com medidas válidas:")
representative_days_results = {}
for level, distributions in frequency_distributions_results.items():
    print(f"\nAnálise para {level}:")
    level_representative_days = []  # Acumular dados de dias representativos para o nível
    level_representative_percentages = []  # Acumular percentuais de dias representativos para o nível
    for city, distribution in distributions.items():
        # Calcular o segundo quartil (mediana) da frequência de dados válidos diários
        second_quartil = pd.Series(distribution.index.repeat(distribution.values)).quantile(0.5)
        print(f"Cidade: {city} | Segundo quartil: {second_quartil}")

        # Determinar dias representativos (frequência >= segundo quartil)
        representative_days = distribution[distribution.index >= second_quartil].sum()
        total_days = (datetime(2024, 12, 31) - datetime(1995, 1, 1)).days + 1
        representative_days_percentage = (representative_days / total_days) * 100

        print(f"  Dias representativos: {representative_days}")
        print(f"  Percentual de dias representativos: {representative_days_percentage:.2f}%")

        # Adicionar dados para o gráfico de barras e boxplot
        level_representative_days.append(representative_days)
        level_representative_percentages.append(representative_days_percentage)

        # Gerar gráfico de barras com dois eixos Y
        fig, ax1 = plt.subplots(figsize=(8, 5))

        # Eixo Y para valores absolutos
        ax1.bar(["Dias Representativos"], [representative_days], color='orange', edgecolor='black', label="Absoluto")
        ax1.set_ylabel("Dias Representativos (Absoluto)", fontsize=12, color='orange')
        ax1.tick_params(axis='y', labelcolor='orange')

        # Eixo Y secundário para percentuais
        ax2 = ax1.twinx()
        ax2.bar(["Dias Representativos (%)"], [representative_days_percentage], color='blue', edgecolor='black', label="Percentual")
        ax2.set_ylabel("Dias Representativos (%)", fontsize=12, color='blue')
        ax2.tick_params(axis='y', labelcolor='blue')

        # Ajustar título para evitar cortes
        title = f"Dias Representativos - {city} ({level})"
        plt.title("\n".join(title.split(" - ")), fontsize=14)  # Quebra o título em múltiplas linhas
        fig.tight_layout()

        # Salvar o gráfico como imagem
        output_dir = "representative_days_plots"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(os.path.join(output_dir, f"{city}_{level}_representative_days_dual_axis_bar.png"))
        plt.close()

        print(f"Gráfico de barras com dois eixos Y salvo em: {os.path.join(output_dir, f'{city}_{level}_representative_days_dual_axis_bar.png')}")

    # Gerar boxplot acumulado para o nível (dias representativos absolutos)
    if level_representative_days:
        plt.figure(figsize=(8, 5))
        plt.boxplot(level_representative_days, vert=False, patch_artist=True, boxprops=dict(facecolor='lightcoral'))
        title = f"Boxplot de Dias Representativos (Absoluto) - {level}"
        plt.title("\n".join(title.split(" - ")), fontsize=14)  # Quebra o título em múltiplas linhas
        plt.xlabel("Número de Dias Representativos", fontsize=12)
        plt.tight_layout()

        # Salvar o boxplot acumulado como imagem
        plt.savefig(os.path.join(output_dir, f"{level}_representative_days_boxplot_absolute.png"))
        plt.close()

        print(f"Boxplot acumulado (absoluto) salvo em: {os.path.join(output_dir, f'{level}_representative_days_boxplot_absolute.png')}")

    # Gerar boxplot acumulado para o nível (percentuais de dias representativos)
    if level_representative_percentages:
        plt.figure(figsize=(8, 5))
        plt.boxplot(level_representative_percentages, vert=False, patch_artist=True, boxprops=dict(facecolor='lightgreen'))
        title = f"Boxplot de Dias Representativos (%) - {level}"
        plt.title("\n".join(title.split(" - ")), fontsize=14)  # Quebra o título em múltiplas linhas
        plt.xlabel("Percentual de Dias Representativos", fontsize=12)
        plt.tight_layout()

        # Salvar o boxplot acumulado como imagem
        plt.savefig(os.path.join(output_dir, f"{level}_representative_days_boxplot_percentage.png"))
        plt.close()

        print(f"Boxplot acumulado (%) salvo em: {os.path.join(output_dir, f'{level}_representative_days_boxplot_percentage.png')}")

#--------------------------------------------------------------
# %% FIM