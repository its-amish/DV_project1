#!/usr/bin/env python3
"""
Test script to validate semantic filtering on Dolly 15k dataset
Compares keyword-only vs hybrid (keyword+semantic) filtering
"""

import logging
from typing import List, Dict, Tuple
from travel_filter import TravelFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test cases representing borderline travel-related content
TEST_CASES = [
    # Should be caught by both (clear travel keywords)
    {
        'text': "I'm planning a trip to Japan next summer. What are the best places to visit?",
        'expected': True,
        'category': 'Clear travel intent'
    },
    
    # Borderline - should be caught by semantic but not keyword alone
    {
        'text': "What are the best places to spend your summer vacation?",
        'expected': True,
        'category': 'Borderline - weak keywords, strong semantic'
    },
    {
        'text': "How do I prepare for my next adventure overseas?",
        'expected': True,
        'category': 'Borderline - adventure implies travel'
    },
    {
        'text': "I want to explore a new country this year",
        'expected': True,
        'category': 'Borderline - explore + country'
    },
    {
        'text': "What's the best packing strategy for a long journey?",
        'expected': True,
        'category': 'Borderline - journey context'
    },
    
    # Non-travel (should fail both)
    {
        'text': "How do I learn Python programming?",
        'expected': False,
        'category': 'Non-travel - programming'
    },
    {
        'text': "What's the best way to cook pasta?",
        'expected': False,
        'category': 'Non-travel - cooking'
    },
    {
        'text': "Can you explain machine learning algorithms?",
        'expected': False,
        'category': 'Non-travel - ML'
    },
]


def compare_filters() -> None:
    """Compare keyword-only vs hybrid filtering"""
    
    logger.info("=" * 70)
    logger.info("SEMANTIC FILTERING TEST - DOLLY 15K DATASET")
    logger.info("=" * 70)
    
    # Initialize filters
    logger.info("\nInitializing filters...")
    filter_keyword = TravelFilter(min_confidence=0.3, use_semantic=False)
    filter_hybrid = TravelFilter(min_confidence=0.3, use_semantic=True)
    
    stats = {
        'total_tests': len(TEST_CASES),
        'keyword_correct': 0,
        'hybrid_correct': 0,
        'semantic_improvements': 0,
        'cases_with_semantic': 0,
    }
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    
    for idx, test_case in enumerate(TEST_CASES, 1):
        text = test_case['text']
        expected = test_case['expected']
        category = test_case['category']
        
        # Test keyword-only filtering
        is_travel_kw, conf_kw, meta_kw = filter_keyword.is_travel_related(text)
        
        # Test hybrid filtering
        is_travel_hybrid, conf_hybrid, meta_hybrid = filter_hybrid.is_travel_related(text)
        
        # Check accuracy
        kw_correct = is_travel_kw == expected
        hybrid_correct = is_travel_hybrid == expected
        
        if kw_correct:
            stats['keyword_correct'] += 1
        if hybrid_correct:
            stats['hybrid_correct'] += 1
        
        # Track improvements from semantic
        semantic_score = meta_hybrid.get('semantic_score', 0)
        if semantic_score > 0:
            stats['cases_with_semantic'] += 1
            if not is_travel_kw and is_travel_hybrid:
                stats['semantic_improvements'] += 1
        
        # Print result
        print(f"\n{idx}. {category}")
        print(f"   Text: {text[:60]}...")
        print(f"   Expected: {expected}")
        print(f"   Keyword-Only: {is_travel_kw} (confidence: {conf_kw:.3f})")
        print(f"   Hybrid: {is_travel_hybrid} (confidence: {conf_hybrid:.3f}, semantic: {semantic_score:.3f})")
        print(f"   Filter Method: {meta_hybrid.get('filter_method', 'keyword')}")
        
        # Mark if improvement
        if not is_travel_kw and is_travel_hybrid:
            print(f"   ✓ IMPROVEMENT: Semantic caught what keywords missed!")
        elif kw_correct and hybrid_correct:
            print(f"   ✓ Both filters correct")
        elif not kw_correct and hybrid_correct:
            print(f"   ✓ Hybrid improved over keyword-only")
        elif is_travel_kw != is_travel_hybrid:
            print(f"   ! Disagreement between filters")
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print(f"Total Tests: {stats['total_tests']}")
    print(f"Keyword-Only Accuracy: {stats['keyword_correct']}/{stats['total_tests']} ({stats['keyword_correct']/stats['total_tests']*100:.1f}%)")
    print(f"Hybrid Accuracy: {stats['hybrid_correct']}/{stats['total_tests']} ({stats['hybrid_correct']/stats['total_tests']*100:.1f}%)")
    print(f"Cases Using Semantic: {stats['cases_with_semantic']}")
    print(f"Semantic Improvements: {stats['semantic_improvements']}")
    print("=" * 70 + "\n")
    
    # Recommendations
    print("RECOMMENDATIONS FOR DOLLY 15K:")
    if stats['semantic_improvements'] > 2:
        print("✓ Semantic filtering adds significant value - enable for Dolly 15k")
    else:
        print("! Limited semantic improvements - may not be necessary")


def test_confidence_range() -> None:
    """Test that semantic is only applied in 0.3-0.7 confidence range"""
    
    logger.info("\nTesting confidence range behavior...")
    
    filter_hybrid = TravelFilter(min_confidence=0.3, use_semantic=True)
    
    # Test cases at different confidence levels
    test_texts = [
        "I'm flying to Paris tomorrow",  # High keyword score
        "Where should I go this summer?",  # Mid keyword score
        "How to pack efficiently?",  # Low keyword score
    ]
    
    print("\n" + "=" * 70)
    print("CONFIDENCE RANGE TEST")
    print("=" * 70)
    
    for text in test_texts:
        is_travel, confidence, metadata = filter_hybrid.is_travel_related(text)
        
        print(f"\nText: {text}")
        print(f"  Keyword Score: {metadata['keyword_score']:.3f}")
        print(f"  Combined Score: {metadata['combined_score']:.3f}")
        print(f"  Semantic Score: {metadata['semantic_score']:.3f}")
        print(f"  Final Score: {metadata['final_score']:.3f}")
        print(f"  Filter Method: {metadata['filter_method']}")
        print(f"  Is Travel: {is_travel}")


if __name__ == '__main__':
    compare_filters()
    test_confidence_range()
    logger.info("Test completed successfully!")
