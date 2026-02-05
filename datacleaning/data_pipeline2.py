"""
Data Pipeline
Orchestrates the complete workflow: Load → Filter → Categorize → Export
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
import re

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
        
        # High confidence to filter garbage
        self.filter_keyword_only = TravelFilter(min_confidence=0.45, use_semantic=False)
        self.filter_hybrid = TravelFilter(min_confidence=0.45, use_semantic=True)
        
        self.categorizer = TravelCategorizer()
        self.all_records = []
        self.travel_records = []
        self.categorized_records = []
        
        self.semantic_enabled_datasets = ['dolly', 'sharegpt', 'sharegpt_parquet']  
        
    def load_data(self, dataset_names: List[str], limit: Optional[int] = None) -> None:
        """Load data from specified datasets"""
        logger.info(f"Starting data loading for: {dataset_names} (Limit: {limit})")
        
        for record in self.loader.batch_load_datasets(dataset_names, limit=limit):
            self.all_records.append(record)
        
        logger.info(f"Loaded {len(self.all_records)} total records")
    
    def filter_travel_data(self) -> None:
        """Filter records for travel-related content"""
        logger.info("Starting travel data filtering...")
        
        for record in tqdm(self.all_records, desc="Filtering"):
            dataset_name = record.get('source_dataset', '').lower()
            
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
        
        logger.info(f"Filtered to {len(self.travel_records)} travel-related records")
    
    def categorize_travel_data(self) -> None:
        """Categorize travel records"""
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
            9: "Travel Services & Infrastructure",
            10: "Other"
        }
        return categories.get(category_id, "Unknown")
    
    def _extract_prompt(self, text: str) -> str:
        """Extracts the human prompt, removing the AI answer."""
        
        # CORRECTED: No inline flags (?i) here
        patterns = [
            r"\bSure,", r"\bCertainly,", r"\bHere is\b", r"\bHere are\b",
            r"\bHere's\b", r"\bI'd be happy\b", r"\bI can help\b", r"\bAs an AI\b",
            r"\bThe following\b", r"\bBelow is\b", r"\n1\.", 
            r"(?<=[a-z\?])\s+1\.\s+(?=[A-Z])", r"(?<=:)\s+(?=[A-Z])"
        ]
        combined_pattern = "|".join(patterns)
        
        # CORRECTED: flag passed as argument
        match = re.search(combined_pattern, text, flags=re.IGNORECASE)
        
        return text[:match.start()].strip() if match else text

    def export_to_csv(self, filename: str = 'travel_data.csv') -> None:
        """Export categorized records to CSV with CLEANED PROMPTS only."""
        ensure_directories()
        
        logger.info("Preparing data for CSV export and cleaning prompts...")
        
        export_records = []
        skipped_count = 0
        
        for record in self.categorized_records:
            original_text = record.get('text', '')
            cleaned_prompt = self._extract_prompt(original_text)
            
            if len(cleaned_prompt) < 15:
                skipped_count += 1
                continue

            export_records.append({
                'id': len(export_records) + 1,
                'text': cleaned_prompt,
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
        logger.info(f"Skipped {skipped_count} records (too short/empty)")
        
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
        
        for record in self.categorized_records:
            category = record.get('travel_category', 'Unknown')
            metadata['category_distribution'][category] = metadata['category_distribution'].get(category, 0) + 1
            source = record.get('source_dataset', 'Unknown')
            metadata['source_distribution'][source] = metadata['source_distribution'].get(source, 0) + 1
        
        if self.travel_records:
            avg_confidence = sum(r.get('confidence_score', 0) for r in self.travel_records) / len(self.travel_records)
            metadata['average_confidence_score'] = round(avg_confidence, 3)
        
        if self.categorized_records:
            avg_cat_confidence = sum(r.get('category_confidence', 0) for r in self.categorized_records) / len(self.categorized_records)
            metadata['average_category_confidence'] = round(avg_cat_confidence, 3)
        
        metadata_path = METADATA_DIR / 'processing_metadata.json'
        save_json(metadata, metadata_path)
        logger.info(f"Exported metadata to {metadata_path}")
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
        print("=" * 60 + "\n")
    
    def run(self, dataset_names: List[str], output_filename: str = 'travel_data.csv', limit: Optional[int] = None) -> None:
        """Run complete pipeline with optional limit"""
        logger.info(f"Starting DVP1 Data Pipeline... (Limit: {limit})")
        self.load_data(dataset_names, limit=limit)
        self.filter_travel_data()
        self.categorize_travel_data()
        csv_path = self.export_to_csv(output_filename)
        self.export_metadata()
        logger.info(f"Pipeline completed! Results saved to {csv_path}")


def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    pipeline = DataPipeline()
    
    datasets_to_process = [
        'sharegpt_parquet'
    ]
    
    pipeline.run(datasets_to_process, output_filename='cleaned_test_prompts.csv', limit=90000)


if __name__ == '__main__':
    main()