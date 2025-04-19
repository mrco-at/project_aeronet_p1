"""
Utility functions for generating maps of AERONET stations.
"""
import os
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import geopandas as gpd
import folium
from folium import plugins
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from typing import Dict, List, Tuple, Any, Optional, Union
from config import BRAZIL_CENTER, MAP_ZOOM, COLOR_SCHEME, OUTPUT_DIR, DATA_DIR, GEOS_DIR
import logging
import numpy as np
from datetime import datetime, timedelta
import glob
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import re
from bs4 import BeautifulSoup
import warnings
from pathlib import Path
import json
from matplotlib.colors import LinearSegmentedColormap
import requests

def extract_kmz_data(kmz_file: str) -> List[Dict[str, Union[str, float]]]:
    """
    Extract station data from KMZ file.
    
    Args:
        kmz_file: Path to the KMZ file
        
    Returns:
        List of dictionaries containing station information
    """
    stations = []
    try:
        with zipfile.ZipFile(kmz_file, 'r') as kmz:
            # Find the KML file in the KMZ archive
            kml_file = next(f for f in kmz.namelist() if f.endswith('.kml'))
            logging.info(f"Found KML file: {kml_file}")
            
            # Extract and read the KML file
            with kmz.open(kml_file) as f:
                content = f.read().decode('utf-8')
                
                # Parse XML with BeautifulSoup
                soup = BeautifulSoup(content, 'xml')
                
                # Find all Placemark elements
                placemarks = soup.find_all('Placemark')
                
                for placemark in placemarks:
                    try:
                        # Extract station name
                        name_tag = placemark.find('name')
                        if name_tag and name_tag.string:
                            station_name = name_tag.string.strip()
                            
                            # Extract coordinates
                            coords_tag = placemark.find('coordinates')
                            if coords_tag and coords_tag.string:
                                coords_text = coords_tag.string.strip()
                                coords = coords_text.split(',')
                                
                                if len(coords) >= 2:
                                    try:
                                        lon, lat = float(coords[0]), float(coords[1])
                                        stations.append({
                                            'name': station_name,
                                            'latitude': lat,
                                            'longitude': lon
                                        })
                                        logging.info(f"Extracted station: {station_name} at ({lat}, {lon})")
                                    except ValueError as e:
                                        logging.warning(f"Could not parse coordinates for station {station_name}: {str(e)}")
                    except Exception as e:
                        logging.warning(f"Error processing placemark: {str(e)}")
                        continue
    
    except Exception as e:
        logging.error(f"Error extracting KMZ data: {str(e)}")
        raise  # Re-raise the exception for better error handling
    
    if not stations:
        logging.warning("No stations were extracted from the KMZ file")
    else:
        logging.info(f"Successfully extracted {len(stations)} stations")
    
    return stations

def filter_brazilian_stations(stations):
    """
    Filter stations to keep only those in Brazil.
    
    Args:
        stations (list): List of dictionaries containing station information
        
    Returns:
        list: Filtered list of stations in Brazil
    """
    # Approximate Brazil boundaries
    brazil_bounds = {
        'min_lat': -35.0,
        'max_lat': 5.0,
        'min_lon': -75.0,
        'max_lon': -30.0
    }
    
    brazilian_stations = []
    for station in stations:
        lat = station['latitude']
        lon = station['longitude']
        
        if (brazil_bounds['min_lat'] <= lat <= brazil_bounds['max_lat'] and
            brazil_bounds['min_lon'] <= lon <= brazil_bounds['max_lon']):
            brazilian_stations.append(station)
    
    return brazilian_stations

