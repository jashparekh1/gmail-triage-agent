"""
Data collection module for Gmail API.
Downloads email history and extracts metadata for ML training.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dateutil import tz
import pandas as pd

from ..core.gmail_api import gmail_service, search_message_ids, get_message_meta, header

class GmailDataCollector:
    """Collects and processes Gmail data for ML training"""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.svc = gmail_service()
        
    def collect_email_history(self, days_back: int = 365, max_emails: int = 10000, 
                            inbox_categories: List[str] = None) -> pd.DataFrame:
        """
        Collect email history for the specified number of days
        
        Args:
            days_back: Number of days to go back
            max_emails: Maximum number of emails to collect
            inbox_categories: List of inbox categories to target. 
                            Options: ['primary', 'social', 'promotions', 'updates', 'forums']
                            If None, defaults to ['primary'] (main inbox)
                            
        Returns:
            DataFrame with email metadata
        """
        # Default to primary inbox if no categories specified
        if inbox_categories is None:
            inbox_categories = ['primary']
        
        print(f"📧 Collecting email history for the last {days_back} days...")
        print(f"🎯 Targeting inboxes: {', '.join(inbox_categories)}")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_date_str = start_date.strftime("%Y/%m/%d")
        
        # Build search query for specific inboxes
        if len(inbox_categories) == 1:
            # Single inbox
            query = f"after:{start_date_str} category:{inbox_categories[0]}"
        else:
            # Multiple inboxes - use OR logic
            category_queries = [f"category:{cat}" for cat in inbox_categories]
            query = f"after:{start_date_str} ({' OR '.join(category_queries)})"
        
        print(f"🔍 Search query: {query}")
        
        # Get message IDs
        messages = self.svc.users().messages().list(
            userId="me", 
            q=query, 
            maxResults=max_emails
        ).execute()
        
        if not messages.get('messages'):
            print("❌ No messages found")
            return pd.DataFrame()
        
        message_ids = [msg['id'] for msg in messages['messages']]
        print(f"📧 Found {len(message_ids)} messages in targeted inboxes")
        
        # Process each email
        email_data = []
        
        for i, msg_id in enumerate(message_ids):
            if i % 100 == 0:
                print(f"📊 Processing message {i+1}/{len(message_ids)}...")
            
            try:
                msg_data = self._extract_message_metadata(msg_id)
                if msg_data:
                    # Add inbox category information
                    msg_data['targeted_inboxes'] = inbox_categories
                    email_data.append(msg_data)
            except Exception as e:
                print(f"⚠️ Error processing message {msg_id}: {e}")
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(email_data)
        
        # Save raw data
        self._save_raw_data(df, start_date_str, inbox_categories)
        
        print(f"✅ Collected {len(df)} emails successfully")
        return df
    
    def collect_from_all_inboxes(self, days_back: int = 365, max_emails: int = 50000) -> pd.DataFrame:
        """
        Collect emails from all inbox categories for comprehensive analysis
        
        Args:
            days_back: Number of days to go back
            max_emails: Maximum number of emails to collect per inbox
            
        Returns:
            DataFrame with email metadata from all inboxes
        """
        print(f"📧 Collecting emails from ALL inbox categories for the last {days_back} days...")
        
        all_categories = ['primary', 'social', 'promotions', 'updates', 'forums']
        all_data = []
        
        for category in all_categories:
            print(f"\n🎯 Collecting from {category} inbox...")
            try:
                category_df = self.collect_email_history(
                    days_back=days_back, 
                    max_emails=max_emails,
                    inbox_categories=[category]
                )
                
                if not category_df.empty:
                    # Add source inbox information
                    category_df['source_inbox'] = category
                    all_data.append(category_df)
                    print(f"✅ Collected {len(category_df)} emails from {category}")
                else:
                    print(f"⚠️ No emails found in {category} inbox")
                    
            except Exception as e:
                print(f"❌ Error collecting from {category}: {e}")
                continue
        
        if not all_data:
            print("❌ No data collected from any inbox")
            return pd.DataFrame()
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save combined data
        self._save_raw_data(combined_df, f"{days_back}_days", ['all_inboxes'])
        
        print(f"\n🎉 Total collection complete: {len(combined_df)} emails from all inboxes")
        return combined_df
    
    def _extract_message_metadata(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from a single message"""
        try:
            # Get full message
            msg = self.svc.users().messages().get(userId="me", id=msg_id).execute()
            
            # Extract basic fields
            metadata = {
                'message_id': msg_id,
                'thread_id': msg.get('threadId', ''),
                'internal_date': msg.get('internalDate', ''),
                'size_estimate': msg.get('sizeEstimate', 0),
                'history_id': msg.get('historyId', ''),
                'snippet': msg.get('snippet', ''),
                'label_ids': msg.get('labelIds', [])
            }
            
            # Extract headers
            if 'payload' in msg and 'headers' in msg['payload']:
                headers = msg['payload']['headers']
                
                # Common headers
                metadata.update({
                    'from': self._extract_header(headers, 'From'),
                    'to': self._extract_header(headers, 'To'),
                    'subject': self._extract_header(headers, 'Subject'),
                    'date': self._extract_header(headers, 'Date'),
                    'message_id_header': self._extract_header(headers, 'Message-ID'),
                    'list_unsubscribe': self._extract_header(headers, 'List-Unsubscribe'),
                    'list_unsubscribe_post': self._extract_header(headers, 'List-Unsubscribe-Post'),
                    'reply_to': self._extract_header(headers, 'Reply-To'),
                    'cc': self._extract_header(headers, 'Cc'),
                    'bcc': self._extract_header(headers, 'Bcc'),
                    'content_type': self._extract_header(headers, 'Content-Type'),
                    'has_attachment': self._has_attachment(msg),
                })
            
            # Extract derived fields
            metadata.update(self._extract_derived_fields(metadata))
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata from {msg_id}: {e}")
            return None
    
    def _extract_header(self, headers: List[Dict[str, str]], name: str) -> str:
        """Extract header value by name"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ''
    
    def _has_attachment(self, msg: Dict[str, Any]) -> bool:
        """Check if message has attachments"""
        if 'payload' not in msg:
            return False
        
        payload = msg['payload']
        
        # Check for multipart content
        if 'parts' in payload:
            return True
        
        # Check content type for attachments
        content_type = payload.get('headers', [])
        for header in content_type:
            if header['name'].lower() == 'content-type':
                if 'attachment' in header['value'].lower():
                    return True
        
        return False
    
    def _extract_derived_fields(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract derived fields from metadata"""
        derived = {}
        
        # Parse internal date
        if metadata.get('internal_date'):
            try:
                timestamp = int(metadata['internal_date']) / 1000
                dt = datetime.fromtimestamp(timestamp)
                derived['arrival_datetime'] = dt
                derived['arrival_date'] = dt.date()
                derived['arrival_hour'] = dt.hour
                derived['arrival_weekday'] = dt.weekday()
                derived['arrival_month'] = dt.month
            except:
                pass
        
        # Extract sender domain
        if metadata.get('from'):
            from_email = metadata['from']
            if '<' in from_email and '>' in from_email:
                # Extract email from "Name <email@domain.com>"
                email = from_email[from_email.find('<')+1:from_email.find('>')]
            else:
                email = from_email
            
            if '@' in email:
                derived['sender_domain'] = email.split('@')[1]
            else:
                derived['sender_domain'] = email
        
        # Extract Gmail categories
        label_ids = metadata.get('label_ids', [])
        derived.update({
            'is_unread': 'UNREAD' in label_ids,
            'is_starred': 'STARRED' in label_ids,
            'is_important': 'IMPORTANT' in label_ids,
            'category_promotions': 'CATEGORY_PROMOTIONS' in label_ids,
            'category_updates': 'CATEGORY_UPDATES' in label_ids,
            'category_social': 'CATEGORY_SOCIAL' in label_ids,
            'category_forums': 'CATEGORY_FORUMS' in label_ids,
            'category_personal': 'CATEGORY_PERSONAL' in label_ids,
            'in_inbox': 'INBOX' in label_ids,
            'in_sent': 'SENT' in label_ids,
            'in_spam': 'SPAM' in label_ids,
            'in_trash': 'TRASH' in label_ids,
        })
        
        # Has unsubscribe link
        derived['has_unsubscribe'] = bool(metadata.get('list_unsubscribe'))
        
        return derived
    
    def _save_raw_data(self, df: pd.DataFrame, date_str: str, source_info: List[str]):
        """Save raw collected data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean up date string to avoid directory issues
        safe_date_str = date_str.replace('/', '_')
        
        # Determine filename based on source
        if 'all_inboxes' in source_info:
            filename = f"gmail_data_all_inboxes_{timestamp}.parquet"
        else:
            filename = f"gmail_data_{safe_date_str}_{timestamp}.parquet"
        
        filepath = self.data_dir / filename
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Save as parquet for efficiency
        df.to_parquet(filepath, index=False)
        print(f"💾 Raw data saved to: {filepath}")
        
        # Also save as CSV for human readability
        csv_filepath = self.data_dir / f"gmail_data_{safe_date_str}_{timestamp}.csv"
        df.to_csv(csv_filepath, index=False)
        print(f"💾 CSV data saved to: {csv_filepath}")
        
        # Save summary stats
        summary = {
            'collection_date': timestamp,
            'date_range': date_str,
            'total_emails': len(df),
            'unique_senders': df['from'].nunique() if 'from' in df.columns else 0,
            'unread_count': df['is_unread'].sum() if 'is_unread' in df.columns else 0,
            'promotions_count': df['category_promotions'].sum() if 'category_promotions' in df.columns else 0,
            'updates_count': df['category_updates'].sum() if 'category_updates' in df.columns else 0,
            'source_inbox': source_info[0] if source_info else 'unknown'
        }
        
        summary_filepath = self.data_dir / f"collection_summary_{timestamp}.json"
        with open(summary_filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"💾 Summary saved to: {summary_filepath}")

def main():
    """Main function for data collection"""
    collector = GmailDataCollector()
    
    # Collect last year's data
    df = collector.collect_email_history(days_back=365, max_emails=50000)
    
    if not df.empty:
        print("\n📊 Data Collection Summary:")
        print(f"Total emails: {len(df)}")
        print(f"Unique senders: {df['from'].nunique()}")
        print(f"Date range: {df['arrival_date'].min()} to {df['arrival_date'].max()}")
        print(f"Unread emails: {df['is_unread'].sum()}")
        print(f"Promotional emails: {df['category_promotions'].sum()}")
        print(f"Emails with unsubscribe links: {df['has_unsubscribe'].sum()}")

if __name__ == "__main__":
    main()
