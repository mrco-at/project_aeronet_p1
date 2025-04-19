"""
Main script for processing AERONET data and generating visualizations.
"""
import os
import logging
from data_processor import AeronetDataProcessor
from visualizer import AeronetVisualizer
from config import (
    DATA_DIR,
    OUTPUT_DIR,
    START_DATE,
    END_DATE,
    MIN_MEASUREMENTS_PER_DAY,
    MIN_AVAILABILITY_PERCENTAGE
)

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('output/processing.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main function to process AERONET data and generate visualizations."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Initialize data processor
        processor = AeronetDataProcessor(
            start_date=START_DATE,
            end_date=END_DATE,
            min_data_points=MIN_MEASUREMENTS_PER_DAY,
            min_availability_percentage=MIN_AVAILABILITY_PERCENTAGE
        )
        
        # Process data
        logger.info("Processing AERONET data...")
        availability_data = processor.process_data()
        
        # Log empty files and errors
        empty_files = processor.get_empty_files()
        if empty_files:
            logger.warning(f"Found {len(empty_files)} empty files")
            for file in empty_files:
                logger.warning(f"Empty file: {file}")
        
        errors = processor.get_errors()
        if errors:
            logger.warning(f"Found {len(errors)} errors during processing")
            for error in errors:
                logger.warning(f"Error: {error}")
        
        # Initialize visualizer
        visualizer = AeronetVisualizer(output_dir=OUTPUT_DIR)
        
        # Generate visualizations
        logger.info("Generating visualizations...")
        
        # Plot availability comparison
        comparison_plot = visualizer.plot_availability_comparison(availability_data)
        logger.info(f"Generated availability comparison plot: {comparison_plot}")
        
        # Plot spatial availability for each level
        for level in ['level10', 'level15', 'level20']:
            spatial_plot = visualizer.plot_spatial_availability(availability_data, level)
            logger.info(f"Generated spatial availability plot for {level}: {spatial_plot}")
        
        logger.info("Processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        raise

if __name__ == '__main__':
    main() 