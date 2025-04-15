# -*- coding: utf-8 -*-
"""
Created on Mon Dec  9 19:25:33 2024

@author: mgodi
"""

#%% Imports
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import chardet
import os
import gc

#%% Define Functions
def detect_file_encoding(file_path, sample_size=10000):
    """
    Detect the encoding of a file by reading a sample of its content.
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(sample_size)
        result = chardet.detect(raw_data)
        return result['encoding']

def preprocess_data(file_path):
    """
    Preprocess the data by checking for required columns and replacing invalid values.
    """
    df = pd.read_csv(file_path)
    
    # Verificar se a coluna 'Date(dd:mm:yyyy)' existe
    if 'Date(dd:mm:yyyy)' not in df.columns:
        raise ValueError("A coluna 'Date(dd:mm:yyyy)' está ausente no arquivo.")
    
    # Substituir valores -999.000000 por NaN
    df.replace(-999.000000, np.nan, inplace=True)
    
    return df

def clean_dataframes(dfs, outlier_threshold=3):
    """
    Clean DataFrames by removing outliers, replacing invalid values, and dropping empty columns.
    """
    cleaned_dfs = {}
    for file_path, df in dfs.items():
        print(f"Cleaning DataFrame for: {file_path}")
        
        # Remove the first row (possible metadata)
        df = df.iloc[1:].reset_index(drop=True)
        
        # Replace specific invalid values with NaN
        df.replace(-999, np.nan, inplace=True)
        
        # Identify numeric columns
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        # Replace outliers with NaN
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std != 0:
                outliers = (df[col] < mean - outlier_threshold * std) | (df[col] > mean + outlier_threshold * std)
                df.loc[outliers, col] = np.nan
        
        # Drop columns with all NaN values
        df = df.dropna(axis=1, how='all')
        
        cleaned_dfs[file_path] = df
    return cleaned_dfs

def align_dataframes_by_date(dfs, date_column="Date(dd:mm:yyyy)", time_column="Time(hh:mm:ss)"):
    """
    Align DataFrames by ensuring they have a row for each day in the global date range.
    """
    for file_path, df in dfs.items():
        df[date_column] = pd.to_datetime(df[date_column], format="%d:%m:%Y", errors="coerce")
    
    min_date = min(df[date_column].min() for df in dfs.values())
    max_date = max(df[date_column].max() for df in dfs.values())
    print(f"Global date range: {min_date} to {max_date}")
    
    full_date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    aligned_dfs = {}
    for file_path, df in dfs.items():
        df = df.drop_duplicates(subset=date_column)
        df = df.set_index(date_column)
        df_aligned = df.reindex(full_date_range)
        df_aligned[date_column] = df_aligned.index
        if time_column in df.columns:
            df_aligned[time_column] = df_aligned[time_column].fillna("12:00:00")
        df_aligned = df_aligned.reset_index(drop=True)
        aligned_dfs[file_path] = df_aligned
    
    return aligned_dfs

def plot_time_series(diction, date_column="Date(dd:mm:yyyy)"):
    """
    Plot time series for each DataFrame in the dictionary with fixed axes and aesthetic configurations.

    X-axis: 1995 to 2024
    Y-axis: 0 to 2.5
    """
    x_min = pd.to_datetime("1995-01-01")
    x_max = pd.to_datetime("2024-12-31")
    y_min = 0
    y_max = 2.5

    # Custom colors and markers
    colors = ['darkblue', 'crimson', 'orange', 'green', 'purple', 'brown', 'gold', 'teal']
    markers = ['o', 's', 'D', '^', 'v', 'P', '*', 'X']

    for file_path, df in diction.items():
        print(f"Plotting time series for {file_path}...")

        # Convert date column if necessary
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

        # Select specific numeric columns
        subset = df.iloc[:, 3:10].copy()

        plt.figure(figsize=(12, 6))

        for i, col in enumerate(subset.columns):
            color = colors[i % len(colors)]
            marker = markers[i % len(markers)]
            plt.scatter(
                df[date_column], df[col],
                label=col,
                s=8,               # Smaller marker size
                alpha=0.6,         # Slight transparency
                color=color,
                marker=marker
            )

        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)
        plt.title(f"Time Series - AOD - {os.path.basename(file_path)}")
        plt.xlabel("Time")
        plt.ylabel("AOD")

        # Legend outside the plot area
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
        plt.tight_layout()

        # Save the figure with a unique filename
        safe_filename = os.path.basename(file_path).replace(" ", "_").replace(":", "_")
        plt.savefig(f'temporal_series_{safe_filename}.png', dpi=200)
        print(f"Figure saved as: temporal_series_{safe_filename}.png")
        plt.close()  # Close the figure to avoid overlapping plots

#%% Main Script
data_directory = '/home/mgodi/Documentos/projeto_aeronet_p1/AOD_data'
file_paths = [os.path.join(data_directory, file) for file in os.listdir(data_directory) if file.endswith('.txt')]

if not file_paths:
    print(f"No .txt files found in directory: {data_directory}")
else:
    print(f"Files found: {file_paths}")

problematic_files = []

for file_path in file_paths:
    try:
        print(f"\nProcessing file: {file_path}")
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        print(f"File size: {file_size:.2f} MB")
        
        encoding = detect_file_encoding(file_path)
        print(f"Detected encoding: {encoding}")
        
        header_line = None
        column_names = None
        with open(file_path, 'r', encoding=encoding) as file:
            for i, line in enumerate(file):
                if "Date(dd:mm:yyyy)" in line:
                    header_line = i
                    column_names = line.strip().split(",")
                    print(f"Header line found: {header_line}")
                    print(f"Column names: {column_names}")
                    break
        
        if header_line is None:
            raise ValueError("Header line not found")
        
        column_name_counts = Counter(column_names)
        unique_column_names = []
        for name in column_names:
            count = column_name_counts[name]
            if count > 1:
                new_name = f"{name}_{column_name_counts[name]}"
                column_name_counts[name] -= 1
            else:
                new_name = name
            unique_column_names.append(new_name)
        
        df = pd.read_csv(
            file_path,
            skiprows=header_line,
            names=unique_column_names,
            comment='#',
            encoding=encoding,
            low_memory=False
        )
        
        for col in df.columns:
            if col not in ["Date(dd:mm:yyyy)", "Time(hh:mm:ss)"]:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = preprocess_data(file_path)
        
        cleaned_dfs = clean_dataframes({file_path: df})
        cleaned_df = cleaned_dfs[file_path]
        
        aligned_dfs = align_dataframes_by_date({file_path: cleaned_df})
        aligned_df = aligned_dfs[file_path]
        
        plot_time_series({file_path: aligned_df}, date_column="Date(dd:mm:yyyy)")
        
        del df, cleaned_dfs, cleaned_df, aligned_dfs, aligned_df
        gc.collect()
        print(f"Memory cleared after processing file: {file_path}")
    
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        problematic_files.append(file_path)

print(f"Problematic files: {problematic_files}")



