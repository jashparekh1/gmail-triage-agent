"""
Smart Unsubscribe Engine
Analyzes sender engagement patterns and recommends unsubscribes.
"""

from __future__ import annotations
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse

class UnsubscribeEngine:
    """Smart engine for identifying senders to unsubscribe from"""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.thresholds = {}  # Will be calculated from data
        
    def _calculate_data_driven_thresholds(self, sender_stats: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate thresholds from actual data distributions
        No magic numbers - everything is data-driven
        """
        if sender_stats.empty:
            return {}
        
        print("📊 Calculating data-driven thresholds...")
        
        thresholds = {}
        
        # Engagement score thresholds
        if 'engagement_score' in sender_stats.columns:
            engagement_scores = sender_stats['engagement_score'].dropna()
            if len(engagement_scores) > 0:
                # Low engagement = bottom 25th percentile
                thresholds['low_engagement'] = engagement_scores.quantile(0.25)
                # Very low engagement = bottom 10th percentile  
                thresholds['very_low_engagement'] = engagement_scores.quantile(0.10)
                print(f"  • Low engagement threshold (25th percentile): {thresholds['low_engagement']:.3f}")
                print(f"  • Very low engagement threshold (10th percentile): {thresholds['very_low_engagement']:.3f}")
        
        # Unread rate thresholds
        if 'read_rate' in sender_stats.columns:
            read_rates = sender_stats['read_rate'].dropna()
            if len(read_rates) > 0:
                # High unread = top 25th percentile (lowest read rates)
                thresholds['high_unread_rate'] = 1 - read_rates.quantile(0.25)
                # Very high unread = top 10th percentile
                thresholds['very_high_unread_rate'] = 1 - read_rates.quantile(0.10)
                print(f"  • High unread rate threshold (75th percentile): {thresholds['high_unread_rate']:.1%}")
                print(f"  • Very high unread rate threshold (90th percentile): {thresholds['very_high_unread_rate']:.1%}")
        
        # Promotional content thresholds
        if 'promo_ratio' in sender_stats.columns:
            promo_ratios = sender_stats['promo_ratio'].dropna()
            if len(promo_ratios) > 0:
                # High promotional = top 25th percentile
                thresholds['high_promo'] = promo_ratios.quantile(0.75)
                # Very high promotional = top 10th percentile
                thresholds['very_high_promo'] = promo_ratios.quantile(0.90)
                print(f"  • High promotional threshold (75th percentile): {thresholds['high_promo']:.1%}")
                print(f"  • Very high promotional threshold (90th percentile): {thresholds['very_high_promo']:.1%}")
        
        # Email frequency thresholds
        if 'emails_per_day' in sender_stats.columns:
            email_freqs = sender_stats['emails_per_day'].dropna()
            if len(email_freqs) > 0:
                # High frequency = top 25th percentile
                thresholds['high_frequency'] = email_freqs.quantile(0.75)
                # Very high frequency = top 10th percentile
                thresholds['very_high_frequency'] = email_freqs.quantile(0.90)
                print(f"  • High frequency threshold (75th percentile): {thresholds['high_frequency']:.3f} emails/day")
                print(f"  • Very high frequency threshold (90th percentile): {thresholds['very_high_frequency']:.3f} emails/day")
        
        # Newsletter identification threshold
        if 'promo_ratio' in sender_stats.columns and 'emails_per_day' in sender_stats.columns:
            # A sender is likely a newsletter if they're above median in both promotional content and frequency
            thresholds['newsletter_promo_threshold'] = promo_ratios.quantile(0.5)
            thresholds['newsletter_frequency_threshold'] = email_freqs.quantile(0.5)
            print(f"  • Newsletter promo threshold (median): {thresholds['newsletter_promo_threshold']:.1%}")
            print(f"  • Newsletter frequency threshold (median): {thresholds['newsletter_frequency_threshold']:.3f} emails/day")
        
        self.thresholds = thresholds
        return thresholds
    
    def analyze_sender_engagement(self, df: pd.DataFrame, 
                                focus_inbox: str = None) -> pd.DataFrame:
        """
        Analyze engagement patterns for each sender
        
        Args:
            df: DataFrame with email data from data_collector
            focus_inbox: Optional specific inbox to focus on ('primary', 'social', 'promotions', etc.)
            
        Returns:
            DataFrame with sender engagement analysis
        """
        if df.empty:
            return pd.DataFrame()
        
        print("🔍 Analyzing sender engagement patterns...")
        
        if focus_inbox:
            print(f"🎯 Focusing analysis on {focus_inbox} inbox")
            # Filter data for specific inbox if source_inbox column exists
            if 'source_inbox' in df.columns:
                df = df[df['source_inbox'] == focus_inbox]
                print(f"📊 Filtered to {len(df)} emails from {focus_inbox} inbox")
            elif 'targeted_inboxes' in df.columns:
                # Handle case where we targeted specific inboxes
                df = df[df['targeted_inboxes'].apply(lambda x: focus_inbox in x if isinstance(x, list) else x == focus_inbox)]
                print(f"📊 Filtered to {len(df)} emails from {focus_inbox} inbox")
        
        # Group by sender and calculate metrics
        sender_stats = df.groupby('from').agg({
            'message_id': 'count',  # Total emails
            'is_unread': 'sum',     # Unread count
            'is_starred': 'sum',    # Starred count
            'is_important': 'sum',  # Important count
            'category_promotions': 'sum',  # Promotional emails
            'category_updates': 'sum',     # Update emails
            'category_social': 'sum',      # Social emails
            'category_forums': 'sum',      # Forum emails
            'category_personal': 'sum',    # Personal emails
            'has_unsubscribe': 'sum',      # Emails with unsubscribe links
            'arrival_datetime': ['min', 'max'],  # First and last email
            'list_unsubscribe': 'first',   # Unsubscribe link
            'sender_domain': 'first',      # Sender domain
        }).reset_index()
        
        # Flatten column names
        sender_stats.columns = [
            'sender', 'total_emails', 'unread_count', 'starred_count', 'important_count',
            'promotions_count', 'updates_count', 'social_count', 'forums_count', 'personal_count',
            'unsubscribe_links_count', 'first_email_date', 'last_email_date', 'unsubscribe_link', 'domain'
        ]
        
        # Calculate engagement metrics
        sender_stats['read_rate'] = (sender_stats['total_emails'] - sender_stats['unread_count']) / sender_stats['total_emails']
        sender_stats['engagement_score'] = (
            sender_stats['starred_count'] * 0.4 + 
            sender_stats['important_count'] * 0.3 + 
            sender_stats['read_rate'] * 0.3
        )
        
        # Calculate email frequency
        sender_stats['first_email_date'] = pd.to_datetime(sender_stats['first_email_date'])
        sender_stats['last_email_date'] = pd.to_datetime(sender_stats['last_email_date'])
        sender_stats['days_active'] = (sender_stats['last_email_date'] - sender_stats['first_email_date']).dt.days
        sender_stats['emails_per_day'] = sender_stats['total_emails'] / sender_stats['days_active'].clip(lower=1)
        
        # Calculate category distribution
        sender_stats['promo_ratio'] = sender_stats['promotions_count'] / sender_stats['total_emails']
        sender_stats['update_ratio'] = sender_stats['updates_count'] / sender_stats['total_emails']
        sender_stats['social_ratio'] = sender_stats['social_count'] / sender_stats['total_emails']
        
        # Identify newsletter characteristics using data-driven thresholds
        if 'promo_ratio' in sender_stats.columns and 'emails_per_day' in sender_stats.columns:
            # Use median thresholds to identify likely newsletters
            promo_median = sender_stats['promo_ratio'].median()
            freq_median = sender_stats['emails_per_day'].median()
            
            sender_stats['is_likely_newsletter'] = (
                (sender_stats['promo_ratio'] > promo_median) | 
                (sender_stats['unsubscribe_links_count'] > 0) |
                (sender_stats['emails_per_day'] > freq_median)
            )
        else:
            # Fallback if we don't have the data
            sender_stats['is_likely_newsletter'] = False
        
        return sender_stats
    
    def get_inbox_insights(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get insights about different inbox categories
        
        Args:
            df: DataFrame with email data
            
        Returns:
            Dictionary with inbox insights
        """
        if df.empty:
            return {}
        
        insights = {}
        
        # Check if we have source inbox information
        if 'source_inbox' in df.columns:
            print("📊 Analyzing inbox category insights...")
            
            # Group by inbox category
            inbox_stats = df.groupby('source_inbox').agg({
                'message_id': 'count',
                'is_unread': 'sum',
                'category_promotions': 'sum',
                'category_updates': 'sum',
                'category_social': 'sum',
                'category_forums': 'sum',
                'category_personal': 'sum',
                'has_unsubscribe': 'sum'
            }).reset_index()
            
            insights['inbox_breakdown'] = inbox_stats.to_dict('records')
            
            # Calculate percentages
            total_emails = len(df)
            for _, inbox in inbox_stats.iterrows():
                inbox_name = inbox['source_inbox']
                inbox_count = inbox['message_id']
                insights[f'{inbox_name}_percentage'] = (inbox_count / total_emails) * 100
                insights[f'{inbox_name}_unread_rate'] = (inbox['is_unread'] / inbox_count) * 100 if inbox_count > 0 else 0
            
            print(f"✅ Analyzed {len(inbox_stats)} inbox categories")
            
        elif 'targeted_inboxes' in df.columns:
            # Handle case where we targeted specific inboxes
            print("📊 Analyzing targeted inbox insights...")
            targeted = df['targeted_inboxes'].iloc[0] if not df.empty else []
            insights['targeted_inboxes'] = targeted
            insights['total_emails'] = len(df)
            
        return insights
    
    def generate_unsubscribe_recommendations(self, sender_stats: pd.DataFrame, 
                                          min_emails: int = 5) -> List[Dict[str, Any]]:
        """
        Generate unsubscribe recommendations using data-driven thresholds
        No magic numbers - everything is calculated from your actual data
        
        Args:
            sender_stats: DataFrame with sender engagement analysis
            min_emails: Minimum emails needed to make recommendation
            
        Returns:
            List of unsubscribe recommendations
        """
        if sender_stats.empty:
            return []
        
        print("🚫 Generating data-driven unsubscribe recommendations...")
        
        # First, calculate thresholds from the data
        thresholds = self._calculate_data_driven_thresholds(sender_stats)
        
        if not thresholds:
            print("⚠️ Not enough data to calculate meaningful thresholds")
            return []
        
        recommendations = []
        
        for _, sender in sender_stats.iterrows():
            if sender['total_emails'] < min_emails:
                continue
            
            # Calculate recommendation score using data-driven thresholds
            recommendation_score = 0
            reasons = []
            confidence = "low"
            
            # Check engagement patterns
            if 'low_engagement' in thresholds:
                if sender['engagement_score'] <= thresholds['low_engagement']:
                    if sender['engagement_score'] <= thresholds.get('very_low_engagement', 0):
                        recommendation_score += 0.4
                        reasons.append(f"Very low engagement (bottom 10%: {sender['engagement_score']:.3f})")
                        confidence = "high"
                    else:
                        recommendation_score += 0.3
                        reasons.append(f"Low engagement (bottom 25%: {sender['engagement_score']:.3f})")
                        confidence = "medium"
            
            # Check unread patterns
            if 'high_unread_rate' in thresholds:
                unread_rate = 1 - sender['read_rate']
                if unread_rate >= thresholds['high_unread_rate']:
                    if unread_rate >= thresholds.get('very_high_unread_rate', 1):
                        recommendation_score += 0.3
                        reasons.append(f"Very high unread rate (top 10%: {unread_rate:.1%})")
                        confidence = "high"
                    else:
                        recommendation_score += 0.2
                        reasons.append(f"High unread rate (top 25%: {unread_rate:.1%})")
                        confidence = "medium"
            
            # Check promotional content
            if 'high_promo' in thresholds:
                if sender['promo_ratio'] >= thresholds['high_promo']:
                    if sender['promo_ratio'] >= thresholds.get('very_high_promo', 1):
                        recommendation_score += 0.3
                        reasons.append(f"Very high promotional content (top 10%: {sender['promo_ratio']:.1%})")
                        confidence = "high"
                    else:
                        recommendation_score += 0.2
                        reasons.append(f"High promotional content (top 25%: {sender['promo_ratio']:.1%})")
                        confidence = "medium"
            
            # Check email frequency
            if 'high_frequency' in thresholds:
                if sender['emails_per_day'] >= thresholds['high_frequency']:
                    if sender['emails_per_day'] >= thresholds.get('very_high_frequency', float('inf')):
                        recommendation_score += 0.2
                        reasons.append(f"Very high frequency (top 10%: {sender['emails_per_day']:.3f} emails/day)")
                        confidence = "high"
                    else:
                        recommendation_score += 0.1
                        reasons.append(f"High frequency (top 25%: {sender['emails_per_day']:.3f} emails/day)")
                        confidence = "medium"
            
            # Bonus for having unsubscribe link (easier to unsubscribe)
            if sender['unsubscribe_links_count'] > 0:
                recommendation_score += 0.1
                reasons.append("Has unsubscribe link")
            
            # Only recommend if score is high enough and we have confidence
            if recommendation_score >= 0.3:  # Lower threshold since we're more precise now
                recommendation = {
                    'sender': sender['sender'],
                    'domain': sender['domain'],
                    'recommendation_score': recommendation_score,
                    'confidence': confidence,
                    'reasons': reasons,
                    'total_emails': sender['total_emails'],
                    'engagement_score': sender['engagement_score'],
                    'read_rate': sender['read_rate'],
                    'promo_ratio': sender['promo_ratio'],
                    'emails_per_day': sender['emails_per_day'],
                    'unsubscribe_link': sender['unsubscribe_link'],
                    'days_active': sender['days_active'],
                    'is_likely_newsletter': sender['is_likely_newsletter'],
                    'thresholds_used': {
                        'low_engagement': thresholds.get('low_engagement'),
                        'high_unread_rate': thresholds.get('high_unread_rate'),
                        'high_promo': thresholds.get('high_promo'),
                        'high_frequency': thresholds.get('high_frequency')
                    }
                }
                
                recommendations.append(recommendation)
        
        # Sort by recommendation score (highest first)
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        print(f"✅ Generated {len(recommendations)} data-driven recommendations")
        return recommendations
    
    def extract_unsubscribe_links(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Extract and categorize unsubscribe links
        
        Args:
            df: DataFrame with email data
            
        Returns:
            Dictionary mapping senders to unsubscribe links
        """
        print("🔗 Extracting unsubscribe links...")
        
        unsubscribe_data = {}
        
        # Filter emails with unsubscribe links
        emails_with_unsubscribe = df[df['list_unsubscribe'].notna() & (df['list_unsubscribe'] != '')]
        
        for _, email in emails_with_unsubscribe.iterrows():
            sender = email['from']
            unsubscribe_text = email['list_unsubscribe']
            
            if sender not in unsubscribe_data:
                unsubscribe_data[sender] = []
            
            # Parse unsubscribe links
            links = self._parse_unsubscribe_links(unsubscribe_text)
            unsubscribe_data[sender].extend(links)
        
        # Remove duplicates
        for sender in unsubscribe_data:
            unsubscribe_data[sender] = list(set(unsubscribe_data[sender]))
        
        print(f"✅ Found unsubscribe links for {len(unsubscribe_data)} senders")
        return unsubscribe_data
    
    def _parse_unsubscribe_links(self, unsubscribe_text: str) -> List[str]:
        """Parse unsubscribe text to extract links"""
        links = []
        
        # Split by comma (multiple unsubscribe methods)
        parts = unsubscribe_text.split(',')
        
        for part in parts:
            part = part.strip()
            
            # Extract URLs
            url_match = re.search(r'https?://[^\s>]+', part)
            if url_match:
                links.append(url_match.group())
            
            # Extract mailto links
            mailto_match = re.search(r'mailto:[^\s>]+', part)
            if mailto_match:
                links.append(mailto_match.group())
        
        return links
    
    def generate_unsubscribe_report(self, recommendations: List[Dict[str, Any]], 
                                  unsubscribe_links: Dict[str, List[str]]) -> str:
        """
        Generate a human-readable unsubscribe report
        
        Args:
            recommendations: List of unsubscribe recommendations
            unsubscribe_links: Dictionary of unsubscribe links
            
        Returns:
            Formatted report string
        """
        if not recommendations:
            return "No unsubscribe recommendations found."
        
        report = []
        report.append("# 🚫 Unsubscribe Recommendations Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total recommendations: {len(recommendations)}")
        report.append("")
        
        # Group by recommendation score
        high_priority = [r for r in recommendations if r['recommendation_score'] >= 0.8]
        medium_priority = [r for r in recommendations if 0.6 <= r['recommendation_score'] < 0.8]
        low_priority = [r for r in recommendations if r['recommendation_score'] < 0.6]
        
        if high_priority:
            report.append("## 🔴 High Priority (Strongly Recommended)")
            report.extend(self._format_recommendations(high_priority, unsubscribe_links))
            report.append("")
        
        if medium_priority:
            report.append("## 🟡 Medium Priority (Consider Unsubscribing)")
            report.extend(self._format_recommendations(medium_priority, unsubscribe_links))
            report.append("")
        
        if low_priority:
            report.append("## 🟢 Low Priority (Optional)")
            report.extend(self._format_recommendations(low_priority, unsubscribe_links))
            report.append("")
        
        # Summary statistics
        report.append("## 📊 Summary Statistics")
        report.append(f"- High priority: {len(high_priority)}")
        report.append(f"- Medium priority: {len(medium_priority)}")
        report.append(f"- Low priority: {len(low_priority)}")
        
        total_emails = sum(r['total_emails'] for r in recommendations)
        report.append(f"- Total emails from recommended senders: {total_emails}")
        report.append(f"- Potential inbox reduction: {total_emails} emails")
        
        # Show data-driven thresholds used
        if recommendations and 'thresholds_used' in recommendations[0]:
            report.append("\n## 🔍 Data-Driven Thresholds Used")
            thresholds = recommendations[0]['thresholds_used']
            if thresholds.get('low_engagement') is not None:
                report.append(f"- **Low engagement threshold**: {thresholds['low_engagement']:.3f} (25th percentile)")
            if thresholds.get('high_unread_rate') is not None:
                report.append(f"- **High unread rate threshold**: {thresholds['high_unread_rate']:.1%} (75th percentile)")
            if thresholds.get('high_promo') is not None:
                report.append(f"- **High promotional threshold**: {thresholds['high_promo']:.1%} (75th percentile)")
            if thresholds.get('high_frequency') is not None:
                report.append(f"- **High frequency threshold**: {thresholds['high_frequency']:.3f} emails/day (75th percentile)")
            report.append("\n*These thresholds are calculated from your actual email data, not arbitrary values.*")
        
        return "\n".join(report)
    
    def _format_recommendations(self, recommendations: List[Dict[str, Any]], 
                               unsubscribe_links: Dict[str, List[str]]) -> List[str]:
        """Format recommendations for display"""
        formatted = []
        
        for rec in recommendations:
            sender = rec['sender']
            domain = rec['domain']
            
            formatted.append(f"### {sender}")
            formatted.append(f"- **Domain**: {domain}")
            formatted.append(f"- **Score**: {rec['recommendation_score']:.2f}")
            formatted.append(f"- **Total emails**: {rec['total_emails']}")
            formatted.append(f"- **Engagement**: {rec['engagement_score']:.2f}")
            formatted.append(f"- **Read rate**: {rec['read_rate']:.1%}")
            formatted.append(f"- **Promo ratio**: {rec['promo_ratio']:.1%}")
            formatted.append(f"- **Frequency**: {rec['emails_per_day']:.2f} emails/day")
            formatted.append(f"- **Active for**: {rec['days_active']} days")
            
            # Add reasons
            if rec['reasons']:
                formatted.append(f"- **Reasons**: {', '.join(rec['reasons'])}")
            
            # Add unsubscribe links
            if sender in unsubscribe_links:
                links = unsubscribe_links[sender]
                formatted.append(f"- **Unsubscribe links**: {len(links)} found")
                for i, link in enumerate(links[:3]):  # Show first 3 links
                    formatted.append(f"  {i+1}. {link}")
                if len(links) > 3:
                    formatted.append(f"  ... and {len(links) - 3} more")
            
            formatted.append("")
        
        return formatted
    
    def save_recommendations(self, recommendations: List[Dict[str, Any]], 
                           unsubscribe_links: Dict[str, List[str]]):
        """Save recommendations to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save recommendations as JSON
        rec_file = self.data_dir / f"unsubscribe_recommendations_{timestamp}.json"
        with open(rec_file, 'w') as f:
            json.dump(recommendations, f, indent=2, default=str)
        
        # Save unsubscribe links
        links_file = self.data_dir / f"unsubscribe_links_{timestamp}.json"
        with open(links_file, 'w') as f:
            json.dump(unsubscribe_links, f, indent=2)
        
        # Generate and save report
        report = self.generate_unsubscribe_report(recommendations, unsubscribe_links)
        report_file = self.data_dir / f"unsubscribe_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"💾 Saved recommendations to: {rec_file}")
        print(f"💾 Saved unsubscribe links to: {links_file}")
        print(f"💾 Saved report to: {report_file}")

def main():
    """Main function for unsubscribe analysis"""
    from .data_collector import GmailDataCollector
    
    print("🚀 Smart Unsubscribe Engine")
    print("=" * 40)
    
    # Collect data if no recent data exists
    data_files = list(Path("data").glob("gmail_data_*.parquet"))
    
    if not data_files:
        print("📧 No existing data found. Collecting email history...")
        collector = GmailDataCollector()
        df = collector.collect_email_history(days_back=90, max_emails=10000)
    else:
        # Use most recent data file
        latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
        print(f"📊 Using existing data: {latest_file}")
        df = pd.read_parquet(latest_file)
    
    if df.empty:
        print("❌ No data available for analysis")
        return
    
    # Initialize unsubscribe engine
    engine = UnsubscribeEngine()
    
    # Analyze sender engagement
    sender_stats = engine.analyze_sender_engagement(df)
    
    # Generate recommendations
    recommendations = engine.generate_unsubscribe_recommendations(sender_stats)
    
    # Extract unsubscribe links
    unsubscribe_links = engine.extract_unsubscribe_links(df)
    
    # Save results
    engine.save_recommendations(recommendations, unsubscribe_links)
    
    # Display summary
    print("\n📊 Analysis Complete!")
    print(f"Total senders analyzed: {len(sender_stats)}")
    print(f"Unsubscribe recommendations: {len(recommendations)}")
    print(f"Senders with unsubscribe links: {len(unsubscribe_links)}")
    
    if recommendations:
        print("\n🔴 Top 3 recommendations:")
        for i, rec in enumerate(recommendations[:3]):
            print(f"{i+1}. {rec['sender']} (Score: {rec['recommendation_score']:.2f})")
            print(f"   Reason: {', '.join(rec['reasons'])}")

if __name__ == "__main__":
    main()
