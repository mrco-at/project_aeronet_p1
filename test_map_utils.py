"""
Test script for map_utils.py functions.
"""
import os
import logging
import pandas as pd
from map_utils import (
    extract_kmz_data, 
    filter_brazilian_stations, 
    create_south_america_map, 
    create_static_south_america_map
)
from config import OUTPUT_DIR, GEOS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_availability_data():
    """
    Load availability data from the data processor output.
    
    Returns:
        dict: Dictionary with station names as keys and availability percentages as values
    """
    # This is a placeholder. In a real scenario, you would load this from your data processor
    # For testing, we'll create some sample data
    sample_stations = [
        "Agri_School", "Alianca", "Chapada", "Jamari", "Jaru", 
        "JARU_TOWN", "Park_Brasilia", "Repressa_Samuel", "Santarem_SONDA", "Teles_Peres"
    ]
    
    # Create sample availability data
    availability_data = {}
    for station in sample_stations:
        # Assign random availability between 0 and 100
        import random
        availability_data[station] = random.uniform(0, 100)
    
    return availability_data

def main():
    """Main function to test map utilities."""
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Path to the KMZ file
        kmz_path = os.path.join(GEOS_DIR, 'aeronet_sites_v3.kmz')
        
        # Check if KMZ file exists
        if not os.path.exists(kmz_path):
            logger.error(f"KMZ file not found at {kmz_path}")
            return
        
        # Extract station information
        logger.info("Extracting station information from KMZ file...")
        all_stations = extract_kmz_data(kmz_path)
        logger.info(f"Found {len(all_stations)} stations in total")
        
        if not all_stations:
            logger.error("No stations found in the KMZ file")
            return
        
        # Filter Brazilian stations
        logger.info("Filtering Brazilian stations...")
        brazilian_stations = filter_brazilian_stations(all_stations)
        logger.info(f"Found {len(brazilian_stations)} stations in Brazil")
        
        # Load availability data
        logger.info("Loading availability data...")
        availability_data = load_availability_data()
        
        # Create interactive map
        logger.info("Creating interactive map of South America...")
        interactive_map_path = os.path.join(OUTPUT_DIR, 'south_america_map.html')
        create_south_america_map(brazilian_stations, availability_data, interactive_map_path)
        logger.info(f"Interactive map saved to: {interactive_map_path}")
        
        # Create static map
        logger.info("Creating static map of South America...")
        static_map_path = os.path.join(OUTPUT_DIR, 'south_america_map_static.png')
        create_static_south_america_map(brazilian_stations, availability_data, static_map_path)
        logger.info(f"Static map saved to: {static_map_path}")
        
        logger.info("Map generation completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 