def calculate_data_availability(data):
    """
    Calculate data availability for a station.
    
    Args:
        data (pd.DataFrame): DataFrame with station data
        
    Returns:
        float: Data availability percentage (0-100)
    """
    if data is None or data.empty:
        return 0.0
        
    try:
        # Find the date column
        date_col = None
        for col in data.columns:
            if 'date' in col.lower():
                date_col = col
                break
                
        if date_col is None:
            logging.warning("No date column found in data")
            return 0.0
            
        # Find AOD columns (500nm is commonly used)
        aod_cols = [col for col in data.columns if 'aod' in col.lower() and '500' in col]
        if not aod_cols:
            logging.warning("No AOD 500nm column found in data")
            return 0.0
            
        aod_col = aod_cols[0]  # Use the first matching AOD column
            
        # Convert date column to datetime, handling different formats
        try:
            # First try to parse the date string to identify the format
            sample_date = str(data[date_col].iloc[0])
            if ':' in sample_date:
                # Try dd:mm:yyyy format
                data[date_col] = pd.to_datetime(data[date_col], format='%d:%m:%Y', errors='coerce')
            elif '/' in sample_date:
                # Try mm/dd/yyyy format
                data[date_col] = pd.to_datetime(data[date_col], format='%m/%d/%Y', errors='coerce')
            else:
                # Try pandas default parser
                data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
            
            # Remove rows with invalid dates
            data = data.dropna(subset=[date_col])
            
            if data.empty:
                logging.warning("No valid dates found in data")
                return 0.0
                
        except Exception as e:
            logging.error(f"Error converting dates: {str(e)}")
            return 0.0
        
        # Filter data between 1995 and 2024
        mask = (data[date_col].dt.year >= 1995) & (data[date_col].dt.year <= 2024)
        filtered_data = data[mask].copy()
        
        if filtered_data.empty:
            logging.warning("No data found between 1995 and 2024")
            return 0.0
            
        # Group by date and count valid measurements per day
        # Convert AOD column to numeric, treating errors as NaN
        filtered_data[aod_col] = pd.to_numeric(filtered_data[aod_col], errors='coerce')
        # Consider values that are not -999 and not NaN as valid
        valid_data = filtered_data[~filtered_data[aod_col].isna() & (filtered_data[aod_col] != -999.0)]
        daily_counts = valid_data.groupby(valid_data[date_col].dt.date)[aod_col].count()
        
        # Consider a day valid if it has at least 8 measurements
        valid_days = (daily_counts >= 8).sum()
        
        # Calculate total days in period
        start_date = datetime(1995, 1, 1)
        end_date = datetime(2024, 12, 31)
        total_days = (end_date - start_date).days + 1
        
        # Calculate availability percentage
        availability = (valid_days / total_days) * 100
        
        logging.info(f"Calculated availability: {availability:.2f}% ({valid_days} valid days out of {total_days} total days)")
        return availability
        
    except Exception as e:
        logging.error(f"Error calculating data availability: {str(e)}")
        return 0.0

def read_aod_data(file_path):
    """
    Read AOD data from a file, handling metadata and date formats correctly.
    
    Args:
        file_path: Path to the AOD data file
        
    Returns:
        DataFrame with processed AOD data
    """
    try:
        # Read the file to find the header line
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Find the header line (contains 'Date' and 'AOD')
        header_line = None
        for i, line in enumerate(lines):
            if 'Date' in line and 'AOD' in line:
                header_line = i
                break
                
        if header_line is None:
            logging.warning(f"No header line found in {file_path}")
            return None
            
        # Read the data starting from the header line
        df = pd.read_csv(file_path, skiprows=header_line, sep=',')
        
        # Find the date column (it may have different names)
        date_col = None
        for col in df.columns:
            if 'Date' in col:
                date_col = col
                break
                
        if date_col is None:
            logging.warning(f"No date column found in {file_path}")
            return None
            
        # Convert date to datetime, handling different formats
        try:
            # Try dd:mm:yyyy format first
            df['date'] = pd.to_datetime(df[date_col], format='%d:%m:%Y')
        except:
            try:
                # Try yyyy:mm:dd format
                df['date'] = pd.to_datetime(df[date_col], format='%Y:%m:%d')
            except:
                # If both fail, let pandas try to infer the format
                df['date'] = pd.to_datetime(df[date_col])
        
        # Find the AOD 500nm column
        aod_col = None
        for col in df.columns:
            if 'AOD_500' in col:
                aod_col = col
                break
                
        if aod_col is None:
            logging.warning(f"No AOD 500nm column found in {file_path}")
            return None
            
        # Convert AOD values to numeric, handling errors
        df['aod_500nm'] = pd.to_numeric(df[aod_col], errors='coerce')
        
        # Remove rows with invalid dates or AOD values
        df = df.dropna(subset=['date', 'aod_500nm'])
        df = df[df['aod_500nm'] != -999.000000]  # Remove missing data values
        
        # Keep only the columns we need
        df = df[['date', 'aod_500nm']]
        
        return df
        
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        return None

