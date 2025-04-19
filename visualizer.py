"""
Visualization module for AERONET data analysis.
"""
import os
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
import logging
import folium
from folium.plugins import MarkerCluster
import branca.colormap as cm

import config
from utils import create_output_directory, format_plot_title

class AeronetVisualizer:
    """Class for visualizing AERONET data."""
    
    def __init__(self, output_dir: str = 'output'):
        """
        Initialize the visualizer with output directory.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Set matplotlib style
        plt.style.use('default')  # Use default matplotlib style

    def plot_frequency_distribution(self, city: str, distribution: pd.Series, level: str) -> str:
        """
        Create and save frequency distribution plot.
        
        Args:
            city: City name
            distribution: Frequency distribution data
            level: Quality level
            
        Returns:
            str: Path to saved plot
        """
        plt.figure(figsize=config.PLOT_DEFAULTS['figure_size'])
        distribution.plot(
            kind='bar',
            color=config.PLOT_DEFAULTS['colors']['frequency_dist'],
            edgecolor='black'
        )
        
        title = format_plot_title(f"Distribuição de Frequência - {city} ({level})")
        plt.title(title, fontsize=config.PLOT_DEFAULTS['title_fontsize'])
        plt.xlabel("Número de Medições Válidas por Dia", fontsize=config.PLOT_DEFAULTS['label_fontsize'])
        plt.ylabel("Frequência", fontsize=config.PLOT_DEFAULTS['label_fontsize'])
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        output_path = os.path.join(config.FREQUENCY_DIST_OUTPUT_DIR, f"{city}_{level}_frequency_distribution.png")
        plt.savefig(output_path)
        plt.close()
        
        return output_path

    def plot_representative_days(self, city: str, level: str,
                               days_absolute: int, days_percentage: float) -> str:
        """
        Create and save representative days dual-axis plot.
        
        Args:
            city: City name
            level: Quality level
            days_absolute: Absolute number of representative days
            days_percentage: Percentage of representative days
            
        Returns:
            str: Path to saved plot
        """
        fig, ax1 = plt.subplots(figsize=(8, 5))
        
        # Absolute values
        ax1.bar(["Dias Representativos"],
                [days_absolute],
                color=config.PLOT_DEFAULTS['colors']['representative_days']['absolute'],
                edgecolor='black',
                label="Absoluto")
        ax1.set_ylabel("Dias Representativos (Absoluto)",
                      fontsize=config.PLOT_DEFAULTS['label_fontsize'],
                      color=config.PLOT_DEFAULTS['colors']['representative_days']['absolute'])
        ax1.tick_params(axis='y',
                       labelcolor=config.PLOT_DEFAULTS['colors']['representative_days']['absolute'])
        
        # Percentage values
        ax2 = ax1.twinx()
        ax2.bar(["Dias Representativos (%)"],
                [days_percentage],
                color=config.PLOT_DEFAULTS['colors']['representative_days']['percentage'],
                edgecolor='black',
                label="Percentual")
        ax2.set_ylabel("Dias Representativos (%)",
                      fontsize=config.PLOT_DEFAULTS['label_fontsize'],
                      color=config.PLOT_DEFAULTS['colors']['representative_days']['percentage'])
        ax2.tick_params(axis='y',
                       labelcolor=config.PLOT_DEFAULTS['colors']['representative_days']['percentage'])
        
        title = f"Dias Representativos - {city} ({level})"
        plt.title(format_plot_title(title),
                 fontsize=config.PLOT_DEFAULTS['title_fontsize'])
        fig.tight_layout()
        
        output_path = os.path.join(config.REPRESENTATIVE_DAYS_OUTPUT_DIR,
                                  f"{city}_{level}_representative_days_dual_axis_bar.png")
        plt.savefig(output_path)
        plt.close()
        
        return output_path

    def plot_availability_comparison(self, availability_data: Dict[str, Dict]) -> str:
        """
        Plot comparison of availability across stations.
        
        Args:
            availability_data: Dictionary containing availability data for each quality level
            
        Returns:
            str: Path to the saved plot
        """
        try:
            if not availability_data:
                self.logger.warning("No availability data to plot")
                return None
            
            # Prepare data for plotting
            plot_data = []
            for level, stations in availability_data.items():
                for station, stats in stations.items():
                    plot_data.append({
                        'Station': station,
                        'Level': level,
                        'Availability (%)': stats['availability_percentage']
                    })
            
            if not plot_data:
                self.logger.warning("No valid data points to plot")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(plot_data)
            
            # Create plot
            plt.figure(figsize=(12, 6))
            
            # Get unique levels and create a bar for each
            levels = df['Level'].unique()
            bar_width = 0.8 / len(levels)
            
            for i, level in enumerate(levels):
                level_data = df[df['Level'] == level]
                x = np.arange(len(level_data))
                plt.bar(x + i * bar_width, level_data['Availability (%)'], 
                       width=bar_width, label=level)
            
            plt.title('Station Availability Comparison')
            plt.xlabel('Station')
            plt.ylabel('Availability (%)')
            plt.xticks(range(len(df['Station'].unique())), df['Station'].unique(), 
                      rotation=45, ha='right')
            plt.legend(title='Quality Level')
            plt.grid(True, axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            # Save plot
            output_path = os.path.join(self.output_dir, 'availability_comparison.png')
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Saved availability comparison plot to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error creating availability comparison plot: {str(e)}")
            raise

    def plot_spatial_availability(self, availability_data: Dict[str, Dict], station_coords: Dict[str, Tuple[float, float]]) -> None:
        """
        Create spatial map of station availability.
        
        Args:
            availability_data: Dictionary containing availability data for each quality level
            station_coords: Dictionary mapping station names to (lat, lon) coordinates
        """
        try:
            # Create base map centered on Brazil
            m = folium.Map(location=[-15.7801, -47.9292], zoom_start=4)
            
            # Create marker cluster
            marker_cluster = MarkerCluster().add_to(m)
            
            # Create colormap
            colormap = cm.LinearColormap(
                colors=['red', 'yellow', 'green'],
                vmin=0,
                vmax=100
            )
            
            # Add markers for each station
            for level, data in availability_data.items():
                for station, stats in data.items():
                    if station in station_coords:
                        lat, lon = station_coords[station]
                        availability = stats['availability_percentage']
                        
                        # Create popup content
                        popup_content = f"""
                        <b>Station:</b> {station}<br>
                        <b>Level:</b> {level}<br>
                        <b>Availability:</b> {availability:.1f}%<br>
                        <b>Days with Data:</b> {stats['days_with_data']}<br>
                        <b>Avg Measurements/Day:</b> {stats['avg_measurements_per_day']:.1f}
                        """
                        
                        # Create marker
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            popup=folium.Popup(popup_content, max_width=300),
                            color=colormap(availability),
                            fill=True,
                            fill_color=colormap(availability),
                            fill_opacity=0.7
                        ).add_to(marker_cluster)
            
            # Add colormap to map
            colormap.add_to(m)
            
            # Save map
            output_path = os.path.join(self.output_dir, 'spatial_availability.html')
            m.save(output_path)
            
            self.logger.info(f"Saved spatial availability map to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating spatial availability map: {str(e)}")
            raise

    def plot_availability(self, availability_data):
        """Plot availability data for all stations."""
        plt.figure(figsize=(12, 6))
        
        stations = list(availability_data.keys())
        values = [data['availability_percentage'] for data in availability_data.values()]
        
        plt.bar(stations, values)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Availability (%)')
        plt.title('Data Availability by Station')
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, 'availability.png')
        plt.savefig(output_path)
        plt.close()
        
        return output_path

    def plot_monthly_availability(self, availability_data):
        """Plot monthly availability patterns."""
        plt.figure(figsize=(12, 6))
        
        # Group data by month
        monthly_data = {}
        for station, data in availability_data.items():
            if 'monthly_availability' in data:
                monthly_data[station] = data['monthly_availability']
        
        if monthly_data:
            df = pd.DataFrame(monthly_data)
            df.plot(kind='line', marker='o')
            plt.xlabel('Month')
            plt.ylabel('Availability (%)')
            plt.title('Monthly Availability Patterns')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            
            output_path = os.path.join(self.output_dir, 'monthly_availability.png')
            plt.savefig(output_path)
            plt.close()
            
            return output_path
        return None

    def plot_station_comparison(self, availability_data: Dict[str, Dict]) -> None:
        """
        Plot comparison of availability across stations.
        
        Args:
            availability_data: Dictionary containing availability data for each quality level
        """
        try:
            # Check if we have any data
            if not availability_data:
                self.logger.warning("No availability data to plot")
                return
            
            # Create figure
            plt.figure(figsize=(12, 6))
            
            # Extract data for plotting
            stations = []
            availability = []
            
            for level, data in availability_data.items():
                for station, stats in data.items():
                    stations.append(f"{station} ({level})")
                    availability.append(stats['availability_percentage'])
            
            if not stations:
                self.logger.warning("No valid data points to plot")
                return
            
            # Create bar plot
            bars = plt.bar(range(len(stations)), availability)
            
            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom')
            
            # Customize plot
            plt.title('Station Availability Comparison', pad=20)
            plt.xlabel('Station')
            plt.ylabel('Availability (%)')
            plt.xticks(range(len(stations)), stations, rotation=45, ha='right')
            plt.grid(True, axis='y', linestyle='--', alpha=0.7)
            
            # Adjust layout
            plt.tight_layout()
            
            # Save plot
            output_path = os.path.join(self.output_dir, 'station_comparison.png')
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Saved station comparison plot to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating station comparison plot: {str(e)}")
            raise 