"""
File: aeraod.py
Authors: Nicolas Neves de Oliveira, Juan Vicente Pallotta, João Basso Marques and Fábio Lopes
Contact: nicolas.oliveira@fisica.ufmt.br
DOI: 10.5281/zenodo.13242332
Date of creation: 2024/07/17
Description: This script downloads AERONET AOD and other data (version 3) for a specified site, date range, data type, data format, and AOD level.
The data is downloaded in a format that can be used in LPP (Lidar Processing Pipeline).

In case you prefer to download the AERONET data manually, please, use the download tool of the "AEROSOL OPTICAL DEPTH (V3)-SOLAR" version (direct sun algorithm).
The direct link is: https://aeronet.gsfc.nasa.gov/new_web/webtool_aod_v3.html
"""

import os
import wget
import sys
import time  # Import time for adding delays
import pandas as pd
import numpy as np

def download_aeronet_aod(site, start_date, end_date, data_type, data_format, aod_level, download_folder):
   
    # Ensure the download folder exists
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Prepare the URL for the download
    base_url = "https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v3?site={}&year={}&month={}&day={}&year2={}&month2={}&day2={}&AOD{}=1&AVG={}&if_no_html=1"

    # Parse the start and end dates
    start_year, start_month, start_day = start_date.split('-')
    end_year, end_month, end_day = end_date.split('-')

    # Select the data format
    if data_format.lower() == "all points":
        avg = 10
    elif data_format.lower() == "daily averages":
        avg = 20
    else:
        raise ValueError("Invalid data format specified. Choose 'all points' or 'daily averages'.")

    # Construct the full URL
    download_url = base_url.format(site, start_year, start_month, start_day, end_year, end_month, end_day, aod_level, avg)
    
    # Construct the output filename
    filename = f"{site}_{start_date}_to_{end_date}_AOD{aod_level}_{data_format.replace(' ', '_')}.txt"
    output_path = os.path.join(download_folder, filename)

    if os.path.isfile(output_path) == False:
        try: # The file does not exist --> Download it!
            print("\nDownloading data...")
            wget.download(download_url, out=output_path)
            print(f"\nDownloaded data to: {output_path}")
        except Exception as e:
            print(f"Error downloading data: {e}")
    else:
        print(f"AERONET file already exists: {output_path}")

def validate_downloaded_data(file_path):
    df = pd.read_csv(file_path)
    
    # Verificar se a coluna 'Date(dd:mm:yyyy)' existe
    if 'Date(dd:mm:yyyy)' not in df.columns:
        raise ValueError("A coluna 'Date(dd:mm:yyyy)' está ausente no arquivo.")
    
    # Substituir valores -999.000000 por NaN
    df.replace(-999.000000, np.nan, inplace=True)
    
    return df

# List of stations in Brazil
stations_in_brazil = [
    "Cuiaba", "Alta_Floresta", "Jamari", "Porto_Nacional", "Brasilia", "Tukurui", "Santarem", "Ariquiums", 
    "JamTown", "Ji_Parana", "Park_Brasilia", "Chapada", "Jaru", "JARU_TOWN", "Agri_School", "Teles_Peres", 
    "GORDO_rest", "Campo_Grande", "Uberlandia", "Alianca", "CAMPO_VERDE", "Pantanal", "Potosi_Mine", 
    "Repressa_Samuel", "Manaus", "Abracos_Hill", "Aguas_Emendadas", "Belterra", "Balbina", "Rio_Branco", 
    "Sao_Paulo", "CUIABA-MIRANDA", "Jaru_Reserve", "Ji_Parana_UNIR", "Porto_Velho", "Sao_Martinho_SONDA", 
    "Brasilia_SONDA", "Petrolina_SONDA", "Campo_Grande_SONDA", "Ji_Parana_SE", "Rio_de_Janeiro_UFRJ", 
    "Manaus_EMBRAPA", "Porto_Velho_UNIR", "Itajuba", "ARM_Manacapuru", "Cachoeira_Paulista", 
    "Amazon_ATTO_Tower", "Natal", "SP-EACH", "Ibirapuera", "Ji_Parana_UNIR_2", "Alta_Floresta_IF", 
    "ATTO-Campina", "Santarem_SONDA"
]

# Main function
if __name__ == "__main__":

    if len(sys.argv) == 8: # Usage: python aeraod.py site_name date_initial date_final data_type data_format aod_level download_folder       
        #                                    (0)        (1)        (2)         (3)        (4)        (5)        (6)          (7)

        # Configuration
        site_name    = sys.argv[1] # e.g. "CUIABA-MIRANDA"   # Specify the site/station name
        date_initial = sys.argv[2] # e.g. "2022-01-01"  # Specify the start date in 'YYYY-MM-DD' format
        date_final   = sys.argv[3] # e.g. "2022-12-31"  # Specify the end date in 'YYYY-MM-DD' format
        data_type    = sys.argv[4] # e.g. "Aerosol Optical Depth (AOD) with Precipitable Water and Angstrom Parameter" or "Total Optical Depth based on AOD Level*"
        data_format  = sys.argv[5] # e.g. "all points"  # Choose the data format: 'all points' or 'daily averages'
        aod_level    = sys.argv[6] # e.g. "10" #  Choose the AOD level: '10' for 1.0, '15' for 1.5, or '20' for 2.0
        download_folder = os.path.join(os.getcwd(), sys.argv[7])  # Specify the folder to the save the downloaded data
    
    if len(sys.argv) == 1: # If you run without arguments...
        print("Using the hardcoded values...")

        # Parameters
        site_name    = "CUIABA-MIRANDA"   # Specify the site/station name
        date_initial = "1995-01-01"  # Specify the start date in 'YYYY-MM-DD' format
        date_final   = "2024-12-31"  # Specify the end date in 'YYYY-MM-DD' format
        data_type    = "Aerosol Optical Depth (AOD) with Precipitable Water and Angstrom Parameter" # or "Total Optical Depth based on AOD Level*"
        data_format  = "all points"  # Choose the data format: 'all points' or 'daily averages'
        aod_level    = "20"          #  Choose the AOD level: '10' for 1.0, '15' for 1.5, or '20' for 2.0
        download_folder = os.path.join(os.getcwd(), "AOD_data_lvl20" )  # Specify the folder to save the downloaded data

    # Open a log file to record errors
    error_log_path = os.path.join(os.getcwd(), "error_log.txt")
    with open(error_log_path, "w") as error_log:
        # Iterate over all stations in the list
        for site_name in stations_in_brazil:
            print(f"\nProcessing station: {site_name}")
            retries = 3  # Number of retry attempts
            for attempt in range(retries):
                try:
                    # Call the download function for each station
                    download_aeronet_aod(site_name, date_initial, date_final, data_type, data_format, aod_level, download_folder)
                    
                    # Validate the downloaded data
                    file_path = os.path.join(download_folder, f"{site_name}_{date_initial}_to_{date_final}_AOD{aod_level}_{data_format.replace(' ', '_')}.txt")
                    validate_downloaded_data(file_path)
                    
                    break  # Exit retry loop if successful
                except Exception as e:
                    error_message = f"Error processing station {site_name} (Attempt {attempt + 1}/{retries}): {e}\n"
                    print(error_message)
                    error_log.write(error_message)
                    if attempt == retries - 1:
                        print(f"Failed to download data for station {site_name} after {retries} attempts.")
            # Add a delay between requests
            time.sleep(2)  # Delay of 2 seconds

