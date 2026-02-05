"""
Load datasets from Hugging Face
Downloads and prepares data from multiple sources
"""

import logging
import json
import ast
import numpy as np
from typing import List, Dict, Generator, Optional, Any
from datasets import load_dataset
from tqdm import tqdm

# REMOVED the bad line: "from load_datasets import DatasetLoader"
from utils import DATASET_INFO, safe_extract_text, log_stats

logger = logging.getLogger(__name__)


class DatasetLoader:
    """Load datasets from Hugging Face"""
    
    def __init__(self):
        """Initialize dataset loader"""
        self.loaded_datasets = {}
    
    def load_dolly_15k(self, split: str = 'train') -> Generator[Dict, None, None]:
        """Load Dolly 15k dataset"""
        logger.info(f"Loading Dolly 15k ({split} split)...")
        try:
            dataset = load_dataset('databricks/databricks-dolly-15k', split=split)
            for record in tqdm(dataset, desc="Dolly 15k"):
                instruction = record.get('instruction', '')
                if instruction.strip():
                    yield {
                        'text': instruction.strip(),
                        'source_dataset': 'databricks-dolly-15k',
                        'source_category': record.get('category', ''),
                        'original_fields': record
                    }
        except Exception as e:
            logger.error(f"Error loading Dolly 15k: {e}")
    
    def load_ign_clean_instruct(self, split: str = 'train') -> Generator[Dict, None, None]:
        """Load IGN Clean Instruct"""
        logger.info(f"Loading IGN Clean Instruct ({split} split)...")
        try:
            dataset = load_dataset('ignmilton/ign_clean_instruct_dataset_500k', split=split)
            for record in tqdm(dataset, desc="IGN Clean Instruct"):
                instruction = record.get('instruction', '')
                if instruction.strip():
                    yield {
                        'text': instruction.strip(),
                        'source_dataset': 'ign-clean-instruct-500k',
                        'original_fields': record
                    }
        except Exception as e:
            logger.error(f"Error loading IGN Clean Instruct: {e}")
    
    def load_ultrachat(self, split: str = 'train_sft') -> Generator[Dict, None, None]:
        """Load UltraChat dataset"""
        logger.info(f"Loading UltraChat ({split} split)...")
        try:
            dataset = load_dataset('openbmb/UltraChat', split=split)
            for record in tqdm(dataset, desc="UltraChat"):
                human_text = self._normalize_conversations(record)
                if human_text.strip():
                    yield {
                        'text': human_text.strip(),
                        'source_dataset': 'ultrachat',
                        'original_fields': {'data': record.get('data')}
                    }
        except Exception as e:
            logger.error(f"Error loading UltraChat: {e}")
    
    def load_sharegpt_vicuna(self, split: str = 'train') -> Generator[Dict, None, None]:
        """Load ShareGPT Vicuna Unfiltered dataset"""
        logger.info(f"Loading ShareGPT Vicuna Unfiltered ({split} split)...")
        try:
            dataset = load_dataset(
                'anon8231489123/ShareGPT_Vicuna_unfiltered', 
                data_files='ShareGPT_V3_unfiltered_cleaned_split.json',
                split=split
            )
            for record in tqdm(dataset, desc="ShareGPT Vicuna"):
                human_text = self._normalize_conversations(record)
                if human_text.strip():
                    yield {
                        'text': human_text.strip(),
                        'source_dataset': 'sharegpt-vicuna-unfiltered',
                        'original_fields': record
                    }
        except Exception as e:
            logger.error(f"Error loading ShareGPT Vicuna: {e}")

    def _normalize_conversations(self, record: Dict[str, Any]) -> str:
        """
        Robustly extract ONLY HUMAN PROMPTS handling Dicts, Lists, and Numpy Arrays.
        """
        human_texts = []
        
        # 1. Try 'conversations'
        if 'conversations' in record:
            convs = record['conversations']
            
            # Parsing stringified JSON if needed
            if isinstance(convs, str):
                try:
                    convs = json.loads(convs)
                except:
                    try:
                        convs = ast.literal_eval(convs)
                    except:
                        pass

            # Columnar format (Dict with arrays)
            if isinstance(convs, dict):
                if 'from' in convs and 'value' in convs:
                    roles = convs['from']
                    values = convs['value']
                    
                    # Handle Numpy Arrays
                    if isinstance(roles, (list, tuple, np.ndarray)) and isinstance(values, (list, tuple, np.ndarray)):
                        for r, v in zip(roles, values):
                            if str(r).lower() in ['human', 'user', 'prompter', 'instruction']:
                                if v: human_texts.append(str(v))
            
            # Row format (List of Dicts)
            elif isinstance(convs, list):
                for item in convs:
                    if isinstance(item, dict):
                        role = item.get('from') or item.get('role') or item.get('speaker')
                        val = item.get('value') or item.get('content') or item.get('text')
                        
                        if role and str(role).lower() in ['human', 'user', 'prompter', 'instruction']:
                            if val: human_texts.append(str(val))

        # 2. Fallbacks
        if not human_texts and 'text' in record and record['text']:
            return str(record['text'])

        if not human_texts and 'instruction' in record and record['instruction']:
            return str(record['instruction'])

        return '\n'.join(human_texts)

    def load_sharegpt_parquet(self, split: str = 'train') -> Generator[Dict, None, None]:
        """
        Load ShareGPT data from local PARQUET files.
        """
        logger.info(f"Loading ShareGPT from local Parquet file...")
        try:
            dataset = load_dataset("parquet", data_files={'train': '*.parquet'}, split='train')
            
            for record in tqdm(dataset, desc="ShareGPT Parquet"):
                human_only_text = self._normalize_conversations(record)
                
                if human_only_text and human_only_text.strip():
                    yield {
                        'text': human_only_text.strip(),
                        'source_dataset': 'sharegpt-parquet',
                        'original_fields': record
                    }
        except Exception as e:
            logger.error(f"Error loading Parquet file: {e}")
            logger.error("Ensure a .parquet file exists in the directory.")

    def get_dataset_loader(self, dataset_name: str) -> Optional[Generator]:
        """Get appropriate loader for dataset"""
        loaders = {
            'dolly': self.load_dolly_15k,
            'ign': self.load_ign_clean_instruct,
            'ultrachat': self.load_ultrachat,
            'vicuna': self.load_sharegpt_vicuna,
            'sharegpt': self.load_sharegpt_vicuna, 
            'sharegpt_parquet': self.load_sharegpt_parquet,
        }
        return loaders.get(dataset_name)
    
    def batch_load_datasets(self, dataset_names: List[str], limit: Optional[int] = None) -> Generator[Dict, None, None]:
        """Load multiple datasets sequentially with an optional global limit."""
        total_loaded = 0
        for dataset_name in dataset_names:
            loader = self.get_dataset_loader(dataset_name)
            if loader:
                try:
                    for record in loader():
                        if limit is not None and total_loaded >= limit:
                            logger.info(f"Reached limit of {limit} records. Stopping load.")
                            return
                        yield record
                        total_loaded += 1
                except Exception as e:
                    logger.error(f"Error loading {dataset_name}: {e}")
            else:
                logger.warning(f"Unknown dataset: {dataset_name}")