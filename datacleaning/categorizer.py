"""
Travel Data Categorizer
Assigns travel records to one of 9 predefined categories
"""

import logging
from typing import Dict, List, Tuple
from collections import defaultdict

from utils import TRAVEL_ONTOLOGY, TRAVEL_CATEGORIES, normalize_text

logger = logging.getLogger(__name__)


class TravelCategorizer:
    """Categorize travel records into predefined categories"""
    
    def __init__(self):
        """Initialize categorizer with category mappings"""
        self.category_keywords = self._build_category_keywords()
        
    def _build_category_keywords(self) -> Dict[int, List[str]]:
        """Build keyword mappings for each category"""
        category_map = {
            1: {  # Places & Destinations
                'keywords': [
                    'destination', 'city', 'country', 'region', 'place', 'location', 'landmark',
                    'attraction', 'poi', 'museum', 'monument', 'park', 'beach', 'mountain',
                    'island', 'town', 'village', 'area', 'zone', 'district', 'explore'
                ],
                'ontology_categories': ['discovery_phrases', 'activities']
            },
            2: {  # Transportation
                'keywords': [
                    'flight', 'train', 'bus', 'car', 'ferry', 'metro', 'subway', 'taxi',
                    'airline', 'boarding', 'ticket', 'seat', 'luggage', 'baggage', 'airport',
                    'station', 'terminal', 'transport', 'ride', 'ride-share', 'vehicle',
                    'rental', 'transit', 'route', 'connect'
                ],
                'ontology_categories': ['transportation']
            },
            3: {  # Accommodation
                'keywords': [
                    'hotel', 'resort', 'hostel', 'airbnb', 'accommodation', 'lodging', 'motel',
                    'guest', 'room', 'suite', 'villa', 'apartment', 'booking', 'reservation',
                    'check-in', 'check-out', 'night', 'stay', 'bed', 'breakfast'
                ],
                'ontology_categories': ['accommodation']
            },
            4: {  # Trip Planning
                'keywords': [
                    'itinerary', 'plan', 'schedule', 'route', 'day-by-day', 'timeline', 'trip',
                    'journey', 'adventure', 'vacation', 'holiday', 'tour', 'guide', 'map',
                    'stopover', 'layover', 'stoppage'
                ],
                'ontology_categories': ['itinerary_building', 'planning_phrases']
            },
            5: {  # Travel Costs & Budgeting
                'keywords': [
                    'cost', 'price', 'budget', 'expensive', 'cheap', 'affordable', 'fee',
                    'discount', 'deal', 'offer', 'payment', 'currency', 'exchange', 'rate',
                    'points', 'miles', 'rewards', 'loyalty', 'credit', 'card', 'pay'
                ],
                'ontology_categories': ['financial_budget']
            },
            6: {  # Tourist Activities & Experiences
                'keywords': [
                    'activity', 'adventure', 'experience', 'tour', 'sightseeing', 'hiking',
                    'dining', 'restaurant', 'food', 'cuisine', 'shopping', 'nightlife',
                    'entertainment', 'show', 'concert', 'event', 'sport', 'game', 'excursion',
                    'photography', 'trek', 'safari'
                ],
                'ontology_categories': ['activities', 'special_keywords']
            },
            7: {  # Travel Tips & Advice
                'keywords': [
                    'tip', 'advice', 'recommendation', 'suggestion', 'guide', 'how', 'should',
                    'best', 'better', 'prefer', 'avoid', 'safety', 'warning', 'caution',
                    'requirement', 'visa', 'passport', 'document', 'permission', 'insurance',
                    'vaccine', 'health', 'etiquette', 'culture', 'local', 'custom'
                ],
                'ontology_categories': ['logistics_safety']
            },
            8: {  # Food & Culture (Travel Context)
                'keywords': [
                    'food', 'cuisine', 'restaurant', 'dining', 'meal', 'dish', 'culture',
                    'cultural', 'tradition', 'local', 'authentic', 'street food', 'flavour',
                    'taste', 'recipe', 'cooking', 'kitchen', 'cuisine', 'market', 'bazaar',
                    'festival', 'celebration', 'custom', 'tradition', 'heritage', 'museum'
                ],
                'ontology_categories': ['activities', 'discovery_phrases']
            },
            9: {  # Travel Services & Infrastructure
                'keywords': [
                    'service', 'infrastructure', 'facility', 'amenity', 'internet', 'wifi',
                    'atm', 'bank', 'currency', 'exchange', 'hospital', 'medical', 'doctor',
                    'police', 'emergency', 'help', 'support', 'customer', 'assistance',
                    'office', 'center', 'counter', 'desk', 'information', 'tourist', 'helpline'
                ],
                'ontology_categories': ['logistics_safety']
            }
        }
        
        return category_map
    
    def categorize(self, record: Dict) -> Tuple[int, float, Dict]:
        """
        Categorize a travel record
        
        Args:
            record: Record with text and travel_metadata
            
        Returns:
            Tuple of (category_id, confidence, categorization_details)
        """
        text = record.get('text', '')
        travel_metadata = record.get('travel_metadata', {})
        
        if not text:
            return 0, 0.0, {'error': 'No text provided'}
        
        normalized_text = normalize_text(text)
        category_scores = defaultdict(float)
        keyword_matches = defaultdict(list)
        
        # Score each category
        for category_id, category_info in self.category_keywords.items():
            keywords = category_info.get('keywords', [])
            
            for keyword in keywords:
                if keyword in normalized_text or normalized_text.find(keyword) != -1:
                    category_scores[category_id] += 1.0
                    keyword_matches[category_id].append(keyword)
        
        # Use travel_metadata for additional scoring
        matched_categories = travel_metadata.get('matched_categories', {})
        for ontology_cat, count in matched_categories.items():
            for cat_id, cat_info in self.category_keywords.items():
                if ontology_cat in cat_info.get('ontology_categories', []):
                    category_scores[cat_id] += count * 0.5
        
        # Determine best category
        if not category_scores:
            return 4, 0.5, {  # Default to Trip Planning
                'reason': 'No specific keywords matched, defaulting to Trip Planning',
                'matched_keywords': [],
                'all_scores': {}
            }
        
        # Normalize scores
        max_score = max(category_scores.values())
        normalized_scores = {
            cat_id: score / max_score for cat_id, score in category_scores.items()
        }
        
        best_category = max(normalized_scores, key=normalized_scores.get)
        best_confidence = normalized_scores[best_category]
        
        return best_category, best_confidence, {
            'category_name': TRAVEL_CATEGORIES.get(best_category, 'Unknown'),
            'all_scores': normalized_scores,
            'matched_keywords': keyword_matches.get(best_category, []),
            'ontology_matches': matched_categories
        }
    
    def batch_categorize(self, records: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Categorize batch of records
        
        Args:
            records: List of travel records
            
        Returns:
            Tuple of (categorized_records, statistics)
        """
        categorized_records = []
        stats = {
            'total': len(records),
            'category_distribution': defaultdict(int),
            'average_confidence': 0.0,
        }
        
        confidence_scores = []
        
        for record in records:
            category_id, confidence, details = self.categorize(record)
            
            categorized_records.append({
                **record,
                'travel_category_id': category_id,
                'travel_category': TRAVEL_CATEGORIES.get(category_id, 'Unknown'),
                'category_confidence': confidence,
                'category_details': details
            })
            
            stats['category_distribution'][TRAVEL_CATEGORIES.get(category_id)] += 1
            confidence_scores.append(confidence)
        
        if confidence_scores:
            stats['average_confidence'] = sum(confidence_scores) / len(confidence_scores)
        
        return categorized_records, stats
