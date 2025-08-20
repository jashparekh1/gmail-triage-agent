"""
CLI interface for the Smart Unsubscribe Engine
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

from .engine import UnsubscribeEngine
from .data_collector import GmailDataCollector

app = typer.Typer(help="Smart Unsubscribe Engine CLI")
console = Console()

@app.command("analyze")
def analyze_cmd(
    days: int = typer.Option(90, help="Number of days to analyze"),
    max_emails: int = typer.Option(10000, help="Maximum emails to collect"),
    force_collect: bool = typer.Option(False, help="Force new data collection"),
    save_report: bool = typer.Option(True, help="Save detailed report"),
    inbox: str = typer.Option(None, help="Focus on specific inbox: primary, social, promotions, updates, forums"),
    all_inboxes: bool = typer.Option(False, help="Collect from all inbox categories"),
):
    """Analyze email patterns and generate unsubscribe recommendations"""
    load_dotenv()
    
    console.print("[bold]🚀 Smart Unsubscribe Engine[/bold]")
    console.print("=" * 50)
    
    # Determine inbox targeting
    if all_inboxes:
        inbox_categories = None  # Will trigger all inboxes collection
        console.print("🎯 Targeting: ALL inbox categories")
    elif inbox:
        inbox_categories = [inbox]
        console.print(f"🎯 Targeting: {inbox} inbox only")
    else:
        inbox_categories = ['primary']  # Default to primary inbox
        console.print("🎯 Targeting: Primary inbox (default)")
    
    # Check for existing data
    data_files = list(Path("data").glob("gmail_data_*.parquet"))
    
    if not data_files or force_collect:
        console.print("📧 Collecting email data...")
        collector = GmailDataCollector()
        
        if all_inboxes:
            df = collector.collect_from_all_inboxes(days_back=days, max_emails=max_emails)
        else:
            df = collector.collect_email_history(
                days_back=days, 
                max_emails=max_emails,
                inbox_categories=inbox_categories
            )
        
        if df.empty:
            console.print("[red]❌ No data collected. Check your Gmail API setup.[/red]")
            raise typer.Exit(1)
    else:
        # Use most recent data file
        latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
        console.print(f"📊 Using existing data: {latest_file.name}")
        
        try:
            df = pd.read_parquet(latest_file)
        except Exception as e:
            console.print(f"[red]❌ Error reading data file: {e}[/red]")
            raise typer.Exit(1)
    
    # Initialize unsubscribe engine
    engine = UnsubscribeEngine()
    
    # Get inbox insights if we have multi-inbox data
    if 'source_inbox' in df.columns or 'targeted_inboxes' in df.columns:
        console.print("\n📊 Inbox Category Insights:")
        insights = engine.get_inbox_insights(df)
        
        if 'inbox_breakdown' in insights:
            for inbox_info in insights['inbox_breakdown']:
                inbox_name = inbox_info['source_inbox']
                email_count = inbox_info['message_id']
                unread_count = inbox_info['is_unread']
                unread_rate = (unread_count / email_count) * 100 if email_count > 0 else 0
                console.print(f"  • {inbox_name}: {email_count} emails, {unread_rate:.1f}% unread")
    
    # Analyze sender engagement (with optional inbox focus)
    focus_inbox = inbox if inbox else None
    with console.status("[bold green]Analyzing sender engagement..."):
        sender_stats = engine.analyze_sender_engagement(df, focus_inbox=focus_inbox)
    
    if sender_stats.empty:
        console.print("[red]❌ No sender data to analyze[/red]")
        raise typer.Exit(1)
    
    # Generate recommendations
    with console.status("[bold green]Generating recommendations..."):
        recommendations = engine.generate_unsubscribe_recommendations(sender_stats)
    
    # Extract unsubscribe links
    with console.status("[bold green]Extracting unsubscribe links..."):
        unsubscribe_links = engine.extract_unsubscribe_links(df)
    
    # Display summary
    console.print(f"\n[green]✅ Analysis Complete![/green]")
    console.print(f"📊 Total senders analyzed: {len(sender_stats)}")
    console.print(f"🚫 Unsubscribe recommendations: {len(recommendations)}")
    console.print(f"🔗 Senders with unsubscribe links: {len(unsubscribe_links)}")
    
    # Show top recommendations
    if recommendations:
        console.print(f"\n[bold red]🔴 Top Recommendations:[/bold red]")
        
        table = Table(show_header=True, header_style="bold red")
        table.add_column("Priority", style="red", width=10)
        table.add_column("Sender", style="white")
        table.add_column("Score", style="cyan", width=8)
        table.add_column("Confidence", style="blue", width=12)
        table.add_column("Emails", style="blue", width=8)
        table.add_column("Engagement", style="green", width=12)
        table.add_column("Reasons", style="yellow")
        
        for i, rec in enumerate(recommendations[:10]):  # Top 10
            # Determine priority
            if rec['recommendation_score'] >= 0.8:
                priority = "🔴 HIGH"
            elif rec['recommendation_score'] >= 0.6:
                priority = "🟡 MED"
            else:
                priority = "🟢 LOW"
            
            # Truncate reasons
            reasons = ", ".join(rec['reasons'])[:50]
            if len(", ".join(rec['reasons'])) > 50:
                reasons += "..."
            
            table.add_row(
                priority,
                rec['sender'][:30] + "..." if len(rec['sender']) > 30 else rec['sender'],
                f"{rec['recommendation_score']:.2f}",
                rec.get('confidence', 'N/A').upper(),
                str(rec['total_emails']),
                f"{rec['engagement_score']:.2f}",
                reasons
            )
        
        console.print(table)
        
        # Show potential impact
        total_emails = sum(r['total_emails'] for r in recommendations)
        console.print(f"\n[bold]💡 Potential Impact:[/bold]")
        console.print(f"📧 You could reduce your inbox by {total_emails} emails")
        console.print(f"🎯 Focus on high-priority recommendations first")
    
    # Save results if requested
    if save_report:
        with console.status("[bold green]Saving reports..."):
            engine.save_recommendations(recommendations, unsubscribe_links)
        console.print("[green]💾 Reports saved to data/ directory[/green]")

@app.command("collect")
def collect_cmd(
    days: int = typer.Option(365, help="Number of days to collect"),
    max_emails: int = typer.Option(50000, help="Maximum emails to collect"),
):
    """Collect email data for analysis"""
    load_dotenv()
    
    console.print("[bold]📧 Gmail Data Collection[/bold]")
    console.print("=" * 40)
    
    collector = GmailDataCollector()
    
    with console.status("[bold green]Collecting email data..."):
        df = collector.collect_email_history(days_back=days, max_emails=max_emails)
    
    if df.empty:
        console.print("[red]❌ No data collected[/red]")
        raise typer.Exit(1)
    
    console.print(f"[green]✅ Successfully collected {len(df)} emails[/green]")
    console.print(f"📊 Unique senders: {df['from'].nunique()}")
    console.print(f"📅 Date range: {df['arrival_date'].min()} to {df['arrival_date'].max()}")
    console.print(f"📧 Unread emails: {df['is_unread'].sum()}")
    console.print(f"🏷️ Promotional emails: {df['category_promotions'].sum()}")
    console.print(f"🔗 Emails with unsubscribe links: {df['has_unsubscribe'].sum()}")

@app.command("stats")
def stats_cmd():
    """Show statistics about collected data"""
    data_files = list(Path("data").glob("gmail_data_*.parquet"))
    
    if not data_files:
        console.print("[red]❌ No data files found. Run 'collect' first.[/red]")
        raise typer.Exit(1)
    
    # Use most recent data file
    latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
    console.print(f"📊 Data file: {latest_file.name}")
    
    try:
        import pandas as pd
        df = pd.read_parquet(latest_file)
        
        console.print(f"\n[bold]📈 Email Statistics:[/bold]")
        console.print(f"📧 Total emails: {len(df)}")
        console.print(f"👥 Unique senders: {df['from'].nunique()}")
        console.print(f"🌐 Unique domains: {df['sender_domain'].nunique()}")
        console.print(f"📅 Date range: {df['arrival_date'].min()} to {df['arrival_date'].max()}")
        
        console.print(f"\n[bold]📊 Email Categories:[/bold]")
        console.print(f"📧 Unread: {df['is_unread'].sum()} ({df['is_unread'].mean():.1%})")
        console.print(f"⭐ Starred: {df['is_starred'].sum()} ({df['is_starred'].mean():.1%})")
        console.print(f"🔴 Important: {df['is_important'].sum()} ({df['is_important'].mean():.1%})")
        console.print(f"🏷️ Promotions: {df['category_promotions'].sum()} ({df['category_promotions'].mean():.1%})")
        console.print(f"📢 Updates: {df['category_updates'].sum()} ({df['category_updates'].mean():.1%})")
        console.print(f"🔗 Unsubscribe links: {df['has_unsubscribe'].sum()} ({df['has_unsubscribe'].mean():.1%})")
        
        # Top senders
        top_senders = df['from'].value_counts().head(10)
        console.print(f"\n[bold]👥 Top 10 Senders:[/bold]")
        for i, (sender, count) in enumerate(top_senders.items(), 1):
            console.print(f"{i:2d}. {sender[:40]}{'...' if len(sender) > 40 else ''} ({count})")
        
    except Exception as e:
        console.print(f"[red]❌ Error reading data: {e}[/red]")
        raise typer.Exit(1)

@app.command("report")
def report_cmd(
    output: str = typer.Option("console", help="Output format: console, json, markdown"),
):
    """Generate unsubscribe report from existing data"""
    data_files = list(Path("data").glob("unsubscribe_recommendations_*.json"))
    
    if not data_files:
        console.print("[red]❌ No recommendation files found. Run 'analyze' first.[/red]")
        raise typer.Exit(1)
    
    # Use most recent file
    latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
    console.print(f"📊 Using recommendations: {latest_file.name}")
    
    try:
        import json
        with open(latest_file, 'r') as f:
            recommendations = json.load(f)
        
        if output == "console":
            # Display in console
            if not recommendations:
                console.print("No recommendations found.")
                return
            
            console.print(f"\n[bold]🚫 Unsubscribe Recommendations[/bold]")
            console.print(f"Total: {len(recommendations)}")
            
            for i, rec in enumerate(recommendations[:20], 1):  # Show top 20
                priority_color = "red" if rec['recommendation_score'] >= 0.8 else "yellow" if rec['recommendation_score'] >= 0.6 else "green"
                
                console.print(f"\n{i}. [{priority_color}]{rec['sender']}[/{priority_color}]")
                console.print(f"   Score: {rec['recommendation_score']:.2f}")
                console.print(f"   Emails: {rec['total_emails']}")
                console.print(f"   Engagement: {rec['engagement_score']:.2f}")
                console.print(f"   Reasons: {', '.join(rec['reasons'])}")
        
        elif output == "json":
            # Save as JSON
            output_file = Path("unsubscribe_report.json")
            with open(output_file, 'w') as f:
                json.dump(recommendations, f, indent=2)
            console.print(f"[green]💾 Report saved to: {output_file}[/green]")
        
        elif output == "markdown":
            # Generate markdown report
            from .engine import UnsubscribeEngine
            engine = UnsubscribeEngine()
            
            # Get unsubscribe links
            data_files = list(Path("data").glob("gmail_data_*.parquet"))
            if data_files:
                latest_data = max(data_files, key=lambda x: x.stat().st_mtime)
                df = pd.read_parquet(latest_data)
                unsubscribe_links = engine.extract_unsubscribe_links(df)
            else:
                unsubscribe_links = {}
            
            report = engine.generate_unsubscribe_report(recommendations, unsubscribe_links)
            output_file = Path("unsubscribe_report.md")
            with open(output_file, 'w') as f:
                f.write(report)
            console.print(f"[green]💾 Report saved to: {output_file}[/green]")
    
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("thresholds")
def thresholds_cmd():
    """Show the data-driven thresholds calculated from your email data"""
    data_files = list(Path("data").glob("gmail_data_*.parquet"))
    
    if not data_files:
        console.print("[red]❌ No data files found. Run 'collect' first.[/red]")
        raise typer.Exit(1)
    
    # Use most recent data file
    latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
    console.print(f"📊 Data file: {latest_file.name}")
    
    try:
        import pandas as pd
        df = pd.read_parquet(latest_file)
        
        if df.empty:
            console.print("[red]❌ No data available[/red]")
            return
        
        # Initialize engine and calculate thresholds
        from .engine import UnsubscribeEngine
        engine = UnsubscribeEngine()
        
        # Analyze sender engagement to get sender stats
        sender_stats = engine.analyze_sender_engagement(df)
        
        if sender_stats.empty:
            console.print("[red]❌ No sender data to analyze[/red]")
            return
        
        # Calculate thresholds
        thresholds = engine._calculate_data_driven_thresholds(sender_stats)
        
        if not thresholds:
            console.print("[yellow]⚠️ Not enough data to calculate meaningful thresholds[/yellow]")
            return
        
        console.print(f"\n[bold]🔍 Data-Driven Thresholds[/bold]")
        console.print("=" * 40)
        console.print("These thresholds are calculated from YOUR actual email data:")
        console.print("")
        
        # Show engagement thresholds
        if 'low_engagement' in thresholds:
            console.print("[bold]📊 Engagement Thresholds:[/bold]")
            console.print(f"  • Low engagement (25th percentile): {thresholds['low_engagement']:.3f}")
            if 'very_low_engagement' in thresholds:
                console.print(f"  • Very low engagement (10th percentile): {thresholds['very_low_engagement']:.3f}")
            console.print("")
        
        # Show unread rate thresholds
        if 'high_unread_rate' in thresholds:
            console.print("[bold]📧 Unread Rate Thresholds:[/bold]")
            console.print(f"  • High unread rate (75th percentile): {thresholds['high_unread_rate']:.1%}")
            if 'very_high_unread_rate' in thresholds:
                console.print(f"  • Very high unread rate (90th percentile): {thresholds['very_high_unread_rate']:.1%}")
            console.print("")
        
        # Show promotional thresholds
        if 'high_promo' in thresholds:
            console.print("[bold]🏷️ Promotional Content Thresholds:[/bold]")
            console.print(f"  • High promotional (75th percentile): {thresholds['high_promo']:.1%}")
            if 'very_high_promo' in thresholds:
                console.print(f"  • Very high promotional (90th percentile): {thresholds['very_high_promo']:.1%}")
            console.print("")
        
        # Show frequency thresholds
        if 'high_frequency' in thresholds:
            console.print("[bold]⏰ Email Frequency Thresholds:[/bold]")
            console.print(f"  • High frequency (75th percentile): {thresholds['high_frequency']:.3f} emails/day")
            if 'very_high_frequency' in thresholds:
                console.print(f"  • Very high frequency (90th percentile): {thresholds['very_high_frequency']:.3f} emails/day")
            console.print("")
        
        # Show newsletter thresholds
        if 'newsletter_promo_threshold' in thresholds:
            console.print("[bold]📰 Newsletter Identification:[/bold]")
            console.print(f"  • Promotional threshold (median): {thresholds['newsletter_promo_threshold']:.1%}")
            console.print(f"  • Frequency threshold (median): {thresholds['newsletter_frequency_threshold']:.3f} emails/day")
            console.print("")
        
        console.print("[green]✅ All thresholds calculated from your actual email patterns[/green]")
        console.print("[yellow]💡 These automatically adjust as your email behavior changes[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)

@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        typer.echo("Use: python -m src.triage.unsubscribe_cli [COMMAND]")
        typer.echo("\nCommands:")
        typer.echo("  analyze     - Analyze emails and generate recommendations")
        typer.echo("  collect     - Collect email data for analysis")
        typer.echo("  stats       - Show statistics about collected data")
        typer.echo("  report      - Generate unsubscribe report")
        typer.echo("  thresholds  - Show data-driven thresholds used")

if __name__ == "__main__":
    app()
