"""Main CLI entry point for socialops command."""

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional

from ..storage.database import LeadDatabase
from ..storage.models import LeadStatus
from ..connectors import InstagramConnector, FacebookConnector, CSVConnector
from ..core.scorer import LeadScorer

console = Console()


def get_db(db_path: Optional[str] = None) -> LeadDatabase:
    """Get database instance."""
    path = Path(db_path) if db_path else None
    return LeadDatabase(path)


@click.group()
@click.version_option(version="1.0.0", prog_name="socialops")
def cli():
    """TD Lead Engine - Social media lead scoring for real estate.

    Score and manage leads from Instagram, Facebook, and CSV imports.
    """
    pass


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def init(db_path: Optional[str]):
    """Initialize the leads database."""
    db = get_db(db_path)
    console.print(Panel.fit(
        f"[green]Database initialized![/green]\n\n"
        f"Location: [cyan]{db.db_path}[/cyan]\n\n"
        f"Next steps:\n"
        f"1. [yellow]socialops import --source instagram --path ./export.zip[/yellow]\n"
        f"2. [yellow]socialops score[/yellow]\n"
        f"3. [yellow]socialops show[/yellow]",
        title="TD Lead Engine"
    ))


@cli.command()
@click.option("--source", "-s", type=click.Choice(["instagram", "facebook", "csv", "manual"]), required=True,
              help="Source type: instagram, facebook, csv, or manual")
@click.option("--path", "-p", type=click.Path(exists=True), required=True,
              help="Path to export file/folder")
@click.option("--db", "db_path", help="Custom database path")
def import_leads(source: str, path: str, db_path: Optional[str]):
    """Import leads from social media exports or CSV files.

    \b
    Examples:
      socialops import --source instagram --path ~/Downloads/instagram-export.zip
      socialops import --source facebook --path ~/Downloads/facebook-export.zip
      socialops import --source csv --path ./contacts.csv
    """
    db = get_db(db_path)
    file_path = Path(path)

    # Select connector
    if source == "instagram":
        connector = InstagramConnector()
    elif source == "facebook":
        connector = FacebookConnector()
    else:
        connector = CSVConnector()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Importing from {source}...", total=None)

        result = connector.import_from_path(file_path)

        progress.update(task, description="Processing leads...")

        new_count = 0
        merged_count = 0

        for raw_lead in result.leads:
            lead, is_new = db.insert_lead(raw_lead)
            if is_new:
                new_count += 1
            else:
                merged_count += 1

    # Show results
    if result.errors:
        for error in result.errors:
            console.print(f"[red]Error:[/red] {error}")

    if result.warnings:
        for warning in result.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

    console.print(Panel.fit(
        f"[green]Import complete![/green]\n\n"
        f"New leads: [cyan]{new_count}[/cyan]\n"
        f"Merged with existing: [cyan]{merged_count}[/cyan]\n"
        f"Total processed: [cyan]{result.count}[/cyan]\n\n"
        f"Run [yellow]socialops score[/yellow] to score imported leads.",
        title=f"Imported from {source}"
    ))


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def score(db_path: Optional[str]):
    """Score all leads in the database.

    Analyzes lead text (bios, messages, notes) for buying/selling intent signals.
    """
    db = get_db(db_path)
    scorer = LeadScorer()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scoring leads...", total=None)
        count = db.score_all_leads(scorer)

    stats = db.get_stats()

    console.print(Panel.fit(
        f"[green]Scoring complete![/green]\n\n"
        f"Leads scored: [cyan]{count}[/cyan]\n\n"
        f"[bold]Results:[/bold]\n"
        f"  Hot (150+):    [red]{stats['by_tier'].get('hot', 0)}[/red]\n"
        f"  Warm (75-149): [yellow]{stats['by_tier'].get('warm', 0)}[/yellow]\n"
        f"  Lukewarm (25-74): [blue]{stats['by_tier'].get('lukewarm', 0)}[/blue]\n"
        f"  Cold (<25):    [dim]{stats['by_tier'].get('cold', 0)}[/dim]\n"
        f"  Negative:      [dim]{stats['by_tier'].get('negative', 0)}[/dim]\n\n"
        f"Run [yellow]socialops show[/yellow] to view top leads.",
        title="Scoring Results"
    ))


