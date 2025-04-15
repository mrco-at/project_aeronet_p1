import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Diretórios dos níveis de qualidade
data_dirs = {
    'lvl10': 'AOD_data_lvl10',
    'lvl15': 'AOD_data_lvl15',
    'lvl20': 'AOD_data_lvl20'
}

# Função para validar e limpar os dados
def validate_and_clean_data(file_path):
    df = pd.read_csv(file_path)
    
    # Verificar se a coluna 'Date(dd:mm:yyyy)' existe
    if 'Date(dd:mm:yyyy)' not in df.columns:
        raise ValueError("A coluna 'Date(dd:mm:yyyy)' está ausente no arquivo.")
    
    # Substituir valores -999.000000 por NaN
    df.replace(-999.000000, np.nan, inplace=True)
    
    return df

# Função para processar os dados de um diretório
def process_aeronet_data(data_dir):
    results = []

    for city_file in os.listdir(data_dir):
        city_path = os.path.join(data_dir, city_file)
        if city_file.endswith('.txt'):
            # Carregar os dados
            try:
                data = validate_and_clean_data(city_path)
                data['Date'] = pd.to_datetime(data['Date(dd:mm:yyyy)'], errors='coerce')
            except Exception as e:
                print(f"Erro ao processar o arquivo {city_file}: {e}")
                continue

            # Contar dados válidos e vazios
            valid_data_count = data.dropna().shape[0]
            empty_data_count = data.shape[0] - valid_data_count

            # Identificar períodos longos de ausência de dados (>= 1 ano)
            data = data.sort_values(by='Date')
            data['Gap'] = data['Date'].diff().dt.days
            long_gaps = data[data['Gap'] >= 365].shape[0]

            # Estatísticas descritivas
            stats = data.describe().to_dict()

            # Adicionar resultados
            results.append({
                'city': city_file.replace('.txt', ''),
                'valid_data_count': valid_data_count,
                'empty_data_count': empty_data_count,
                'long_gaps': long_gaps,
                'stats': stats
            })

    return results

# Processar os dados para cada nível de qualidade
final_results = {}
for level, directory in data_dirs.items():
    if os.path.exists(directory):
        final_results[level] = process_aeronet_data(directory)

# Exibir os resultados
for level, results in final_results.items():
    print(f"\nResultados para {level}:")
    for result in results:
        print(f"Cidade: {result['city']}")
        print(f"  Dados válidos: {result['valid_data_count']}")
        print(f"  Dados vazios: {result['empty_data_count']}")
        print(f"  Períodos longos de ausência: {result['long_gaps']}")
        print(f"  Estatísticas descritivas: {result['stats']}")