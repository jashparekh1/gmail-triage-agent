from __future__ import annotations
from pathlib import Path

def markdown_report(date_label: str, stats: dict, urgent_rows: list[dict]) -> str:
    lines = []
    lines.append(f"# Gmail Triage — {date_label}\n")
    lines.append(
        f"- **Urgent:** {stats['urgent']}  |  **Non-urgent:** {stats['non_urgent']}  |  "
        f"**Promo:** {stats['promo']}  |  **Total:** {stats['total']}\n"
    )
    lines.append("\n## Urgent\n")
    if not urgent_rows:
        lines.append("_None_\n")
    else:
        for r in urgent_rows:
            lines.append(
                f"- **{r['subject']}** — from {r['from']} — {r['time']}  \n"
                f"  {r['snippet']}\n"
            )
    return "\n".join(lines)

def save_report(text: str, reports_dir: Path, basename: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{basename}.md"
    path.write_text(text)
    return path