def load_station_data(station_name, level=None):
    """
    Load AOD data for a specific station.
    
    Args:
        station_name (str): Name of the station
        level (int, optional): AOD data level (10, 15, or 20)
        
    Returns:
        pd.DataFrame: DataFrame with station data, or None if no data available
    """
    # Define the data directories
    data_dirs = {
        20: 'AOD_data_lvl20',
        15: 'AOD_data_lvl15',
        10: 'AOD_data_lvl10'
    }
    
    # If level is specified, try that level first
    if level in data_dirs:
        file_path = os.path.join(data_dirs[level], f"{station_name}_1995-01-01_to_2024-12-31_AOD{level}_all_points.txt")
        if os.path.exists(file_path):
            data = read_aod_data(file_path)
            if data is not None:
                logging.info(f"Loaded data for {station_name} from level {level}")
                return data
    
    # If level is not specified or data not found, try all levels in preferred order
    preferred_levels = [20, 15, 10]  # Try highest quality first
    if level is not None:
        preferred_levels.remove(level)
        preferred_levels.insert(0, level)
        
    for lvl in preferred_levels:
        file_path = os.path.join(data_dirs[lvl], f"{station_name}_1995-01-01_to_2024-12-31_AOD{lvl}_all_points.txt")
        if os.path.exists(file_path):
            data = read_aod_data(file_path)
            if data is not None:
                logging.info(f"Loaded data for {station_name} from level {lvl}")
                return data
                
    logging.warning(f"No valid data found for station {station_name}")
    return None

def get_availability_color(availability):
    """
    Get color based on data availability.
    
    Args:
        availability (float): Data availability percentage
        
    Returns:
        str: Color in hex format
    """
    if availability == 0:
        return '#808080'  # Gray for no data
        
    # Create a custom colormap from red to yellow to green
    colors = [(1, 0, 0), (1, 1, 0), (0, 1, 0)]  # Red, Yellow, Green
    positions = [0, 0.5, 1]
    custom_cmap = LinearSegmentedColormap.from_list("custom", list(zip(positions, colors)))
    
    # Normalize availability to [0, 1]
    normalized = min(max(availability / 100.0, 0), 1)
    
    # Get RGB color and convert to hex
    rgb = custom_cmap(normalized)
    hex_color = mcolors.rgb2hex(rgb)
    
    return hex_color

def get_marker_properties(availability):
    """
    Retorna a cor e o grupo do marcador baseado na disponibilidade.
    
    Args:
        availability (float): Porcentagem de disponibilidade dos dados
    
    Returns:
        tuple: (cor, grupo) onde cor é uma string hex e grupo é uma string
    """
    if availability >= 75:
        return '#2ecc71', 'high'  # Verde
    elif availability >= 50:
        return '#f1c40f', 'medium'  # Amarelo
    else:
        return '#e74c3c', 'low'  # Vermelho

def ensure_kmz_file():
    """
    Ensure the KMZ file exists in the data directory.
    If not, download it from AERONET website.
    """
    kmz_path = os.path.join('data', 'AERONET_Stations.kmz')
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists(kmz_path):
        logging.info("Downloading AERONET stations KMZ file...")
        try:
            response = requests.get('https://aeronet.gsfc.nasa.gov/aeronet_locations.kmz')
            response.raise_for_status()
            
            with open(kmz_path, 'wb') as f:
                f.write(response.content)
            logging.info(f"KMZ file downloaded successfully to {kmz_path}")
        except Exception as e:
            logging.error(f"Error downloading KMZ file: {str(e)}")
            raise
    else:
        logging.info(f"KMZ file already exists at {kmz_path}")
    
    return kmz_path