@cli.command()
@click.option("--tier", "-t", type=click.Choice(["hot", "warm", "lukewarm", "cold", "negative"]),
              help="Filter by tier")
@click.option("--limit", "-n", default=20, help="Number of leads to show")
@click.option("--db", "db_path", help="Custom database path")
def show(tier: Optional[str], limit: int, db_path: Optional[str]):
    """Display leads sorted by score.

    \b
    Examples:
      socialops show              # Top 20 leads
      socialops show --tier hot   # Hot leads only
      socialops show -n 50        # Top 50 leads
    """
    db = get_db(db_path)

    leads = db.get_all_leads(tier=tier, limit=limit)

    if not leads:
        console.print("[yellow]No leads found.[/yellow]")
        console.print("Run [cyan]socialops import[/cyan] to add leads.")
        return

    table = Table(title=f"Top {len(leads)} Leads" + (f" ({tier})" if tier else ""))
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Tier", justify="center")
    table.add_column("Name", style="cyan")
    table.add_column("Contact")
    table.add_column("Source")
    table.add_column("Signals")

    tier_colors = {
        "hot": "red",
        "warm": "yellow",
        "lukewarm": "blue",
        "cold": "dim",
        "negative": "dim red"
    }

    for lead in leads:
        # Parse score breakdown for signals
        signals = ""
        if lead.score_breakdown:
            try:
                breakdown = json.loads(lead.score_breakdown)
                matches = breakdown.get("matches", [])[:2]
                signals = ", ".join(m["phrase"] for m in matches)
            except Exception:
                pass

        tier_style = tier_colors.get(lead.tier, "")

        table.add_row(
            str(lead.score),
            f"[{tier_style}]{lead.tier}[/{tier_style}]",
            lead.display_name[:25],
            lead.contact_info[:25],
            lead.source,
            signals[:40]
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--db", "db_path", help="Custom database path")
def search(query: str, db_path: Optional[str]):
    """Search leads by name, email, phone, or notes."""
    db = get_db(db_path)

    leads = db.search_leads(query)

    if not leads:
        console.print(f"[yellow]No leads found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("ID", justify="right")
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Contact")
    table.add_column("Source")

    for lead in leads[:20]:
        table.add_row(
            str(lead.id),
            str(lead.score),
            lead.display_name[:30],
            lead.contact_info[:30],
            lead.source
        )

    console.print(table)


@cli.command()
@click.argument("lead_id", type=int)
@click.option("--db", "db_path", help="Custom database path")
def detail(lead_id: int, db_path: Optional[str]):
    """Show detailed information for a specific lead."""
    db = get_db(db_path)

    lead = db.get_lead(lead_id)
    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    # Build detail panel
    info_lines = [
        f"[bold]Name:[/bold] {lead.name or 'N/A'}",
        f"[bold]Email:[/bold] {lead.email or 'N/A'}",
        f"[bold]Phone:[/bold] {lead.phone or 'N/A'}",
        f"[bold]Username:[/bold] @{lead.username}" if lead.username else "",
        f"[bold]Profile:[/bold] {lead.profile_url or 'N/A'}",
        "",
        f"[bold]Score:[/bold] {lead.score} ({lead.tier.upper()})",
        f"[bold]Status:[/bold] {lead.status.value}",
        f"[bold]Source:[/bold] {lead.source}",
    ]

    if lead.score_breakdown:
        try:
            breakdown = json.loads(lead.score_breakdown)
            matches = breakdown.get("matches", [])
            if matches:
                info_lines.append("")
                info_lines.append("[bold]Matched Signals:[/bold]")
                for m in matches[:10]:
                    sign = "+" if m["weight"] > 0 else ""
                    info_lines.append(f"  {sign}{m['weight']}: \"{m['phrase']}\" [{m['category']}]")
        except Exception:
            pass

    if lead.notes:
        info_lines.append("")
        info_lines.append("[bold]Notes:[/bold]")
        info_lines.append(lead.notes[:500])

    if lead.bio:
        info_lines.append("")
        info_lines.append("[bold]Bio:[/bold]")
        info_lines.append(lead.bio[:300])

    console.print(Panel(
        "\n".join(filter(None, info_lines)),
        title=f"Lead #{lead.id}: {lead.display_name}"
    ))


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def stats(db_path: Optional[str]):
    """Show database statistics."""
    db = get_db(db_path)

    data = db.get_stats()

    console.print(Panel.fit(
        f"[bold]Total Leads:[/bold] {data['total_leads']}\n\n"
        f"[bold]By Tier:[/bold]\n"
        f"  Hot:      [red]{data['by_tier'].get('hot', 0)}[/red]\n"
        f"  Warm:     [yellow]{data['by_tier'].get('warm', 0)}[/yellow]\n"
        f"  Lukewarm: [blue]{data['by_tier'].get('lukewarm', 0)}[/blue]\n"
        f"  Cold:     [dim]{data['by_tier'].get('cold', 0)}[/dim]\n"
        f"  Negative: [dim]{data['by_tier'].get('negative', 0)}[/dim]\n\n"
        f"[bold]By Source:[/bold]\n" +
        "\n".join(f"  {src}: {cnt}" for src, cnt in data['by_source'].items()) + "\n\n"
        f"[bold]Score Stats:[/bold]\n"
        f"  Average: {data['score_avg']}\n"
        f"  Max: {data['score_max']}\n"
        f"  Min: {data['score_min']}",
        title="Database Statistics"
    ))


@cli.command()
@click.option("--path", "-p", type=click.Path(), default="./leads_export.csv",
              help="Output CSV file path")
@click.option("--tier", "-t", type=click.Choice(["hot", "warm", "lukewarm", "cold"]),
              help="Export only specific tier")
@click.option("--db", "db_path", help="Custom database path")
def export(path: str, tier: Optional[str], db_path: Optional[str]):
    """Export leads to CSV file.

    \b
    Examples:
      socialops export                        # Export all leads
      socialops export --tier hot -p hot.csv  # Export hot leads only
    """
    db = get_db(db_path)

    output_path = Path(path)
    count = db.export_to_csv(output_path, tier=tier)

    console.print(Panel.fit(
        f"[green]Export complete![/green]\n\n"
        f"Leads exported: [cyan]{count}[/cyan]\n"
        f"File: [cyan]{output_path.absolute()}[/cyan]",
        title="CSV Export"
    ))


@cli.command()
@click.argument("lead_id", type=int)
@click.argument("note")
@click.option("--db", "db_path", help="Custom database path")
def note(lead_id: int, note: str, db_path: Optional[str]):
    """Add a note to a lead."""
    db = get_db(db_path)

    lead = db.get_lead(lead_id)
    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    # Append note
    current_notes = lead.notes or ""
    lead.notes = f"{current_notes}\n[Note] {note}".strip()
    db.update_lead(lead)

    console.print(f"[green]Note added to lead #{lead_id}[/green]")


@cli.command()
@click.argument("lead_id", type=int)
@click.argument("status", type=click.Choice([s.value for s in LeadStatus]))
@click.option("--db", "db_path", help="Custom database path")
def set_status(lead_id: int, status: str, db_path: Optional[str]):
    """Update lead status.

    \b
    Status options: new, contacted, responded, qualified, nurturing, converted, lost, archived
    """
    db = get_db(db_path)

    lead = db.get_lead(lead_id)
    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    lead.status = LeadStatus(status)
    db.update_lead(lead)

    console.print(f"[green]Lead #{lead_id} status updated to: {status}[/green]")


@cli.command()
@click.argument("text")
def test_score(text: str):
    """Test scoring on a piece of text.

    \b
    Example:
      socialops test-score "First time homebuyer looking in Powell, preapproved"
    """
    scorer = LeadScorer()
    result = scorer.score_text(text)

    console.print(Panel(
        scorer.explain_score(result),
        title=f"Score: {result.total_score} ({result.tier.upper()})"
    ))


if __name__ == "__main__":
    cli()
