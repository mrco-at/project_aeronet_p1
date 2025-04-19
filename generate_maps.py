import pandas as pd
import folium
from folium import plugins
import geopandas as gpd
import logging
from map_utils import create_south_america_map

# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

def generate_maps():
    """Generate maps for each quality level using availability data."""
    # Ler dados de disponibilidade
    df = pd.read_csv('station_availability.csv')
    
    # Processar cada nível de qualidade
    for level in ['10', '15', '20']:
        # Filtrar dados para o nível atual
        level_data = df[df['level'] == level]
        
        # Criar lista de estações no formato esperado pela função create_south_america_map
        stations = []
        for _, row in level_data.iterrows():
            stations.append({
                'name': row['station'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'availability': row['availability']
            })
        
        # Gerar mapa interativo
        output_path = f'output/south_america_map_level{level}.html'
        create_south_america_map(stations, level=level, output_path=output_path)
        logging.info(f"Mapa interativo para nível {level} gerado em: {output_path}")
        
        # Gerar mapa estático
        static_output_path = f'output/south_america_map_level{level}_static.png'
        create_static_south_america_map(stations, output_path=static_output_path, level=level)
        logging.info(f"Mapa estático para nível {level} gerado em: {static_output_path}")

if __name__ == "__main__":
    generate_maps() 