def create_south_america_map(stations, level=None, output_path=None):
    """
    Create an interactive map of South America with AERONET stations.
    
    Args:
        stations (list): List of dictionaries containing station information
        level (int, optional): AOD data level (10, 15, or 20)
        output_path (str, optional): Path to save the map
        
    Returns:
        str: Path to the saved map
    """
    try:
        # Ensure KMZ file exists
        kmz_path = ensure_kmz_file()
        
        # Extract station data from KMZ
        stations_data = extract_kmz_data(kmz_path)
        
        # Create a DataFrame from stations
        stations_df = pd.DataFrame(stations_data)
        
        # Ensure required columns exist
        if 'latitude' not in stations_df.columns or 'longitude' not in stations_df.columns:
            logging.error("Missing required columns 'latitude' or 'longitude' in stations data")
            return None
            
        # Create map centered on South America
        m = folium.Map(
            location=BRAZIL_CENTER,
            zoom_start=MAP_ZOOM,
            tiles='CartoDB positron'
        )
        
        # Add stations to map
        for _, station in stations_df.iterrows():
            try:
                # Load station data and calculate availability
                data = load_station_data(station['name'], level)
                availability = calculate_data_availability(data)
                
                # Get marker properties based on availability
                marker_props = get_marker_properties(availability)
                
                # Create popup content
                popup_content = f"""
                <b>{station['name']}</b><br>
                Latitude: {station['latitude']:.4f}<br>
                Longitude: {station['longitude']:.4f}<br>
                Data Availability: {availability:.1f}%
                """
                
                # Add marker to map
                folium.CircleMarker(
                    location=[station['latitude'], station['longitude']],
                    radius=marker_props['size'],
                    popup=popup_content,
                    color=marker_props['color'],
                    fill=True,
                    fillColor=marker_props['color'],
                    fillOpacity=0.7
                ).add_to(m)
                
            except Exception as e:
                logging.warning(f"Error adding station {station['name']} to map: {str(e)}")
                # Add a gray marker for stations with errors
                folium.CircleMarker(
                    location=[station['latitude'], station['longitude']],
                    radius=5,
                    popup=f"Error processing station: {station['name']}",
                    color='gray',
                    fill=True,
                    fillColor='gray',
                    fillOpacity=0.7
                ).add_to(m)
        
        # Save map
        if output_path is None:
            output_path = os.path.join(OUTPUT_DIR, f'south_america_map_level{level}.html')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        m.save(output_path)
        logging.info(f"Map saved to {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"Error creating South America map: {str(e)}")
        return None

def create_static_south_america_map(stations, output_path='south_america_map_static.png', level=None):
    """
    Cria um mapa estático da América do Sul com as estações AERONET.
    
    Args:
        stations (list): Lista de dicionários com informações das estações
        output_path (str): Caminho para salvar o mapa estático
        level (str, optional): Nível de qualidade dos dados ('cleaned', 'level20', 'level15', 'level10')
    
    Returns:
        bool: True se o mapa foi criado com sucesso, False caso contrário
    """
    try:
        # Cria a figura e o eixo
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Tenta carregar o shapefile da América do Sul
        try:
            south_america = gpd.read_file('geos/ne_110m_admin_0_countries.shp')
            south_america.plot(ax=ax, color='#e6e6e6', edgecolor='#666666')
        except Exception as e:
            logging.warning(f"Não foi possível carregar o shapefile da América do Sul: {str(e)}")
            # Cria um mapa básico se não conseguir carregar o shapefile
            ax.set_xlim(-80, -30)
            ax.set_ylim(-35, 5)
        
        # Adiciona as estações ao mapa
        for station in stations:
            try:
                # Carrega os dados da estação
                df = load_station_data(station['name'], level)
                
                if df is not None:
                    # Calcula a disponibilidade dos dados
                    total_days = (df['date'].max() - df['date'].min()).days
                    available_days = len(df['date'].unique())
                    availability = (available_days / total_days) * 100 if total_days > 0 else 0
                    
                    # Determina a cor do marcador baseado na disponibilidade
                    color = get_availability_color(availability)
                else:
                    # Usa cinza para estações sem dados
                    color = 'gray'
                    availability = 0
                
                # Adiciona o marcador ao mapa
                ax.scatter(
                    station['longitude'],
                    station['latitude'],
                    c=color,
                    s=100,
                    alpha=0.7,
                    label=f"{station['name']} ({availability:.1f}%)"
                )
                
            except Exception as e:
                logging.error(f"Erro ao adicionar estação {station['name']} ao mapa: {str(e)}")
                continue
        
        # Configura o título e as legendas
        title = f"Estações AERONET na América do Sul - Nível {level}" if level else "Estações AERONET na América do Sul - Melhor disponível"
        ax.set_title(title, pad=20, fontsize=14)
        
        # Adiciona a legenda de cores
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Alta disponibilidade (≥30%)'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Média disponibilidade (10-30%)'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Baixa disponibilidade (<10%)'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=10, label='Sem dados')
        ]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5))
        
        # Ajusta o layout e salva o mapa
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logging.info(f"Mapa estático salvo em {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Erro ao criar mapa estático: {str(e)}")
        return False

