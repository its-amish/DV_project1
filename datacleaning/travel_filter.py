"""
Travel Data Filter
Identifies travel-related content using keyword matching and semantic analysis
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from collections import Counter
import numpy as np

from utils import TRAVEL_ONTOLOGY, normalize_text

try:
    from sentence_transformers import SentenceTransformer, util
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class TravelFilter:
    """Filter to identify travel-related records"""
    
    def __init__(self, min_confidence: float = 0.3, use_semantic: bool = False):
        """
        Initialize filter with confidence threshold
        
        Args:
            min_confidence: Minimum confidence score (0-1) to classify as travel-related
            use_semantic: Whether to use semantic filtering for borderline cases
        """
        self.min_confidence = min_confidence
        self.use_semantic = use_semantic and SEMANTIC_AVAILABLE
        self.keyword_weights = self._build_keyword_weights()
        self.phrase_patterns = self._build_phrase_patterns()
        
        # Initialize semantic model if enabled
        self.semantic_model = None
        self.travel_embeddings = None
        if self.use_semantic:
            self._init_semantic_model()
    
    def _init_semantic_model(self):
        """Initialize sentence transformer model for semantic matching"""
        try:
            logger.info("Loading semantic model (all-MiniLM-L6-v2)...")
            self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create reference embeddings for ACTUAL travel content (intent-focused)
            travel_concepts = [
                "planning a trip to visit a new city",
                "booking a hotel for my vacation",
                "what are the best places to travel",
                "I want to travel to Paris",
                "how do I get a tourist visa",
                "packing list for my holiday",
                "best tourist attractions to visit",
                "booking a flight for my trip",
                "travel tips for backpackers",
                "itinerary for a 5 day vacation",
                "where should I go on vacation",
                "recommend travel destinations",
            ]
            self.travel_embeddings = self.semantic_model.encode(travel_concepts, convert_to_tensor=True)
            logger.info("Semantic model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load semantic model: {e}")
            self.use_semantic = False
        
    def _build_keyword_weights(self) -> Dict[str, Tuple[str, float]]:
        """Build keyword dictionary with category and weight"""
        weights = {}
        
        # High priority keywords (weight: 1.0)
        high_priority = {
            'itinerary_building': 1.0,
            'transportation': 0.9,
            'accommodation': 0.9,
        }
        
        # Medium priority keywords (weight: 0.7)
        medium_priority = {
            'logistics_safety': 0.7,
            'financial_budget': 0.7,
            'activities': 0.7,
        }
        
        # Low priority keywords (weight: 0.5)
        low_priority = {
            'discovery_phrases': 0.5,
            'planning_phrases': 0.6,
            'special_keywords': 0.6,
        }
        
        for category, weight in high_priority.items():
            for keyword in TRAVEL_ONTOLOGY.get(category, []):
                weights[keyword.lower()] = (category, weight)
        
        for category, weight in medium_priority.items():
            for keyword in TRAVEL_ONTOLOGY.get(category, []):
                weights[keyword.lower()] = (category, weight)
        
        for category, weight in low_priority.items():
            for keyword in TRAVEL_ONTOLOGY.get(category, []):
                weights[keyword.lower()] = (category, weight)
        
        return weights
    
    def _build_phrase_patterns(self) -> List[re.Pattern]:
        """Build regex patterns for multi-word phrases"""
        patterns = []
        
        # Common travel phrases
        travel_phrases = [
            r'traveling\s+to',
            r'trip\s+to',
            r'visit\s+\w+',
            r'vacation\s+in',
            r'holiday\s+in',
            r'tour\s+of',
            r'explore\s+\w+',
            r'travel\s+guide',
            r'travel\s+tips',
            r'tourist\s+attractions',
            r'best\s+places\s+to',
            r'how\s+to\s+get\s+to',
            r'getting\s+around',
        ]
        
        for phrase in travel_phrases:
            patterns.append(re.compile(phrase, re.IGNORECASE))
        
        return patterns
    
    def is_travel_related(self, text: str) -> Tuple[bool, float, Dict]:
        """
        Determine if text is travel-related using hybrid approach
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (is_travel, confidence_score, metadata)
        """
        if not text or len(text.strip()) < 10:
            return False, 0.0, {}
        
        normalized_text = normalize_text(text)
        metadata = {
            'matched_keywords': [],
            'matched_categories': [],
            'phrase_matches': 0,
            'keyword_score': 0.0,
            'phrase_score': 0.0,
            'combined_score': 0.0,
            'semantic_score': 0.0,
            'final_score': 0.0,
            'filter_method': 'keyword',
        }
        
        # Check keywords
        keyword_score, keyword_data = self._score_keywords(normalized_text)
        metadata['matched_keywords'] = keyword_data['keywords']
        metadata['matched_categories'] = keyword_data['categories']
        metadata['keyword_score'] = keyword_score
        
        # Check phrases
        phrase_score = self._score_phrases(normalized_text)
        metadata['phrase_matches'] = phrase_score['count']
        metadata['phrase_score'] = phrase_score['score']
        
        # Combined scoring (weighted average)
        combined_score = (keyword_score * 0.7) + (phrase_score['score'] * 0.3)
        metadata['combined_score'] = combined_score
        
        # Use semantic filtering - balance precision and recall
        final_score = combined_score
        if self.use_semantic:
            semantic_score = self._semantic_score(text)
            metadata['semantic_score'] = semantic_score
            metadata['filter_method'] = 'hybrid'
            
            # Strong keyword match (>= 0.4): still need some semantic confirmation
            # Medium keyword match (0.1-0.4): use hybrid scoring
            # Weak keyword match (< 0.1): rely on semantic
            if combined_score >= 0.4:
                # Strong keywords - but reject if semantic shows no travel intent
                if semantic_score < 0.15:
                    # Keywords matched but content isn't travel-focused
                    final_score = combined_score * 0.5  # Heavily penalize
                else:
                    final_score = (combined_score * 0.8) + (semantic_score * 0.2)
            elif combined_score >= 0.1:
                # Medium keywords - hybrid approach
                if semantic_score < 0.1:
                    final_score = 0.0
                else:
                    final_score = (combined_score * 0.55) + (semantic_score * 0.45)
            else:
                # Weak/no keywords - need semantic confirmation
                if semantic_score >= 0.28:
                    final_score = semantic_score * 0.95
                else:
                    final_score = 0.0
        
        metadata['final_score'] = final_score
        is_travel = final_score >= self.min_confidence
        
        return is_travel, final_score, metadata
    
    def _score_keywords(self, text: str) -> Tuple[float, Dict]:
        """Score text based on keyword matches with WHOLE WORD matching"""
        text_lower = text.lower()
        matched_keywords = []
        categories = Counter()
        total_weight = 0.0
        
        for keyword, (category, weight) in self.keyword_weights.items():
            keyword_lower = keyword.lower()
            
            # Use word boundary regex to match WHOLE WORDS only
            # This prevents "inn" matching "winning" or "train" matching "trained"
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, text_lower):
                matched_keywords.append(keyword)
                categories[category] += 1
                total_weight += weight
        
        # Normalize score (0-1) - 2 good matches = 1.0
        keyword_score = min(total_weight / 1.5, 1.0)
        
        return keyword_score, {
            'keywords': list(set(matched_keywords)),
            'categories': dict(categories)
        }
    
    def _score_phrases(self, text: str) -> Dict:
        """Score text based on phrase patterns"""
        phrase_count = 0
        
        for pattern in self.phrase_patterns:
            matches = pattern.findall(text)
            phrase_count += len(matches)
        
        # Normalize phrase score (max 5 phrases = 1.0)
        phrase_score = min(phrase_count / 5.0, 1.0)
        
        return {
            'count': phrase_count,
            'score': phrase_score
        }
    
    def _semantic_score(self, text: str) -> float:
        """
        Calculate semantic similarity to travel concepts using embeddings
        
        Args:
            text: Text to analyze
            
        Returns:
            Confidence score 0-1 based on semantic similarity
        """
        if not self.use_semantic or self.semantic_model is None or self.travel_embeddings is None:
            return 0.0
        
        try:
            # Encode input text
            text_embedding = self.semantic_model.encode(text, convert_to_tensor=True)
            
            # Calculate cosine similarities
            similarities = util.pytorch_cos_sim(text_embedding, self.travel_embeddings)
            
            # Get average similarity score
            avg_similarity = float(similarities.mean().cpu().item())
            
            # Normalize to 0-1 range
            semantic_score = min(max(avg_similarity, 0.0), 1.0)
            
            return semantic_score
        except Exception as e:
            # Fail gracefully
            return 0.0
    
    def batch_filter(self, records: List[Dict], text_field: str = 'text') -> Tuple[List[Dict], Dict]:
        """
        Filter batch of records
        
        Args:
            records: List of record dictionaries
            text_field: Name of text field in records
            
        Returns:
            Tuple of (filtered_records, statistics)
        """
        filtered_records = []
        stats = {
            'total': len(records),
            'travel_related': 0,
            'average_confidence': 0.0,
            'category_distribution': Counter(),
            'filter_methods': {'keyword': 0, 'hybrid': 0},
        }
        
        confidence_scores = []
        
        for record in records:
            if text_field not in record:
                continue
            
            text = record.get(text_field, '')
            is_travel, confidence, metadata = self.is_travel_related(text)
            
            if is_travel:
                filtered_records.append({
                    **record,
                    'is_travel': True,
                    'confidence_score': confidence,
                    'travel_metadata': metadata
                })
                stats['travel_related'] += 1
                confidence_scores.append(confidence)
                
                # Track filter method
                filter_method = metadata.get('filter_method', 'keyword')
                stats['filter_methods'][filter_method] += 1
                
                # Track category distribution
                for category in metadata.get('matched_categories', {}):
                    stats['category_distribution'][category] += 1
        
        if confidence_scores:
            stats['average_confidence'] = sum(confidence_scores) / len(confidence_scores)
        
        return filtered_records, stats
