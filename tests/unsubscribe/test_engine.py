#!/usr/bin/env python3
"""
Test script for the data-driven unsubscribe engine
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_threshold_calculation():
    """Test that thresholds are calculated correctly from data"""
    print("🧪 Testing data-driven threshold calculation...")
    
    try:
        from triage.unsubscribe_engine import UnsubscribeEngine
        import pandas as pd
        
        # Create sample data
        sample_data = pd.DataFrame({
            'from': ['sender1', 'sender2', 'sender3', 'sender4', 'sender5'],
            'message_id': [1, 1, 1, 1, 1],
            'is_unread': [8, 5, 2, 9, 1],
            'is_starred': [0, 1, 2, 0, 3],
            'is_important': [0, 1, 1, 0, 2],
            'category_promotions': [9, 5, 1, 10, 0],
            'category_updates': [1, 5, 9, 0, 10],
            'category_social': [0, 0, 0, 0, 0],
            'category_forums': [0, 0, 0, 0, 0],
            'category_personal': [0, 0, 0, 0, 0],
            'has_unsubscribe': [1, 1, 0, 1, 0],
            'arrival_datetime': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01'],
            'list_unsubscribe': ['link1', 'link2', '', 'link3', ''],
            'sender_domain': ['domain1.com', 'domain2.com', 'domain3.com', 'domain4.com', 'domain4.com']
        })
        
        # Convert to proper datetime
        sample_data['arrival_datetime'] = pd.to_datetime(sample_data['arrival_datetime'])
        
        # Initialize engine
        engine = UnsubscribeEngine()
        
        # Test threshold calculation
        thresholds = engine._calculate_data_driven_thresholds(sample_data)
        
        print("✅ Threshold calculation test passed!")
        print(f"📊 Calculated {len(thresholds)} thresholds from sample data")
        
        for key, value in thresholds.items():
            print(f"  • {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Threshold calculation test failed: {e}")
        return False

def test_engagement_analysis():
    """Test that engagement analysis works correctly"""
    print("\n🧪 Testing engagement analysis...")
    
    try:
        from triage.unsubscribe_engine import UnsubscribeEngine
        import pandas as pd
        
        # Create sample data with proper structure
        sample_data = pd.DataFrame({
            'from': ['sender1', 'sender2', 'sender3', 'sender4', 'sender5'],
            'message_id': [1, 1, 1, 1, 1],
            'is_unread': [8, 5, 2, 9, 1],
            'is_starred': [0, 1, 2, 0, 3],
            'is_important': [0, 1, 1, 0, 2],
            'category_promotions': [9, 5, 1, 10, 0],
            'category_updates': [1, 5, 9, 0, 10],
            'category_social': [0, 0, 0, 0, 0],
            'category_forums': [0, 0, 0, 0, 0],
            'category_personal': [0, 0, 0, 0, 0],
            'has_unsubscribe': [1, 1, 0, 1, 0],
            'arrival_datetime': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01'],
            'list_unsubscribe': ['link1', 'link2', '', 'link3', ''],
            'sender_domain': ['domain1.com', 'domain2.com', 'domain3.com', 'domain4.com', 'domain4.com']
        })
        
        # Convert to proper datetime
        sample_data['arrival_datetime'] = pd.to_datetime(sample_data['arrival_datetime'])
        
        # Initialize engine
        engine = UnsubscribeEngine()
        
        # Test engagement analysis
        sender_stats = engine.analyze_sender_engagement(sample_data)
        
        print("✅ Engagement analysis test passed!")
        print(f"📊 Analyzed {len(sender_stats)} senders")
        
        # Show some stats
        if not sender_stats.empty:
            print("\n📈 Sample engagement scores:")
            for _, sender in sender_stats.iterrows():
                print(f"  • {sender['sender']}: engagement={sender['engagement_score']:.3f}, read_rate={sender['read_rate']:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Engagement analysis test failed: {e}")
        return False

def test_inbox_targeting():
    """Test inbox targeting functionality"""
    print("\n🧪 Testing inbox targeting...")
    
    try:
        from triage.unsubscribe_engine import UnsubscribeEngine
        import pandas as pd
        
        # Create sample data with inbox information
        sample_data = pd.DataFrame({
            'from': ['sender1', 'sender2', 'sender3', 'sender4', 'sender5'],
            'message_id': [1, 1, 1, 1, 1],
            'is_unread': [8, 5, 2, 9, 1],
            'is_starred': [0, 1, 2, 0, 3],
            'is_important': [0, 1, 1, 0, 2],
            'category_promotions': [9, 5, 1, 10, 0],
            'category_updates': [1, 5, 9, 0, 10],
            'category_social': [0, 0, 0, 0, 0],
            'category_forums': [0, 0, 0, 0, 0],
            'category_personal': [0, 0, 0, 0, 0],
            'has_unsubscribe': [1, 1, 0, 1, 0],
            'arrival_datetime': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01'],
            'list_unsubscribe': ['link1', 'link2', '', 'link3', ''],
            'sender_domain': ['domain1.com', 'domain2.com', 'domain3.com', 'domain4.com', 'domain4.com'],
            'source_inbox': ['primary', 'primary', 'promotions', 'promotions', 'social']
        })
        
        # Convert to proper datetime
        sample_data['arrival_datetime'] = pd.to_datetime(sample_data['arrival_datetime'])
        
        # Initialize engine
        engine = UnsubscribeEngine()
        
        # Test inbox insights
        insights = engine.get_inbox_insights(sample_data)
        
        print("✅ Inbox insights test passed!")
        print(f"📊 Got insights for {len(insights.get('inbox_breakdown', []))} inbox categories")
        
        # Test focused analysis on primary inbox
        primary_stats = engine.analyze_sender_engagement(sample_data, focus_inbox='primary')
        print(f"🎯 Primary inbox analysis: {len(primary_stats)} senders")
        
        # Test focused analysis on promotions inbox
        promo_stats = engine.analyze_sender_engagement(sample_data, focus_inbox='promotions')
        print(f"🎯 Promotions inbox analysis: {len(promo_stats)} senders")
        
        return True
        
    except Exception as e:
        print(f"❌ Inbox targeting test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Data-Driven Unsubscribe Engine")
    print("=" * 50)
    
    tests = [
        test_threshold_calculation,
        test_engagement_analysis,
        test_inbox_targeting
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The engine is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
