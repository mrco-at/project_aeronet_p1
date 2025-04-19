"""
Configuration settings for AERONET data processing and visualization.
"""
import os
from datetime import datetime

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
GEOS_DIR = os.path.join(BASE_DIR, 'geos')

# KMZ file path
KMZ_FILE = os.path.join(GEOS_DIR, 'aeronet_sites_v3.kmz')

# Create directories if they don't exist
for directory in [DATA_DIR, OUTPUT_DIR, GEOS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Data processing settings
START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2023, 12, 31)
MIN_AVAILABILITY_PERCENTAGE = 5.0  # Porcentagem mínima de disponibilidade para considerar uma estação

# Dynamic threshold settings
THRESHOLD_MULTIPLIER = 1.5  # Multiplicador para o limiar dinâmico
MIN_MEASUREMENTS_PER_DAY = 8  # Número mínimo de medições por dia

# Map settings
BRAZIL_CENTER = [-15.7801, -47.9292]  # Latitude and longitude of Brazil's center
MAP_ZOOM = 4  # Initial zoom level for the map
COLOR_SCHEME = {
    'low': '#ffeda0',    # Light yellow for low availability
    'medium': '#feb24c',  # Orange for medium availability
    'high': '#f03b20'     # Red for high availability
}

# Plot settings
PLOT_DEFAULTS = {
    'figure_size': (12, 8),
    'dpi': 300,
    'font_size': {
        'title': 14,
        'label': 12,
        'tick': 10
    },
    'colors': {
        'primary': '#1f77b4',
        'secondary': '#ff7f0e',
        'tertiary': '#2ca02c'
    }
} 