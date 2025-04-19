import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('availability_analysis.log'),
        logging.StreamHandler()
    ]
)

def read_aod_data(file_path):
    """
    Read AOD data from a file, handling metadata and date formats.
    """
    try:
        # Find the header line
        with open(file_path, 'r') as f:
            lines = f.readlines()
            header_line = None
            for i, line in enumerate(lines):
                if 'Date' in line and 'AOD' in line:
                    header_line = i
                    break
            
            if header_line is None:
                logging.warning(f"No header line found in {file_path}")
                return None
            
            # Read the data starting from the header line
            df = pd.read_csv(file_path, skiprows=header_line, delimiter=',')
            
            # Find date and AOD 500nm columns
            date_col = [col for col in df.columns if 'Date' in col][0]
            aod_col = [col for col in df.columns if 'AOD_500' in col][0]
            
            # Convert date and AOD to proper formats
            df[date_col] = pd.to_datetime(df[date_col], format='%d:%m:%Y', errors='coerce')
            df[aod_col] = pd.to_numeric(df[aod_col], errors='coerce')
            
            # Remove rows with invalid dates or AOD values
            df = df.dropna(subset=[date_col, aod_col])
            df = df[df[aod_col] != -999.000000]
            
            # Keep only relevant columns and rename them
            df = df[[date_col, aod_col]]
            df.columns = ['date', 'aod_500nm']
            
            return df
            
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        return None

def calculate_daily_availability(df):
    """
    Calculate daily availability of measurements.
    """
    if df is None or df.empty:
        return None
    
    # Group by date and count measurements
    daily_counts = df.groupby(df['date'].dt.date).size()
    
    # Calculate statistics
    total_days = len(daily_counts)
    days_with_data = len(daily_counts[daily_counts > 0])
    avg_measurements = daily_counts.mean()
    
    return {
        'total_days': total_days,
        'days_with_data': days_with_data,
        'availability_percentage': (days_with_data / total_days * 100) if total_days > 0 else 0,
        'avg_measurements': avg_measurements,
        'daily_counts': daily_counts
    }

def plot_availability(daily_counts, station_name, output_dir='output'):
    """
    Create plots showing data availability.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Daily measurement counts
    daily_counts.plot(kind='line', ax=ax1)
    ax1.set_title(f'Daily Measurements - {station_name}')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Number of Measurements')
    ax1.grid(True)
    
    # Plot 2: Histogram of measurements per day
    daily_counts.plot(kind='hist', bins=50, ax=ax2)
    ax2.set_title(f'Distribution of Daily Measurements - {station_name}')
    ax2.set_xlabel('Measurements per Day')
    ax2.set_ylabel('Frequency')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station_name}_availability.png'))
    plt.close()

def main():
    # Diretórios dos dados
    data_dirs = {
        'level10': 'AOD_data_lvl10',
        'level15': 'AOD_data_lvl15',
        'level20': 'AOD_data_lvl20'
    }
    
    results = {}
    
    # Processar cada diretório
    for level, dir_name in data_dirs.items():
        if not os.path.exists(dir_name):
            logging.warning(f"Directory not found: {dir_name}")
            continue
            
        results[level] = {}
        
        # Processar cada arquivo no diretório
        for file_name in os.listdir(dir_name):
            if not file_name.endswith('.txt'):
                continue
                
            station_name = file_name.split('_')[0]
            file_path = os.path.join(dir_name, file_name)
            
            logging.info(f"Processing {file_name}")
            
            # Ler e processar dados
            df = read_aod_data(file_path)
            if df is not None and not df.empty:
                availability = calculate_daily_availability(df)
                if availability:
                    results[level][station_name] = availability
                    plot_availability(availability['daily_counts'], 
                                    f"{station_name}_{level}", 
                                    'output')
    
    # Gerar relatório
    report_data = []
    for level in results:
        for station in results[level]:
            stats = results[level][station]
            report_data.append({
                'Level': level,
                'Station': station,
                'Total Days': stats['total_days'],
                'Days with Data': stats['days_with_data'],
                'Availability %': stats['availability_percentage'],
                'Avg Measurements/Day': stats['avg_measurements']
            })
    
    # Criar DataFrame e salvar relatório
    report_df = pd.DataFrame(report_data)
    report_df.to_csv('output/availability_report.csv', index=False)
    
    # Plotar comparação entre níveis
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=report_df, x='Level', y='Availability %')
    plt.title('Data Availability by Quality Level')
    plt.savefig('output/availability_by_level.png')
    plt.close()

if __name__ == "__main__":
    main() 