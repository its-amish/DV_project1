"""
Data Pipeline
Orchestrates the complete workflow: Load → Filter → Categorize → Export
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List
from tqdm import tqdm

from utils import ensure_directories, log_stats, TRAVEL_DIR, METADATA_DIR, save_json, PROJECT_ROOT
from load_datasets import DatasetLoader
from travel_filter import TravelFilter
from categorizer import TravelCategorizer

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrate data processing pipeline"""
    
    def __init__(self):
        """Initialize pipeline components"""
        self.loader = DatasetLoader()
        self.filter_keyword_only = TravelFilter(min_confidence=0.25, use_semantic=False)
        self.filter_hybrid = TravelFilter(min_confidence=0.25, use_semantic=True)
        self.categorizer = TravelCategorizer()
        self.all_records = []
        self.travel_records = []
        self.categorized_records = []
        
        # Dataset-specific semantic filtering settings
        self.semantic_enabled_datasets = ['dolly']  # Only Dolly uses semantic initially
        
    def load_data(self, dataset_names: List[str]) -> None:
        """
        Load data from specified datasets
        
        Args:
            dataset_names: List of dataset names to load
        """
        logger.info(f"Starting data loading for: {dataset_names}")
        
        for record in self.loader.batch_load_datasets(dataset_names):
            self.all_records.append(record)
        
        logger.info(f"Loaded {len(self.all_records)} total records")
    
    def filter_travel_data(self) -> None:
        """Filter records for travel-related content with dataset-specific settings"""
        logger.info("Starting travel data filtering...")
        
        for record in tqdm(self.all_records, desc="Filtering"):
            dataset_name = record.get('source_dataset', '').lower()
            
            # Choose appropriate filter based on dataset
            # Check if any semantic dataset name is contained in the record's dataset name
            use_semantic = any(sd in dataset_name for sd in self.semantic_enabled_datasets)
            if use_semantic:
                filter_instance = self.filter_hybrid
            else:
                filter_instance = self.filter_keyword_only
            
            is_travel, confidence, metadata = filter_instance.is_travel_related(record['text'])
            
            if is_travel:
                record['is_travel'] = True
                record['confidence_score'] = confidence
                record['travel_metadata'] = metadata
                self.travel_records.append(record)
        
        # Log statistics
        for dataset_name in set(r['source_dataset'] for r in self.all_records):
            total = sum(1 for r in self.all_records if r['source_dataset'] == dataset_name)
            travel = sum(1 for r in self.travel_records if r['source_dataset'] == dataset_name)
            is_semantic = any(sd in dataset_name.lower() for sd in self.semantic_enabled_datasets)
            filter_type = "hybrid (keyword+semantic)" if is_semantic else "keyword-only"
            log_stats(total, travel, dataset_name, f"[{filter_type}]")
        
        logger.info(f"Filtered to {len(self.travel_records)} travel-related records")
    
    def categorize_travel_data(self) -> None:
        """Categorize travel records into predefined categories"""
        logger.info("Starting travel data categorization...")
        
        for record in tqdm(self.travel_records, desc="Categorizing"):
            category_id, confidence, details = self.categorizer.categorize(record)
            
            record['travel_category_id'] = category_id
            record['travel_category'] = self._get_category_name(category_id)
            record['category_confidence'] = confidence
            record['category_details'] = details
            
            self.categorized_records.append(record)
        
        logger.info(f"Categorized {len(self.categorized_records)} records")
    
    def _get_category_name(self, category_id: int) -> str:
        """Get category name from ID"""
        categories = {
            1: "Places & Destinations",
            2: "Transportation",
            3: "Accommodation",
            4: "Trip Planning",
            5: "Travel Costs & Budgeting",
            6: "Tourist Activities & Experiences",
            7: "Travel Tips & Advice",
            8: "Food & Culture (Travel Context)",
            9: "Travel Services & Infrastructure"
        }
        return categories.get(category_id, "Unknown")
    
    def export_to_csv(self, filename: str = 'travel_data.csv') -> None:
        """
        Export categorized records to CSV
        
        Args:
            filename: Output CSV filename
        """
        ensure_directories()
        
        logger.info("Preparing data for CSV export...")
        
        export_records = []
        for record in self.categorized_records:
            export_records.append({
                'id': len(export_records) + 1,
                'text': record.get('text', ''),
                'source_dataset': record.get('source_dataset', ''),
                'confidence_score': round(record.get('confidence_score', 0), 3),
                'travel_category_id': record.get('travel_category_id', 0),
                'travel_category': record.get('travel_category', ''),
                'category_confidence': round(record.get('category_confidence', 0), 3),
                'matched_keywords': ', '.join(record.get('travel_metadata', {}).get('matched_keywords', [])),
                'matched_categories': ', '.join(record.get('travel_metadata', {}).get('matched_categories', {}).keys()),
            })
        
        df = pd.DataFrame(export_records)
        output_path = TRAVEL_DIR / filename
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Exported {len(export_records)} records to {output_path}")
        
        return output_path
    
    def export_metadata(self) -> None:
        """Export processing metadata and statistics"""
        ensure_directories()
        
        metadata = {
            'total_records_loaded': len(self.all_records),
            'travel_records_found': len(self.travel_records),
            'travel_percentage': (len(self.travel_records) / len(self.all_records) * 100) if self.all_records else 0,
            'categorized_records': len(self.categorized_records),
            'category_distribution': {},
            'source_distribution': {},
            'average_confidence_score': 0,
            'average_category_confidence': 0,
        }
        
        # Calculate distribution stats
        for record in self.categorized_records:
            category = record.get('travel_category', 'Unknown')
            metadata['category_distribution'][category] = metadata['category_distribution'].get(category, 0) + 1
            
            source = record.get('source_dataset', 'Unknown')
            metadata['source_distribution'][source] = metadata['source_distribution'].get(source, 0) + 1
        
        # Calculate average confidence scores
        if self.travel_records:
            avg_confidence = sum(r.get('confidence_score', 0) for r in self.travel_records) / len(self.travel_records)
            metadata['average_confidence_score'] = round(avg_confidence, 3)
        
        if self.categorized_records:
            avg_cat_confidence = sum(r.get('category_confidence', 0) for r in self.categorized_records) / len(self.categorized_records)
            metadata['average_category_confidence'] = round(avg_cat_confidence, 3)
        
        metadata_path = METADATA_DIR / 'processing_metadata.json'
        save_json(metadata, metadata_path)
        logger.info(f"Exported metadata to {metadata_path}")
        
        # Print summary
        self._print_summary(metadata)
    
    def _print_summary(self, metadata: dict) -> None:
        """Print processing summary"""
        print("\n" + "=" * 60)
        print("TRAVEL DATA SCRAPING PIPELINE - SUMMARY")
        print("=" * 60)
        print(f"Total Records Loaded: {metadata['total_records_loaded']}")
        print(f"Travel Records Found: {metadata['travel_records_found']}")
        print(f"Travel Percentage: {metadata['travel_percentage']:.2f}%")
        print(f"Avg Confidence Score: {metadata['average_confidence_score']:.3f}")
        print(f"Avg Category Confidence: {metadata['average_category_confidence']:.3f}")
        
        print("\nCategory Distribution:")
        for category, count in metadata['category_distribution'].items():
            percentage = (count / metadata['categorized_records'] * 100) if metadata['categorized_records'] > 0 else 0
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        print("\nSource Distribution:")
        for source, count in metadata['source_distribution'].items():
            percentage = (count / metadata['categorized_records'] * 100) if metadata['categorized_records'] > 0 else 0
            print(f"  {source}: {count} ({percentage:.1f}%)")
        print("=" * 60 + "\n")
    
    def run(self, dataset_names: List[str], output_filename: str = 'travel_data.csv') -> None:
        """
        Run complete pipeline
        
        Args:
            dataset_names: List of dataset names to process
            output_filename: Name of the output CSV file
        """
        logger.info("Starting DVP1 Data Pipeline...")
        
        # Step 1: Load data
        self.load_data(dataset_names)
        
        # Step 2: Filter for travel data
        self.filter_travel_data()
        
        # Step 3: Categorize records
        self.categorize_travel_data()
        
        # Step 4: Export results
        csv_path = self.export_to_csv(output_filename)
        self.export_metadata()
        
        logger.info(f"Pipeline completed! Results saved to {csv_path}")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize pipeline
    pipeline = DataPipeline()
    
    # Define datasets to process (in priority order)
    datasets_to_process = [
        'dolly',      # Priority 1
        # 'ign',        # Priority 2
        # 'ultrachat',  # Priority 3
        # 'vicuna',     # Priority 4

        # 'sharegpt'

    ]
    
    # Run pipeline
    pipeline.run(datasets_to_process)


if __name__ == '__main__':
    main()
