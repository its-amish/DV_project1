"""
Utility functions for DVP1 Travel Data Scraping Project
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'
METADATA_DIR = DATA_DIR / 'metadata'
TRAVEL_DIR = PROCESSED_DIR / 'travel_only'

# Travel-related keywords and ontology - Expanded domains
# NOTE: Only include keywords that are UNAMBIGUOUSLY travel-related
# Avoid: "tour" (factory tour), "train" (training), "inn" (winning), "stay" (generic), "visit" (generic)
TRAVEL_ONTOLOGY = {
    'itinerary_building': [
        'itinerary', 'travel itinerary', 'trip itinerary', 'day-by-day',
        'travel schedule', 'stopover', 'layover', 'road trip', 'travel plan',
        'trip planner', 'weekend getaway', 'day trip', 'multi-city trip',
        '3-day trip', '5-day trip', '7-day trip', 'week trip', 'two-week'
    ],
    'logistics_safety': [
        'travel visa', 'tourist visa', 'passport', 'customs',
        'travel insurance', 'travel vaccine', 'vaccination', 'travel safety',
        'travel advisory', 'entry requirements', 'embassy', 'consulate',
        'border crossing', 'travel documents', 'immigration'
    ],
    'financial_budget': [
        'travel budget', 'trip cost', 'travel expenses', 'travel rewards',
        'airline miles', 'frequent flyer', 'travel deal', 'cheap flights',
        'budget travel', 'all-inclusive', 'travel savings',
        'affordable travel', 'luxury travel', 'travel credit card'
    ],
    'transportation': [
        'flights to', 'book a flight', 'airline ticket', 'airport', 'airplane', 'plane ticket',
        'railway station', 'train station', 'car rental', 'rent a car',
        'ferry', 'cruise', 'cruise ship', 'boarding pass', 'airport transfer',
        'bus travel', 'transportation hub', 'public transit'
    ],
    'accommodation': [
        'hotel', 'hotels', 'resort', 'resorts', 'airbnb', 'hostel', 'hostels',
        'motel', 'lodging', 'vacation rental', 'guest house',
        'check-in', 'check-out', 'hotel booking',
        'accommodation', 'where to stay', 'book a room'
    ],
    'destinations': [
        'destination', 'destinations', 'places to visit', 'must visit',
        'tourist attraction', 'attractions', 'landmark', 'landmarks',
        'famous places', 'popular places', 'hidden gems', 'off the beaten path',
        'bucket list', 'travel to', 'trip to', 'travel destination'
    ],
    'planning_phrases': [
        'plan a trip', 'plan a vacation', 'plan a holiday', 'planning to travel',
        'trip planning', 'vacation planning', 'travel planning', 'travel guide',
        'packing list', 'travel tips', 'travel advice', 'before you travel',
        'how to travel', 'traveling to', 'going on vacation', 'going on holiday',
        'things to do in', 'what to do in', 'where to go', 'best time to visit'
    ],
    'activities': [
        'sightseeing', 'guided tour', 'city tour', 'walking tour',
        'excursion', 'hiking trail', 'trekking', 'safari', 'snorkeling',
        'scuba diving', 'beach vacation',
        'tourist spot', 'tourist spots'
    ],
    'travel_types': [
        'solo travel', 'solo traveler', 'family vacation', 'family trip',
        'honeymoon', 'backpacking', 'backpacker', 'digital nomad',
        'business travel', 'leisure travel', 'adventure travel', 'eco-tourism',
        'sustainable travel', 'luxury travel', 'budget travel', 'group travel'
    ],
    'geography_travel': [
        'travel abroad', 'overseas travel', 'international travel',
        'domestic travel', 'cross-country', 'road trip'
    ],
    'culture_travel': [
        'local cuisine', 'local food', 'street food', 'traditional food',
        'food tour', 'local culture', 'cultural experience',
        'heritage site', 'historic site', 'historical site',
        'world heritage', 'unesco site'
    ],
    'travel_experience': [
        'travel experience', 'vacation', 'holiday', 'getaway',
        'wanderlust', 'traveler', 'traveller', 'tourist', 'tourism'
    ]
}

TRAVEL_CATEGORIES = {
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

DATASET_INFO = {
    'databricks-dolly-15k': {
        'repo_id': 'databricks/databricks-dolly-15k',
        'fields': ['instruction', 'context', 'response', 'category'],
        'name': 'Dolly 15k'
    },
    'ign-clean-instruct': {
        'repo_id': 'ignmilton/ign_clean_instruct_dataset_500k',
        'fields': ['prompt', 'chosen', 'rejected'],
        'name': 'IGN Clean Instruct 500k'
    },
    'ultrachat': {
        'repo_id': 'openbmb/UltraChat',
        'fields': ['id', 'data'],
        'name': 'UltraChat'
    },
    'sharegpt-vicuna': {
        'repo_id': 'anon8231489123/ShareGPT_Vicuna_unfiltered',
        'fields': ['conversations'],
        'name': 'ShareGPT Vicuna Unfiltered'
    }
}


def ensure_directories():
    """Ensure all required directories exist"""
    for directory in [RAW_DIR, PROCESSED_DIR, TRAVEL_DIR, METADATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    logger.info("All directories verified/created")


def get_travel_keywords() -> List[str]:
    """Get flattened list of all travel keywords"""
    keywords = []
    for category, words in TRAVEL_ONTOLOGY.items():
        keywords.extend(words)
    return keywords


def save_json(data: Any, filepath: Path) -> None:
    """Save data as JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON: {filepath}")


def load_json(filepath: Path) -> Any:
    """Load JSON data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"Loaded JSON: {filepath}")
    return data


def safe_extract_text(data: Dict, fields: List[str]) -> Optional[str]:
    """
    Safely extract text from nested dictionaries
    Tries multiple field combinations
    """
    for field in fields:
        if field in data:
            value = data[field]
            if isinstance(value, str) and value.strip():
                return value
            elif isinstance(value, list) and value:
                # Handle list of dictionaries (like conversations)
                if isinstance(value[0], dict) and 'value' in value[0]:
                    return ' '.join([item.get('value', '') for item in value if isinstance(item, dict)])
                elif isinstance(value[0], str):
                    return ' '.join(value)
    return None


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""
    return text.lower().strip()


def log_stats(total: int, travel_related: int, source: str, filter_type: str = "") -> None:
    """
    Log processing statistics
    
    Args:
        total: Total records processed
        travel_related: Records identified as travel-related
        source: Source dataset name
        filter_type: Optional filter type description (e.g., "[hybrid (keyword+semantic)]")
    """
    percentage = (travel_related / total * 100) if total > 0 else 0
    logger.info(f"{source}: {travel_related}/{total} records ({percentage:.2f}%) are travel-related {filter_type}")
