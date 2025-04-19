"""
Data processing module for AERONET data.
"""
import os
import logging
import pandas as pd
import chardet
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
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        self.min_data_points = min_data_points
        self.min_availability_percentage = min_availability_percentage
        self.empty_files = []
        self.errors = []
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        os.makedirs('output', exist_ok=True)
    
    def detect_file_encoding(self, file_path: str, sample_size: int = 10000) -> str:
        """
        Detect the encoding of a file using chardet.
        
        Args:
            file_path: Path to the file
            sample_size: Number of bytes to sample for detection
            
        Returns:
            str: Detected encoding
        """
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'

    def verify_file_integrity(self, file_path: str) -> bool:
        """
        Verify if a file is valid and contains data.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file is valid, False otherwise
        """
        try:
            # Check if file exists and is not empty
            if not os.path.exists(file_path):
                self.logger.warning(f"File does not exist: {file_path}")
                return False
                
            if os.path.getsize(file_path) == 0:
                self.logger.warning(f"File is empty: {file_path}")
                self.empty_files.append(file_path)
                return False
                
            # Try to read first few lines to check format
            with open(file_path, 'rb') as f:
                first_lines = f.readlines(1024)
                if not first_lines:
                    self.logger.warning(f"File has no content: {file_path}")
                    return False
                    
                # Check if file starts with AERONET header
                header = first_lines[0].decode('utf-8', errors='ignore').strip()
                if not header.startswith('AERONET'):
                    self.logger.warning(f"File does not have AERONET header: {file_path}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying file integrity: {str(e)}")
            return False

    def process_data(self) -> Dict[str, Dict]:
        """
        Process AERONET data files and calculate availability statistics.
        
        Returns:
            Dict[str, Dict]: Dictionary containing availability data for each station
        """
        availability_data = {}
        
        # Process each level
        for level in ['10', '15', '20']:
            level_dir = os.path.join(self.data_dir, f'AOD_data_lvl{level}')
            if not os.path.exists(level_dir):
                self.logger.warning(f"Directory not found: {level_dir}")
                continue
                
            # Process each file in the level directory
            for file_name in os.listdir(level_dir):
                if not file_name.endswith('.txt'):
                    continue
                    
                file_path = os.path.join(level_dir, file_name)
                station_name = file_name.split('_')[0]
                
                try:
                    # Verify file integrity
                    if not self.verify_file_integrity(file_path):
                        continue
                    
                    # Detect file encoding
                    encoding = self.detect_file_encoding(file_path)
                    self.logger.info(f"Detected encoding for {file_name}: {encoding}")
                    
                    # Try different skiprows values
                    skiprows_options = [4, 5, 6]
                    df = None
                    
                    for skiprows in skiprows_options:
                        try:
                            df = pd.read_csv(file_path, 
                                           skiprows=skiprows, 
                                           encoding=encoding,
                                           low_memory=False)
                            
                            # Verify required columns
                            if 'Date(dd:mm:yyyy)' not in df.columns:
                                self.logger.warning(f"Date column not found with skiprows={skiprows}")
                                continue
                                
                            # Convert date column
                            df['Date(dd:mm:yyyy)'] = pd.to_datetime(df['Date(dd:mm:yyyy)'], 
                                                                   format='%d:%m:%Y',
                                                                   errors='coerce')
                            
                            # Remove rows with invalid dates
                            df = df.dropna(subset=['Date(dd:mm:yyyy)'])
                            
                            if len(df) == 0:
                                self.logger.warning(f"No valid dates found in file: {file_path}")
                                continue
                                
                            break
                            
                        except Exception as e:
                            self.logger.warning(f"Error reading file with skiprows={skiprows}: {str(e)}")
                            continue
                    
                    if df is None or len(df) == 0:
                        raise ValueError(f"Could not read file with any configuration: {file_path}")
                    
                    # Filter by date range
                    df = df[(df['Date(dd:mm:yyyy)'] >= self.start_date) & 
                           (df['Date(dd:mm:yyyy)'] <= self.end_date)]
                    
                    if len(df) == 0:
                        self.logger.warning(f"No data found in date range for {file_path}")
                        continue
                    
                    # Calculate availability
                    total_days = (self.end_date - self.start_date).days + 1
                    days_with_data = len(df['Date(dd:mm:yyyy)'].unique())
                    availability = (days_with_data / total_days) * 100
                    
                    # Store results
                    if station_name not in availability_data:
                        availability_data[station_name] = {}
                    
                    availability_data[station_name][f'level{level}'] = {
                        'availability': availability,
                        'days_with_data': days_with_data,
                        'total_days': total_days
                    }
                    
                    self.logger.info(f"Successfully processed station {station_name} for level {level} with {availability:.2f}% availability")
                    
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
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