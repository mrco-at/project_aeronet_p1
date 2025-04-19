#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from map_utils import extract_kmz_data, create_south_america_map, create_static_south_america_map
from config import KMZ_FILE, OUTPUT_DIR

def main():
    """
    Função principal que gera mapas da América do Sul com estações AERONET.
    Gera mapas para diferentes níveis de AOD (10, 15 e 20).
    """
    # Configuração do logging
    logging.basicConfig(level=logging.INFO)
    
    # Verifica se o arquivo KMZ existe
    if not os.path.exists(KMZ_FILE):
        logging.error(f"KMZ file not found: {KMZ_FILE}")
        return
    
    try:
        # Extrai as estações do arquivo KMZ
        stations = extract_kmz_data(KMZ_FILE)
        if not stations:
            logging.error("No stations found in the KMZ file.")
            return
        
        logging.info(f"Extracted {len(stations)} stations from KMZ file.")
        
        # Cria o diretório de saída se não existir
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Gera mapas para cada nível de AOD
        for level in ['level20', 'level15', 'level10']:
            # Gera o mapa interativo
            interactive_map = create_south_america_map(
                stations,
                level=level,
                output_path=os.path.join(OUTPUT_DIR, f'south_america_map_{level}.html')
            )
            logging.info(f"Interactive map for {level} generated in: {os.path.join(OUTPUT_DIR, f'south_america_map_{level}.html')}")
            
            # Gera o mapa estático
            create_static_south_america_map(
                stations,
                level=level,
                output_path=os.path.join(OUTPUT_DIR, f'south_america_map_{level}_static.png')
            )
            logging.info(f"Static map for {level} generated in: {os.path.join(OUTPUT_DIR, f'south_america_map_{level}_static.png')}")
        
        logging.info("All maps generation completed successfully!")
        
    except Exception as e:
        logging.error(f"Error processing KMZ file: {str(e)}")
        return

if __name__ == '__main__':
    main() 