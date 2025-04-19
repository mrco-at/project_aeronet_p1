#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para calcular a disponibilidade de dias representativos de AOD_500
em cada cidade e nível de qualidade.
"""

import os
import logging
import pandas as pd
from map_utils import calculate_all_stations_availability
from visualizer import AeronetVisualizer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('availability_calculation.log'),
        logging.StreamHandler()
    ]
)

def generate_availability_report(results, output_dir='output'):
    """
    Gera um relatório de disponibilidade em formato CSV.
    
    Args:
        results: Dicionário com resultados da disponibilidade
        output_dir: Diretório para salvar o relatório
    """
    # Criar diretório de saída se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    # Preparar dados para o DataFrame
    data = []
    
    for station, station_data in results.items():
        # Extrair informações espaciais se disponíveis
        latitude = station_data.get('latitude', None)
        longitude = station_data.get('longitude', None)
        elevation = station_data.get('elevation', None)
        
        for level, stats in station_data.items():
            if level.startswith('level'):
                data.append({
                    'Estação': station,
                    'Latitude': latitude,
                    'Longitude': longitude,
                    'Elevação (m)': elevation,
                    'Nível': level,
                    'Total de Dias Possíveis': stats['total_possible_days'],
                    'Total de Dias com Dados': stats['total_days'],
                    'Dias Representativos': stats['representative_days'],
                    'Dias Representativos (% dos dias com dados)': stats['representative_days_percentage'],
                    'Dias Representativos (% do período total)': stats['representative_days_percentage_total'],
                    'Média de Medições/Dia': stats['avg_measurements_per_day'],
                    'Mínimo de Medições/Dia': stats['min_measurements_per_day'],
                    'Máximo de Medições/Dia': stats['max_measurements_per_day'],
                    'Total de Medições': stats['total_measurements'],
                    'Data Inicial': stats['start_date'],
                    'Data Final': stats['end_date'],
                    'Período de Cobertura (dias)': stats['data_coverage_days']
                })
    
    # Criar DataFrame
    df = pd.DataFrame(data)
    
    # Ordenar por estação e nível
    df = df.sort_values(['Estação', 'Nível'])
    
    # Salvar relatório
    output_file = os.path.join(output_dir, 'availability_report.csv')
    df.to_csv(output_file, index=False)
    logging.info(f"Relatório salvo em: {output_file}")
    
    # Imprimir resumo
    print("\n=== RESUMO DE DISPONIBILIDADE ===")
    print(f"Total de estações analisadas: {len(df['Estação'].unique())}")
    
    # Calcular médias por nível
    for level in ['level10', 'level15', 'level20']:
        level_data = df[df['Nível'] == level]
        if not level_data.empty:
            avg_percentage_data = level_data['Dias Representativos (% dos dias com dados)'].mean()
            avg_percentage_total = level_data['Dias Representativos (% do período total)'].mean()
            print(f"\nNível {level}:")
            print(f"  {len(level_data)} estações")
            print(f"  Média em relação aos dias com dados: {avg_percentage_data:.2f}%")
            print(f"  Média em relação ao período total: {avg_percentage_total:.2f}%")
    
    # Identificar estações com melhor disponibilidade
    print("\n=== ESTAÇÕES COM MELHOR DISPONIBILIDADE ===")
    for level in ['level10', 'level15', 'level20']:
        level_data = df[df['Nível'] == level]
        if not level_data.empty:
            print(f"\nTop 5 estações no nível {level} (em relação ao período total):")
            top_stations = level_data.nlargest(5, 'Dias Representativos (% do período total)')
            for _, row in top_stations.iterrows():
                print(f"  {row['Estação']}:")
                print(f"    - Em relação aos dias com dados: {row['Dias Representativos (% dos dias com dados)']:.2f}%")
                print(f"    - Em relação ao período total: {row['Dias Representativos (% do período total)']:.2f}%")
                print(f"    - Dias com dados: {row['Total de Dias com Dados']}")
                print(f"    - Período: {row['Data Inicial'].strftime('%Y-%m-%d')} a {row['Data Final'].strftime('%Y-%m-%d')}")

def main():
    """Função principal."""
    logging.info("Iniciando cálculo de disponibilidade...")
    
    # Calcular disponibilidade para todas as estações
    results = calculate_all_stations_availability(min_measurements_per_day=8)
    
    # Gerar relatório
    generate_availability_report(results)
    
    # Criar visualizações
    visualizer = AeronetVisualizer(output_dir=OUTPUT_DIR)
    
    # Gerar gráficos de comparação
    comparison_plot = visualizer.plot_availability_comparison(results, min_days=30)
    if comparison_plot:
        logging.info(f"Gráfico de comparação salvo em: {comparison_plot}")
    
    # Gerar mapas de disponibilidade para cada nível
    for level in ['level10', 'level15', 'level20']:
        spatial_plot = visualizer.plot_spatial_availability(results, level)
        if spatial_plot:
            logging.info(f"Mapa de disponibilidade para {level} salvo em: {spatial_plot}")
    
    logging.info("Cálculo de disponibilidade concluído.")

if __name__ == "__main__":
    main() 