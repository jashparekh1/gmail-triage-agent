import typer
from rich.console import Console
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from dateutil import tz

from .gmail_api import today_iso_for_gmail_query, search_message_ids, get_message_meta, header
from .classify_llm import classify_with_gemini
from .render import markdown_report, save_report

app = typer.Typer(help="Gmail Triage CLI")
console = Console()

def _local_date_str():
    return datetime.now(tz.gettz()).date().isoformat()

@app.command("triage")
def triage_cmd(
    since: str = typer.Option(None, help="YYYY/MM/DD (local). Defaults to today."),
    limit: int = typer.Option(50, help="Max unread to fetch"),
    save: bool = typer.Option(False, help="Write Markdown report to ./reports"),
    show: str = typer.Option("urgent", help="Which items to list: urgent | non-urgent | promo | all"),
    justification: bool = typer.Option(False, "--justification", help="Show the LLM's reason next to each item"),
):
    """Fetch unread mail since a date, classify with Gemini, print stats + list items."""
    load_dotenv()
    since_str = since or today_iso_for_gmail_query()
    q = f'is:unread after:{since_str}'
    console.print(f"[bold]Query[/bold]: {q}")

    ids = search_message_ids(q=q, max_results=limit)
    if not ids:
        console.print("[green]No unread messages found. 🎉[/green]")
        raise typer.Exit()

    rows, stats = [], {"urgent":0, "non_urgent":0, "promo":0, "total":0}
    for mid in ids:
        m = get_message_meta(mid)
        frm = header(m, "From")
        sub = header(m, "Subject", "(no subject)")
        date = header(m, "Date")
        snippet = m.get("snippet","")

        try:
            llm = classify_with_gemini(sub, frm, snippet)
            label, reason = llm["label"], llm["reason"]
        except Exception as e:
            label, reason = "non-urgent", f"llm_error:{e}"

        stats["total"] += 1
        if label == "urgent": stats["urgent"] += 1
        elif label == "promo": stats["promo"] += 1
        else: stats["non_urgent"] += 1

        rows.append({
            "label": label, "reason": reason, "from": frm, "subject": sub,
            "snippet": snippet[:200].replace("\n"," "), "time": date
        })

    console.print(
        f"Urgent: {stats['urgent']} • Non-urgent: {stats['non_urgent']} • Promo: {stats['promo']} • Total: {stats['total']}\n"
    )

    # decide what to show
    label_filter = {"urgent","non-urgent","promo"} if show=="all" else {show}
    title = "ALL" if show=="all" else show.upper()
    console.print(f"[bold]{title}[/bold]")

    shown = [r for r in rows if r["label"] in label_filter]
    if not shown:
        console.print("None 🎉")
    else:
        for r in shown:
            base = f"- {r['subject']} — from {r['from']} — {r['time']}\n  {r['snippet']}"
            if justification and r["reason"]:
                base += f"  [i]({r['reason']})[/i]"
            console.print(base)

    if save:
        urg = [r for r in rows if r["label"] == "urgent"]
        md = markdown_report(_local_date_str(), stats, urg)
        out = save_report(md, Path("reports"), f"{_local_date_str()}_triage")
        console.print(f"\nSaved: {out}")

@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        typer.echo("Use: python -m src.triage.cli triage [--since YYYY/MM/DD] [--save]")

if __name__ == "__main__":
    app()
