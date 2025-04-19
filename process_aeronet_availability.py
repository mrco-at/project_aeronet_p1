#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para processar dados AERONET e gerar figuras de disponibilidade.
"""

import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
from config import (
    START_DATE,
    END_DATE,
    MIN_AVAILABILITY_PERCENTAGE,
    THRESHOLD_MULTIPLIER,
    MIN_MEASUREMENTS_PER_DAY
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aeronet_processing.log'),
        logging.StreamHandler()
    ]
)

class AeronetProcessor:
    """Classe para processar dados AERONET e gerar visualizações."""
    
    def __init__(self, 
                 data_dirs: Dict[str, str] = {
                     'level10': 'AOD_data_lvl10',
                     'level15': 'AOD_data_lvl15',
                     'level20': 'AOD_data_lvl20'
                 },
                 output_dir: str = 'output',
                 min_measurements_per_day: int = 8,
                 threshold_multiplier: float = 1.5,
                 start_year: int = 1995,
                 end_year: int = 2024):
        """
        Inicializa o processador de dados AERONET.
        
        Args:
            data_dirs: Dicionário com diretórios de dados para cada nível
            output_dir: Diretório para salvar as saídas
            min_measurements_per_day: Número mínimo de medições por dia
            threshold_multiplier: Multiplicador para o limiar dinâmico
            start_year: Ano inicial para análise
            end_year: Ano final para análise
        """
        self.data_dirs = data_dirs
        self.output_dir = output_dir
        self.min_measurements_per_day = min_measurements_per_day
        self.threshold_multiplier = threshold_multiplier
        self.start_year = start_year
        self.end_year = end_year
        
        # Criar diretório de saída
        os.makedirs(output_dir, exist_ok=True)
        
        # Calcular período total
        self.start_date = datetime(start_year, 1, 1)
        self.end_date = datetime(end_year, 12, 31)
        self.total_days = (self.end_date - self.start_date).days + 1
    
    def read_aod_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Lê dados AOD de um arquivo.
        
        Args:
            file_path: Caminho para o arquivo de dados
            
        Returns:
            DataFrame com os dados processados ou None se houver erro
        """
        try:
            # Encontrar linha do cabeçalho
            with open(file_path, 'r') as f:
                lines = f.readlines()
                header_line = None
                for i, line in enumerate(lines):
                    if 'Date' in line and 'AOD' in line:
                        header_line = i
                        break
                
                if header_line is None:
                    logging.warning(f"Linha de cabeçalho não encontrada em {file_path}")
                    return None
            
            # Ler dados a partir da linha do cabeçalho
            df = pd.read_csv(file_path, skiprows=header_line, delimiter=',')
            
            # Encontrar colunas de data e AOD 500nm
            date_col = [col for col in df.columns if 'Date' in col][0]
            aod_col = [col for col in df.columns if 'AOD_500' in col][0]
            
            # Converter data e AOD para formatos apropriados
            df[date_col] = pd.to_datetime(df[date_col], format='%d:%m:%Y', errors='coerce')
            df[aod_col] = pd.to_numeric(df[aod_col], errors='coerce')
            
            # Remover linhas com datas ou valores AOD inválidos
            df = df.dropna(subset=[date_col, aod_col])
            df = df[df[aod_col] != -999.000000]
            
            # Manter apenas colunas relevantes e renomear
            df = df[[date_col, aod_col]]
            df.columns = ['date', 'aod_500nm']
            
            return df
            
        except Exception as e:
            logging.error(f"Erro ao ler arquivo {file_path}: {str(e)}")
            return None
    
    def calculate_availability(self, df: pd.DataFrame) -> Dict:
        """
        Calcula estatísticas de disponibilidade para um DataFrame.
        
        Args:
            df: DataFrame com dados AOD
            
        Returns:
            Dicionário com estatísticas de disponibilidade
        """
        if df is None or df.empty:
            return None
        
        # Filtrar dados dentro do período
        mask = (df['date'].dt.year >= self.start_year) & (df['date'].dt.year <= self.end_year)
        df = df[mask].copy()
        
        if df.empty:
            return None
        
        # Agrupar por data e contar medições
        daily_counts = df.groupby(df['date'].dt.date).size()
        
        # Calcular estatísticas básicas
        total_days = len(daily_counts)
        days_with_data = len(daily_counts[daily_counts > 0])
        
        # Calcular média de medições por dia (apenas para dias com dados)
        avg_measurements = daily_counts[daily_counts > 0].mean()
        
        # Calcular limiar dinâmico
        dynamic_threshold = max(
            self.min_measurements_per_day,  # Limiar mínimo absoluto
            avg_measurements * self.threshold_multiplier  # Limiar baseado na média
        )
        
        # Calcular dias representativos usando o limiar dinâmico
        representative_days = len(daily_counts[daily_counts >= dynamic_threshold])
        
        # Calcular porcentagens
        availability_percentage = (days_with_data / self.total_days * 100)
        representative_percentage = (representative_days / self.total_days * 100)
        
        return {
            'total_days': total_days,
            'days_with_data': days_with_data,
            'representative_days': representative_days,
            'availability_percentage': availability_percentage,
            'representative_percentage': representative_percentage,
            'avg_measurements': avg_measurements,
            'dynamic_threshold': dynamic_threshold,
            'daily_counts': daily_counts,
            'start_date': df['date'].min(),
            'end_date': df['date'].max()
        }
    
    def process_all_stations(self) -> Dict[str, Dict[str, Dict]]:
        """
        Processa todas as estações em todos os níveis.
        
        Returns:
            Dicionário com resultados para cada estação em cada nível
        """
        results = {}
        
        for level, data_dir in self.data_dirs.items():
            if not os.path.exists(data_dir):
                logging.warning(f"Diretório não encontrado: {data_dir}")
                continue
            
            results[level] = {}
            
            # Processar cada arquivo no diretório
            for filename in os.listdir(data_dir):
                if not filename.endswith('.txt'):
                    continue
                
                station_name = filename.split('_')[0]
                file_path = os.path.join(data_dir, filename)
                
                logging.info(f"Processando {filename}")
                
                # Ler e processar dados
                df = self.read_aod_data(file_path)
                if df is not None and not df.empty:
                    availability = self.calculate_availability(df)
                    if availability:
                        results[level][station_name] = availability
        
        return results
    
    def plot_availability_comparison(self, results: Dict[str, Dict[str, Dict]]) -> str:
        """
        Plota comparação de disponibilidade entre níveis.
        
        Args:
            results: Dicionário com resultados de disponibilidade
            
        Returns:
            Caminho para o arquivo do gráfico salvo
        """
        # Preparar dados para plotagem
        plot_data = []
        for level, stations in results.items():
            for station, stats in stations.items():
                plot_data.append({
                    'Level': level,
                    'Station': station,
                    'Availability (%)': stats['availability_percentage'],
                    'Representative Days (%)': stats['representative_percentage']
                })
        
        df = pd.DataFrame(plot_data)
        
        # Criar figura com subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Boxplot de disponibilidade
        sns.boxplot(data=df, x='Level', y='Availability (%)', ax=ax1)
        ax1.set_title('Data Availability by Quality Level')
        ax1.set_xlabel('Quality Level')
        ax1.set_ylabel('Availability (%)')
        
        # Plot 2: Boxplot de dias representativos
        sns.boxplot(data=df, x='Level', y='Representative Days (%)', ax=ax2)
        ax2.set_title('Representative Days by Quality Level')
        ax2.set_xlabel('Quality Level')
        ax2.set_ylabel('Representative Days (%)')
        
        plt.tight_layout()
        
        # Salvar gráfico
        output_path = os.path.join(self.output_dir, 'availability_comparison.png')
        plt.savefig(output_path)
        plt.close()
        
        return output_path
    
    def plot_station_availability(self, results: Dict[str, Dict[str, Dict]], level: str) -> str:
        """
        Plota disponibilidade para cada estação em um nível específico.
        
        Args:
            results: Dicionário com resultados de disponibilidade
            level: Nível de qualidade
            
        Returns:
            Caminho para o arquivo do gráfico salvo
        """
        if level not in results:
            logging.warning(f"Nível {level} não encontrado nos resultados")
            return None
        
        # Preparar dados
        stations = []
        availability = []
        representative = []
        
        for station, stats in results[level].items():
            stations.append(station)
            availability.append(stats['availability_percentage'])
            representative.append(stats['representative_percentage'])
        
        # Criar figura
        fig, ax = plt.subplots(figsize=(15, 8))
        
        x = np.arange(len(stations))
        width = 0.35
        
        ax.bar(x - width/2, availability, width, label='Availability (%)')
        ax.bar(x + width/2, representative, width, label='Representative Days (%)')
        
        ax.set_ylabel('Percentage')
        ax.set_title(f'Station Availability - {level}')
        ax.set_xticks(x)
        ax.set_xticklabels(stations, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        
        # Salvar gráfico
        output_path = os.path.join(self.output_dir, f'station_availability_{level}.png')
        plt.savefig(output_path)
        plt.close()
        
        return output_path
    
    def generate_report(self, results: Dict[str, Dict[str, Dict]]) -> str:
        """
        Gera relatório de disponibilidade em formato CSV.
        
        Args:
            results: Dicionário com resultados de disponibilidade
            
        Returns:
            Caminho para o arquivo do relatório
        """
        # Preparar dados para o DataFrame
        data = []
        
        for level, stations in results.items():
            for station, stats in stations.items():
                data.append({
                    'Level': level,
                    'Station': station,
                    'Total Days': stats['total_days'],
                    'Days with Data': stats['days_with_data'],
                    'Representative Days': stats['representative_days'],
                    'Availability (%)': stats['availability_percentage'],
                    'Representative Days (%)': stats['representative_percentage'],
                    'Avg Measurements/Day': stats['avg_measurements'],
                    'Start Date': stats['start_date'],
                    'End Date': stats['end_date']
                })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Ordenar por nível e estação
        df = df.sort_values(['Level', 'Station'])
        
        # Salvar relatório
        output_path = os.path.join(self.output_dir, 'availability_report.csv')
        df.to_csv(output_path, index=False)
        
        return output_path

    def process_station_data(self, station_data: pd.DataFrame) -> Dict:
        """Process data for a single station."""
        try:
            # Calculate availability using dynamic threshold
            availability = self.calculate_availability(
                station_data,
                threshold_multiplier=THRESHOLD_MULTIPLIER,
                min_measurements=MIN_MEASUREMENTS_PER_DAY
            )
            
            # Calculate statistics
            stats = self.calculate_statistics(station_data)
            
            # Generate visualizations
            self.generate_visualizations(station_data, availability)
            
            return {
                'availability': availability,
                'statistics': stats
            }
        except Exception as e:
            logging.error(f"Error processing station data: {str(e)}")
            raise

def main():
    """Função principal."""
    try:
        # Inicializar processador
        processor = AeronetProcessor()
        
        # Processar dados
        logging.info("Processando dados AERONET...")
        results = processor.process_all_stations()
        
        # Gerar visualizações
        logging.info("Gerando visualizações...")
        
        # Plot de comparação
        comparison_plot = processor.plot_availability_comparison(results)
        logging.info(f"Gráfico de comparação salvo em: {comparison_plot}")
        
        # Plot de disponibilidade por estação para cada nível
        for level in processor.data_dirs.keys():
            station_plot = processor.plot_station_availability(results, level)
            if station_plot:
                logging.info(f"Gráfico de disponibilidade por estação para {level} salvo em: {station_plot}")
        
        # Gerar relatório
        report_path = processor.generate_report(results)
        logging.info(f"Relatório salvo em: {report_path}")
        
        logging.info("Processamento concluído com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro durante o processamento: {str(e)}")
        raise

if __name__ == '__main__':
    main() 