def create_brazil_map(stations_df: pd.DataFrame, availability_data: Dict[str, float], 
                     output_path: str = "brazil_map.html") -> str:
    """
    Create an interactive map of Brazil with AERONET stations.
    
    Args:
        stations_df: DataFrame with station information
        availability_data: Dictionary with station names as keys and availability percentages as values
        output_path: Path to save the map
        
    Returns:
        Path to the saved map
    """
    # Create a map centered on Brazil
    brazil_map = folium.Map(
        location=[-15.7801, -47.9292],  # Brasília coordinates
        zoom_start=5,
        tiles='CartoDB positron'
    )
    
    # Add Brazil boundaries
    brazil_boundaries = gpd.read_file('ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp')
    brazil_boundaries = brazil_boundaries[brazil_boundaries['NAME'] == 'Brazil']
    
    # Add Brazil to the map
    folium.GeoJson(
        brazil_boundaries,
        name='Brazil',
        style_function=lambda x: {
            'fillColor': '#f0f0f0',
            'color': '#000000',
            'weight': 1
        }
    ).add_to(brazil_map)
    
    # Create a color scale for availability
    min_availability = min(availability_data.values()) if availability_data else 0
    max_availability = max(availability_data.values()) if availability_data else 100
    
    # Create a color map
    colormap = folium.LinearColormap(
        colors=['red', 'yellow', 'green'],
        vmin=min_availability,
        vmax=max_availability
    )
    
    # Add stations to the map
    for _, station in stations_df.iterrows():
        if station['longitude'] is not None and station['latitude'] is not None:
            name = station['name']
            availability = availability_data.get(name, 0)
            
            # Create popup content
            popup_content = f"""
            <b>{name}</b><br>
            Disponibilidade: {availability:.2f}%<br>
            Coordenadas: {station['latitude']:.4f}, {station['longitude']:.4f}
            """
            
            # Add marker
            folium.CircleMarker(
                location=[station['latitude'], station['longitude']],
                radius=8,
                popup=folium.Popup(popup_content, max_width=300),
                color=colormap(availability),
                fill=True,
                fill_color=colormap(availability),
                fill_opacity=0.7
            ).add_to(brazil_map)
    
    # Add colormap to the map
    colormap.add_to(brazil_map)
    colormap.caption = 'Disponibilidade de Dados (%)'
    
    # Save the map
    brazil_map.save(output_path)
    
    return output_path

def create_static_map(stations_df: pd.DataFrame, availability_data: Dict[str, float], 
                     output_path: str = "brazil_map_static.png") -> str:
    """
    Create a static map of Brazil with AERONET stations.
    
    Args:
        stations_df: DataFrame with station information
        availability_data: Dictionary with station names as keys and availability percentages as values
        output_path: Path to save the map
        
    Returns:
        Path to the saved map
    """
    # Read Brazil boundaries
    brazil_boundaries = gpd.read_file('ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp')
    brazil_boundaries = brazil_boundaries[brazil_boundaries['NAME'] == 'Brazil']
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot Brazil
    brazil_boundaries.plot(ax=ax, color='#f0f0f0', edgecolor='black', linewidth=0.5)
    
    # Create a color map
    cmap = plt.cm.RdYlGn
    
    # Add stations to the map
    for _, station in stations_df.iterrows():
        if station['longitude'] is not None and station['latitude'] is not None:
            name = station['name']
            availability = availability_data.get(name, 0)
            
            # Plot station
            ax.scatter(
                station['longitude'], 
                station['latitude'], 
                c=[availability], 
                cmap=cmap, 
                vmin=0, 
                vmax=100,
                s=100,
                edgecolor='black',
                linewidth=0.5
            )
            
            # Add station name
            ax.annotate(
                name, 
                (station['longitude'], station['latitude']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8
            )
    
    # Add colorbar
    norm = mcolors.Normalize(vmin=0, vmax=100)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.01)
    cbar.set_label('Disponibilidade de Dados (%)')
    
    # Set map limits
    ax.set_xlim(-75, -30)
    ax.set_ylim(-35, 5)
    
    # Add title
    ax.set_title('Disponibilidade de Dados AERONET no Brasil', fontsize=16)
    
    # Remove axes
    ax.axis('off')
    
    # Save the map
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path

