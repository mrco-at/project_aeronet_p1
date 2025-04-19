"""
Utility functions for AERONET data analysis.
"""
import os
import chardet
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

def detect_file_encoding(file_path: str, sample_size: int = 10000) -> str:
    """
    Detect the encoding of a file.
    
    Args:
        file_path: Path to the file
        sample_size: Number of bytes to read for detection
        
    Returns:
        str: Detected encoding
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(sample_size)
        encoding = chardet.detect(raw_data)['encoding']
    return encoding or 'utf-8'

def create_output_directory(directory: str) -> None:
    """
    Create output directory if it doesn't exist.
    
    Args:
        directory: Directory path to create
    """
    os.makedirs(directory, exist_ok=True)

def calculate_date_range_days(start_date: str, end_date: str) -> int:
    """
    Calculate the number of days between two dates.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        int: Number of days between dates
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    return (end - start).days + 1

def format_plot_title(title: str) -> str:
    """
    Format plot title by breaking it into multiple lines if needed.
    
    Args:
        title: Original title string
        
    Returns:
        str: Formatted title
    """
    return "\n".join(title.split(" - "))

class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass 