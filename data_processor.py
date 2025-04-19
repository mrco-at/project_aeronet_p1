"""
Data processing module for AERONET data.
"""
import os
import logging
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class AeronetDataProcessor:
    """Class for processing AERONET data."""
    
    def __init__(self,
                 data_dir: str = 'data',
                 start_date: str = '2020-01-01',
                 end_date: str = '2023-12-31',
                 min_data_points: int = 1000,
                 min_availability_percentage: float = 50.0):
        """
        Initialize the data processor.
        
        Args:
            data_dir: Directory containing AERONET data files
            start_date: Start date for data processing (YYYY-MM-DD)
            end_date: End date for data processing (YYYY-MM-DD)
            min_data_points: Minimum number of data points required
            min_availability_percentage: Minimum availability percentage required
        """
        self.data_dir = data_dir
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.min_data_points = min_data_points
        self.min_availability_percentage = min_availability_percentage
        self.empty_files = []
        self.errors = []
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        os.makedirs('output', exist_ok=True)
    
    def process_data(self) -> Dict[str, Dict]:
        """
        Process AERONET data files and calculate availability statistics.
        
        Returns:
            Dictionary containing availability data for each quality level
        """
        availability_data = {}
        
        # Process each quality level directory
        for level in ['10', '15', '20']:
            level_dir = f'AOD_data_lvl{level}'
            if not os.path.exists(level_dir):
                self.logger.warning(f"Directory not found: {level_dir}")
                continue
                
            availability_data[f'level{level}'] = {}
            
            # Process each station file
            for file_name in os.listdir(level_dir):
                if not file_name.endswith('.txt'):
                    continue
                    
                file_path = os.path.join(level_dir, file_name)
                station_name = file_name.split('_')[0]
                
                try:
                    # Check if file is empty
                    if os.path.getsize(file_path) == 0:
                        self.logger.warning(f"Empty file: {file_path}")
                        self.empty_files.append(file_path)
                        continue
                    
                    # Try different encodings
                    encodings = ['utf-8', 'latin1', 'iso-8859-1']
                    df = None
                    
                    for encoding in encodings:
                        try:
                            df = pd.read_csv(file_path, skiprows=4, encoding=encoding, low_memory=False)
                            break
                        except UnicodeDecodeError:
                            continue
                        except Exception as e:
                            self.logger.warning(f"Error reading file with {encoding} encoding: {str(e)}")
                            continue
                    
                    if df is None:
                        raise ValueError(f"Could not read file with any encoding: {file_path}")
                    
                    # Convert date column
                    df['Date(dd:mm:yyyy)'] = pd.to_datetime(df['Date(dd:mm:yyyy)'], format='%d:%m:%Y')
                    
                    # Filter by date range
                    df = df[(df['Date(dd:mm:yyyy)'] >= self.start_date) & 
                           (df['Date(dd:mm:yyyy)'] <= self.end_date)]
                    
                    if len(df) == 0:
                        self.logger.warning(f"No data found in date range for {file_path}")
                        continue
                    
                    # Calculate statistics
                    total_days = (self.end_date - self.start_date).days + 1
                    days_with_data = len(df['Date(dd:mm:yyyy)'].unique())
                    availability = (days_with_data / total_days) * 100
                    
                    if availability >= self.min_availability_percentage:
                        availability_data[f'level{level}'][station_name] = {
                            'availability_percentage': availability,
                            'days_with_data': days_with_data,
                            'total_days': total_days,
                            'avg_measurements_per_day': len(df) / days_with_data
                        }
                    
                except Exception as e:
                    error_msg = f"Error processing file {file_path}: {str(e)}"
                    self.logger.error(error_msg)
                    self.errors.append((file_path, error_msg))
        
        return availability_data
    
    def get_empty_files(self) -> List[str]:
        """
        Get list of empty data files.
        
        Returns:
            List of empty file paths
        """
        empty_files = []
        for level in ['10', '15', '20']:
            level_dir = f'AOD_data_lvl{level}'
            if not os.path.exists(level_dir):
                continue
            for filename in os.listdir(level_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(level_dir, filename)
                    if os.path.getsize(file_path) == 0:
                        empty_files.append(file_path)
        return empty_files
    
    def get_errors(self) -> List[Tuple[str, str]]:
        """
        Get list of processing errors.
        
        Returns:
            List of tuples containing (file_path, error_message)
        """
        return self.errors 