def calculate_representative_days(file_path, min_measurements_per_day=8):
    """
    Calcula a disponibilidade de dias representativos de AOD_500 em um arquivo.
    
    Args:
        file_path: Caminho para o arquivo de dados AOD
        min_measurements_per_day: Número mínimo de medições por dia para considerar um dia representativo
        
    Returns:
        dict: Dicionário com informações sobre dias representativos
    """
    try:
        # Ler os dados do arquivo
        df = read_aod_data(file_path)
        
        # Calcular o número total possível de dias no período (1995-2024)
        start_date = pd.Timestamp('1995-01-01')
        end_date = pd.Timestamp('2024-12-31')
        total_possible_days = (end_date - start_date).days + 1
        
        if df is None or df.empty:
            logging.warning(f"Arquivo vazio ou sem dados: {file_path}")
            return {
                'total_possible_days': total_possible_days,
                'total_days': 0,
                'representative_days': 0,
                'representative_days_percentage': 0,
                'representative_days_percentage_total': 0,
                'avg_measurements_per_day': 0,
                'min_measurements_per_day': 0,
                'max_measurements_per_day': 0,
                'total_measurements': 0,
                'start_date': None,
                'end_date': None,
                'data_coverage_days': 0
            }
        
        # Agrupar por data e contar medições por dia
        measurements_per_day = df.groupby(df['date'].dt.date).size()
        
        # Calcular estatísticas
        total_days = len(measurements_per_day)
        representative_days = sum(measurements_per_day >= min_measurements_per_day)
        
        # Calcular porcentagens em relação aos dias com dados e ao total possível
        representative_days_percentage = (representative_days / total_days * 100) if total_days > 0 else 0
        representative_days_percentage_total = (representative_days / total_possible_days * 100)
        
        # Estatísticas adicionais
        avg_measurements_per_day = measurements_per_day.mean() if not measurements_per_day.empty else 0
        min_measurements_per_day = measurements_per_day.min() if not measurements_per_day.empty else 0
        max_measurements_per_day = measurements_per_day.max() if not measurements_per_day.empty else 0
        total_measurements = len(df)
        
        # Período coberto pelos dados
        start_date_data = df['date'].min()
        end_date_data = df['date'].max()
        data_coverage_days = (end_date_data - start_date_data).days + 1
        
        return {
            'total_possible_days': total_possible_days,
            'total_days': total_days,
            'representative_days': representative_days,
            'representative_days_percentage': representative_days_percentage,
            'representative_days_percentage_total': representative_days_percentage_total,
            'avg_measurements_per_day': avg_measurements_per_day,
            'min_measurements_per_day': min_measurements_per_day,
            'max_measurements_per_day': max_measurements_per_day,
            'total_measurements': total_measurements,
            'start_date': start_date_data,
            'end_date': end_date_data,
            'data_coverage_days': data_coverage_days
        }
    
    except Exception as e:
        logging.error(f"Erro ao calcular dias representativos para {file_path}: {str(e)}")
        return None

def calculate_all_stations_availability(min_measurements_per_day=8):
    """
    Calcula a disponibilidade de dias representativos para todas as estações em todos os níveis.
    
    Args:
        min_measurements_per_day: Número mínimo de medições por dia para considerar um dia representativo
        
    Returns:
        dict: Dicionário com informações de disponibilidade para cada estação em cada nível
    """
    results = {}
    
    # Carregar informações das estações do arquivo KMZ
    try:
        stations_info = extract_kmz_data('geos/aeronet_sites_v3.kmz')
        stations_dict = {station['name']: station for station in stations_info}
    except Exception as e:
        logging.error(f"Erro ao carregar informações das estações: {str(e)}")
        stations_dict = {}
    
    # Níveis de qualidade
    levels = ['10', '15', '20']
    
    # Obter lista de arquivos em cada diretório
    for level in levels:
        dir_path = f'AOD_data_lvl{level}'
        
        if not os.path.exists(dir_path):
            logging.warning(f"Diretório não encontrado: {dir_path}")
            continue
        
        # Listar arquivos no diretório
        files = [f for f in os.listdir(dir_path) if f.endswith(f'_AOD{level}_all_points.txt')]
        
        for file in files:
            station_name = file.split('_')[0]
            file_path = os.path.join(dir_path, file)
            
            # Calcular disponibilidade
            availability = calculate_representative_days(file_path, min_measurements_per_day)
            
            if availability:
                if station_name not in results:
                    results[station_name] = {}
                    # Adicionar informações espaciais se disponíveis
                    if station_name in stations_dict:
                        results[station_name]['latitude'] = stations_dict[station_name]['latitude']
                        results[station_name]['longitude'] = stations_dict[station_name]['longitude']
                        results[station_name]['elevation'] = stations_dict[station_name]['elevation']
                
                results[station_name][f'level{level}'] = availability
                logging.info(f"Disponibilidade calculada para {station_name} no nível {level}:")
                logging.info(f"  - Em relação aos dias com dados: {availability['representative_days_percentage']:.2f}%")
                logging.info(f"  - Em relação ao período total: {availability['representative_days_percentage_total']:.2f}%") 