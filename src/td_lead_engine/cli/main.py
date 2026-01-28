"""Main CLI entry point for socialops command."""

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from typing import Optional
from datetime import datetime

from ..storage.database import LeadDatabase
from ..storage.models import LeadStatus
from ..connectors import CONNECTORS, get_connector
from ..core.scorer import LeadScorer

console = Console()


def get_db(db_path: Optional[str] = None) -> LeadDatabase:
    """Get database instance."""
    path = Path(db_path) if db_path else None
    return LeadDatabase(path)


@click.group()
@click.version_option(version="2.0.0", prog_name="socialops")
def cli():
    """TD Lead Engine - Social media lead scoring for real estate.

    \b
    Quick Start:
      socialops init                                    # Initialize database
      socialops import -s csv -p contacts.csv           # Import contacts
      socialops score                                   # Score all leads
      socialops show --tier hot                         # View hot leads

    \b
    Available Sources:
      instagram, facebook, csv, zillow, google_business,
      google_contacts, google_forms, google_ads, linkedin,
      sales_navigator, nextdoor, website
    """
    pass


# ============================================================================
# CORE COMMANDS
# ============================================================================

@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def migrate(db_path: Optional[str]):
    """Run pending database migrations."""
    from ..storage.migrations import run_migrations

    db = get_db(db_path)
    count = run_migrations(str(db.db_path))
    if count:
        console.print(f"[green]Applied {count} migration(s)[/green]")
    else:
        console.print("[dim]No pending migrations[/dim]")


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def init(db_path: Optional[str]):
    """Initialize the leads database and show setup wizard."""
    db = get_db(db_path)

    # Run migrations automatically on init
    try:
        from ..storage.migrations import run_migrations
        run_migrations(str(db.db_path))
    except Exception as e:
        console.print(f"[yellow]Migration note: {e}[/yellow]")

    console.print(Panel.fit(
        f"[green]✓ Database initialized![/green]\n\n"
        f"Location: [cyan]{db.db_path}[/cyan]\n\n"
        f"[bold]Quick Start:[/bold]\n"
        f"1. [yellow]socialops import -s csv -p ./contacts.csv[/yellow]\n"
        f"2. [yellow]socialops score[/yellow]\n"
        f"3. [yellow]socialops show --tier hot[/yellow]\n\n"
        f"[bold]Configure Integrations:[/bold]\n"
        f"• [yellow]socialops setup slack[/yellow]     - Get hot lead alerts\n"
        f"• [yellow]socialops setup zapier[/yellow]    - Connect 5000+ apps\n"
        f"• [yellow]socialops setup twilio[/yellow]    - SMS notifications\n\n"
        f"[dim]Run 'socialops --help' for all commands[/dim]",
        title="🏠 TD Lead Engine v2.0"
    ))


@cli.command("import")
@click.option("--source", "-s", type=click.Choice(list(CONNECTORS.keys())), required=True,
              help="Source type")
@click.option("--path", "-p", type=click.Path(exists=True), required=True,
              help="Path to export file/folder")
@click.option("--auto-score", is_flag=True, help="Automatically score after import")
@click.option("--notify", is_flag=True, help="Send notifications for hot leads")
@click.option("--db", "db_path", help="Custom database path")
def import_leads(source: str, path: str, auto_score: bool, notify: bool, db_path: Optional[str]):
    """Import leads from various sources.

    \b
    Examples:
      socialops import -s instagram -p ~/Downloads/instagram-export.zip
      socialops import -s zillow -p ./zillow_leads.csv --auto-score
      socialops import -s google_forms -p ./responses.csv --notify
      socialops import -s linkedin -p ./Connections.csv
    """
    db = get_db(db_path)
    file_path = Path(path)
    connector = get_connector(source)

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
        hot_leads = []

        for raw_lead in result.leads:
            lead, is_new = db.insert_lead(raw_lead)
            if is_new:
                new_count += 1
            else:
                merged_count += 1

        # Auto-score if requested
        if auto_score:
            progress.update(task, description="Scoring leads...")
            scorer = LeadScorer()
            db.score_all_leads(scorer)

            # Find hot leads for notification
            hot_leads = db.get_hot_leads(limit=10)

    # Show results
    if result.errors:
        for error in result.errors:
            console.print(f"[red]Error:[/red] {error}")

    if result.warnings:
        for warning in result.warnings[:5]:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

    stats = db.get_stats() if auto_score else None

    output = (
        f"[green]✓ Import complete![/green]\n\n"
        f"New leads: [cyan]{new_count}[/cyan]\n"
        f"Merged: [cyan]{merged_count}[/cyan]\n"
        f"Total: [cyan]{result.count}[/cyan]"
    )

    if auto_score and stats:
        output += (
            f"\n\n[bold]Scoring Results:[/bold]\n"
            f"  🔥 Hot: [red]{stats['by_tier'].get('hot', 0)}[/red]\n"
            f"  🌡️  Warm: [yellow]{stats['by_tier'].get('warm', 0)}[/yellow]"
        )

    if not auto_score:
        output += "\n\n[dim]Run 'socialops score' to score leads[/dim]"

    console.print(Panel.fit(output, title=f"Imported from {source}"))

    # Send notifications if requested
    if notify and hot_leads:
        _send_hot_lead_notifications(hot_leads)


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def score(db_path: Optional[str]):
    """Score all leads in the database."""
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
        f"[green]✓ Scored {count} leads[/green]\n\n"
        f"[bold]Results:[/bold]\n"
        f"  🔥 Hot (150+):     [red]{stats['by_tier'].get('hot', 0)}[/red]\n"
        f"  🌡️  Warm (75-149):  [yellow]{stats['by_tier'].get('warm', 0)}[/yellow]\n"
        f"  💧 Lukewarm (25-74): [blue]{stats['by_tier'].get('lukewarm', 0)}[/blue]\n"
        f"  ❄️  Cold (<25):      [dim]{stats['by_tier'].get('cold', 0)}[/dim]\n"
        f"  ⛔ Negative:        [dim]{stats['by_tier'].get('negative', 0)}[/dim]\n\n"
        f"[dim]Run 'socialops show --tier hot' to view hot leads[/dim]",
        title="Scoring Complete"
    ))


@cli.command()
@click.option("--tier", "-t", type=click.Choice(["hot", "warm", "lukewarm", "cold", "negative"]),
              help="Filter by tier")
@click.option("--source", "-s", help="Filter by source")
@click.option("--status", type=click.Choice([s.value for s in LeadStatus]), help="Filter by status")
@click.option("--limit", "-n", default=20, help="Number of leads to show")
@click.option("--db", "db_path", help="Custom database path")
def show(tier: Optional[str], source: Optional[str], status: Optional[str], limit: int, db_path: Optional[str]):
    """Display leads sorted by score."""
    db = get_db(db_path)

    leads = db.get_all_leads(
        tier=tier,
        status=LeadStatus(status) if status else None,
        limit=limit
    )

    # Filter by source if specified
    if source:
        leads = [l for l in leads if l.source == source]

    if not leads:
        console.print("[yellow]No leads found matching criteria.[/yellow]")
        return

    table = Table(title=f"Leads ({len(leads)})" + (f" - {tier}" if tier else ""))
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Tier", justify="center")
    table.add_column("Name", style="cyan", max_width=25)
    table.add_column("Contact", max_width=25)
    table.add_column("Source")
    table.add_column("Signals", max_width=35)

    tier_colors = {"hot": "red", "warm": "yellow", "lukewarm": "blue", "cold": "dim", "negative": "dim red"}

    for lead in leads:
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
            str(lead.id),
            str(lead.score),
            f"[{tier_style}]{lead.tier}[/{tier_style}]",
            lead.display_name[:25],
            lead.contact_info[:25],
            lead.source,
            signals[:35]
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

    table = Table(title=f"Search: '{query}' ({len(leads)} results)")
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
    """Show detailed information for a lead."""
    db = get_db(db_path)
    lead = db.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

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
        f"[bold]Created:[/bold] {lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else 'N/A'}",
    ]

    if lead.score_breakdown:
        try:
            breakdown = json.loads(lead.score_breakdown)
            matches = breakdown.get("matches", [])
            if matches:
                info_lines.extend(["", "[bold]Matched Signals:[/bold]"])
                for m in matches[:10]:
                    sign = "+" if m["weight"] > 0 else ""
                    info_lines.append(f"  {sign}{m['weight']}: \"{m['phrase']}\"")
        except Exception:
            pass

    if lead.notes:
        info_lines.extend(["", "[bold]Notes:[/bold]", lead.notes[:500]])

    if lead.bio:
        info_lines.extend(["", "[bold]Bio:[/bold]", lead.bio[:300]])

    console.print(Panel("\n".join(filter(None, info_lines)), title=f"Lead #{lead.id}: {lead.display_name}"))


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def stats(db_path: Optional[str]):
    """Show database statistics."""
    db = get_db(db_path)
    data = db.get_stats()

    source_lines = "\n".join(f"  {src}: {cnt}" for src, cnt in sorted(data['by_source'].items(), key=lambda x: -x[1]))

    console.print(Panel.fit(
        f"[bold]Total Leads:[/bold] {data['total_leads']}\n\n"
        f"[bold]By Tier:[/bold]\n"
        f"  🔥 Hot:      [red]{data['by_tier'].get('hot', 0)}[/red]\n"
        f"  🌡️  Warm:     [yellow]{data['by_tier'].get('warm', 0)}[/yellow]\n"
        f"  💧 Lukewarm: [blue]{data['by_tier'].get('lukewarm', 0)}[/blue]\n"
        f"  ❄️  Cold:     [dim]{data['by_tier'].get('cold', 0)}[/dim]\n"
        f"  ⛔ Negative: [dim]{data['by_tier'].get('negative', 0)}[/dim]\n\n"
        f"[bold]By Source:[/bold]\n{source_lines}\n\n"
        f"[bold]Score Stats:[/bold]\n"
        f"  Average: {data['score_avg']}\n"
        f"  Max: {data['score_max']}\n"
        f"  Min: {data['score_min']}",
        title="📊 Database Statistics"
    ))


# ============================================================================
# LEAD MANAGEMENT
# ============================================================================

@cli.command()
@click.argument("lead_id", type=int)
@click.argument("note_text")
@click.option("--db", "db_path", help="Custom database path")
def note(lead_id: int, note_text: str, db_path: Optional[str]):
    """Add a note to a lead."""
    db = get_db(db_path)
    lead = db.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    current_notes = lead.notes or ""
    lead.notes = f"{current_notes}\n[{timestamp}] {note_text}".strip()
    db.update_lead(lead)

    console.print(f"[green]✓ Note added to lead #{lead_id}[/green]")


@cli.command("status")
@click.argument("lead_id", type=int)
@click.argument("new_status", type=click.Choice([s.value for s in LeadStatus]))
@click.option("--db", "db_path", help="Custom database path")
def set_status(lead_id: int, new_status: str, db_path: Optional[str]):
    """Update lead status."""
    db = get_db(db_path)
    lead = db.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    old_status = lead.status.value
    lead.status = LeadStatus(new_status)
    db.update_lead(lead)

    console.print(f"[green]✓ Lead #{lead_id}: {old_status} → {new_status}[/green]")


@cli.command()
@click.argument("lead_id", type=int)
@click.option("--db", "db_path", help="Custom database path")
def convert(lead_id: int, db_path: Optional[str]):
    """Mark a lead as converted (became a client)."""
    db = get_db(db_path)
    lead = db.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    lead.status = LeadStatus.CONVERTED
    db.update_lead(lead)

    # Record conversion for ML
    try:
        from ..core.config import ConversionTracker
        tracker = ConversionTracker()
        signals = []
        if lead.score_breakdown:
            breakdown = json.loads(lead.score_breakdown)
            signals = [m["phrase"] for m in breakdown.get("matches", [])]

        days = (datetime.now() - lead.created_at).days if lead.created_at else 0
        tracker.record_conversion(
            lead_id=lead.id,
            converted=True,
            signals=signals,
            score=lead.score,
            days=days,
            source=lead.source
        )
    except Exception:
        pass

    console.print(f"[green]🎉 Lead #{lead_id} marked as CONVERTED![/green]")
    console.print("[dim]Conversion recorded for scoring optimization[/dim]")


@cli.command()
@click.argument("lead_id", type=int)
@click.argument("tags")
@click.option("--db", "db_path", help="Custom database path")
def tag(lead_id: int, tags: str, db_path: Optional[str]):
    """Add tags to a lead (comma-separated)."""
    db = get_db(db_path)
    lead = db.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    existing_tags = lead.get_tags_list()
    new_tags = [t.strip() for t in tags.split(",") if t.strip()]

    for t in new_tags:
        if t not in existing_tags:
            existing_tags.append(t)

    lead.set_tags_list(existing_tags)
    db.update_lead(lead)

    console.print(f"[green]✓ Tags added: {', '.join(new_tags)}[/green]")


# ============================================================================
# EXPORT & REPORTS
# ============================================================================

@cli.command()
@click.option("--path", "-p", type=click.Path(), default="./leads_export.csv", help="Output file path")
@click.option("--tier", "-t", type=click.Choice(["hot", "warm", "lukewarm", "cold"]), help="Filter by tier")
@click.option("--db", "db_path", help="Custom database path")
def export(path: str, tier: Optional[str], db_path: Optional[str]):
    """Export leads to CSV."""
    db = get_db(db_path)
    output_path = Path(path)
    count = db.export_to_csv(output_path, tier=tier)

    console.print(Panel.fit(
        f"[green]✓ Exported {count} leads[/green]\n\n"
        f"File: [cyan]{output_path.absolute()}[/cyan]",
        title="CSV Export"
    ))


@cli.command()
@click.option("--type", "-t", "report_type", type=click.Choice(["daily", "weekly", "monthly"]), default="daily")
@click.option("--format", "-f", "output_format", type=click.Choice(["text", "html", "json"]), default="text")
@click.option("--output", "-o", type=click.Path(), help="Save report to file")
@click.option("--db", "db_path", help="Custom database path")
def report(report_type: str, output_format: str, output: Optional[str], db_path: Optional[str]):
    """Generate lead report."""
    from ..analytics.reports import ReportGenerator

    db = get_db(db_path)
    generator = ReportGenerator(db)

    if report_type == "daily":
        rep = generator.generate_daily_report()
    elif report_type == "weekly":
        rep = generator.generate_weekly_report()
    else:
        rep = generator.generate_monthly_report()

    if output:
        output_path = Path(output)
        generator.save_report(rep, output_path, output_format)
        console.print(f"[green]✓ Report saved to {output_path}[/green]")
    else:
        console.print(generator.format_report_text(rep))


# ============================================================================
# INTEGRATIONS SETUP
# ============================================================================

@cli.group()
def setup():
    """Configure integrations (Slack, Zapier, Twilio, etc.)."""
    pass


@setup.command("slack")
@click.option("--webhook-url", prompt="Slack Webhook URL", help="Slack incoming webhook URL")
def setup_slack(webhook_url: str):
    """Configure Slack notifications."""
    from ..automation.webhooks import WebhookManager, WebhookEvent

    manager = WebhookManager()
    manager.register(
        webhook_id="slack",
        url=webhook_url,
        events=[WebhookEvent.LEAD_HOT, WebhookEvent.DAILY_DIGEST, WebhookEvent.IMPORT_COMPLETED],
    )

    console.print(Panel.fit(
        "[green]✓ Slack configured![/green]\n\n"
        "You'll receive notifications for:\n"
        "• Hot lead alerts\n"
        "• Daily digests\n"
        "• Import completions\n\n"
        "[dim]Test with: socialops test-notify slack[/dim]",
        title="Slack Integration"
    ))


@setup.command("zapier")
@click.option("--new-lead-url", prompt="Zapier webhook for new leads (or 'skip')", default="skip")
@click.option("--hot-lead-url", prompt="Zapier webhook for hot leads (or 'skip')", default="skip")
def setup_zapier(new_lead_url: str, hot_lead_url: str):
    """Configure Zapier webhooks."""
    from ..automation.webhooks import WebhookManager, WebhookEvent

    manager = WebhookManager()

    if new_lead_url and new_lead_url != "skip":
        manager.register(
            webhook_id="zapier_new_lead",
            url=new_lead_url,
            events=[WebhookEvent.LEAD_CREATED],
        )

    if hot_lead_url and hot_lead_url != "skip":
        manager.register(
            webhook_id="zapier_hot_lead",
            url=hot_lead_url,
            events=[WebhookEvent.LEAD_HOT],
        )

    console.print(Panel.fit(
        "[green]✓ Zapier configured![/green]\n\n"
        "Now in Zapier:\n"
        "1. Click 'Test Trigger' to see sample data\n"
        "2. Add actions (email, SMS, CRM, etc.)\n"
        "3. Turn on your Zaps",
        title="Zapier Integration"
    ))


@setup.command("twilio")
@click.option("--account-sid", prompt="Twilio Account SID")
@click.option("--auth-token", prompt="Twilio Auth Token", hide_input=True)
@click.option("--from-number", prompt="Twilio Phone Number (e.g., +16145551234)")
@click.option("--notify-number", prompt="Your phone number for alerts")
def setup_twilio(account_sid: str, auth_token: str, from_number: str, notify_number: str):
    """Configure Twilio SMS notifications."""
    config_path = Path.home() / ".td-lead-engine" / "twilio_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "account_sid": account_sid,
        "auth_token": auth_token,
        "from_number": from_number,
        "notify_numbers": [notify_number],
    }

    with open(config_path, "w") as f:
        json.dump(config, f)

    console.print(Panel.fit(
        "[green]✓ Twilio configured![/green]\n\n"
        f"From: {from_number}\n"
        f"Alerts to: {notify_number}\n\n"
        "[dim]Test with: socialops test-notify sms[/dim]",
        title="Twilio SMS Integration"
    ))


@setup.command("email")
@click.option("--provider", type=click.Choice(["gmail", "sendgrid"]), prompt="Email provider")
def setup_email(provider: str):
    """Configure email notifications."""
    config_path = Path.home() / ".td-lead-engine" / "email_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if provider == "gmail":
        email = Prompt.ask("Gmail address")
        app_password = Prompt.ask("Gmail App Password", password=True)
        notify_email = Prompt.ask("Email to receive alerts")

        config = {
            "provider": "smtp",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "username": email,
            "password": app_password,
            "from_email": email,
            "notify_emails": [notify_email],
        }
    else:
        api_key = Prompt.ask("SendGrid API Key", password=True)
        from_email = Prompt.ask("From email address")
        notify_email = Prompt.ask("Email to receive alerts")

        config = {
            "provider": "sendgrid",
            "api_key": api_key,
            "from_email": from_email,
            "notify_emails": [notify_email],
        }

    with open(config_path, "w") as f:
        json.dump(config, f)

    console.print(f"[green]✓ Email configured with {provider}![/green]")


@setup.command("hubspot")
@click.option("--api-key", prompt="HubSpot API Key", hide_input=True)
def setup_hubspot(api_key: str):
    """Configure HubSpot CRM sync."""
    config_path = Path.home() / ".td-lead-engine" / "hubspot_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {"api_key": api_key}

    with open(config_path, "w") as f:
        json.dump(config, f)

    # Test connection
    try:
        from ..integrations.hubspot import HubSpotIntegration, HubSpotConfig
        integration = HubSpotIntegration(HubSpotConfig(api_key=api_key))
        if integration.test_connection():
            console.print("[green]✓ HubSpot connected successfully![/green]")
            integration.create_custom_properties()
            console.print("[dim]Custom properties created in HubSpot[/dim]")
        else:
            console.print("[red]Could not connect to HubSpot[/red]")
    except Exception as e:
        console.print(f"[yellow]Saved config. Connection test failed: {e}[/yellow]")


@setup.command("show")
def setup_show():
    """Show current integration status."""
    config_dir = Path.home() / ".td-lead-engine"

    integrations = [
        ("Slack", "webhooks.json", "slack"),
        ("Zapier", "webhooks.json", "zapier"),
        ("Twilio SMS", "twilio_config.json", None),
        ("Email", "email_config.json", None),
        ("HubSpot", "hubspot_config.json", None),
    ]

    table = Table(title="Integration Status")
    table.add_column("Integration")
    table.add_column("Status")

    for name, config_file, webhook_id in integrations:
        config_path = config_dir / config_file
        if config_path.exists():
            if webhook_id:
                try:
                    with open(config_path) as f:
                        data = json.load(f)
                    webhooks = data.get("webhooks", [])
                    if any(w.get("id", "").startswith(webhook_id) for w in webhooks):
                        table.add_row(name, "[green]✓ Configured[/green]")
                    else:
                        table.add_row(name, "[dim]Not configured[/dim]")
                except Exception:
                    table.add_row(name, "[dim]Not configured[/dim]")
            else:
                table.add_row(name, "[green]✓ Configured[/green]")
        else:
            table.add_row(name, "[dim]Not configured[/dim]")

    console.print(table)


# ============================================================================
# AUTOMATION
# ============================================================================

@cli.group()
def schedule():
    """Manage scheduled tasks."""
    pass


@schedule.command("list")
def schedule_list():
    """List scheduled tasks."""
    from ..automation.scheduler import TaskScheduler

    scheduler = TaskScheduler()
    tasks = scheduler.list_tasks()

    if not tasks:
        console.print("[yellow]No scheduled tasks.[/yellow]")
        console.print("[dim]Run 'socialops schedule setup' to create default tasks[/dim]")
        return

    table = Table(title="Scheduled Tasks")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Frequency")
    table.add_column("Next Run")
    table.add_column("Status")

    for task in tasks:
        next_run = task.next_run.strftime("%Y-%m-%d %H:%M") if task.next_run else "N/A"
        status = "[green]Enabled[/green]" if task.enabled else "[dim]Disabled[/dim]"
        table.add_row(task.id, task.name, task.frequency.value, next_run, status)

    console.print(table)


@schedule.command("setup")
def schedule_setup():
    """Set up recommended scheduled tasks."""
    from ..automation.scheduler import TaskScheduler, setup_default_schedule

    scheduler = TaskScheduler()
    setup_default_schedule(scheduler)

    console.print(Panel.fit(
        "[green]✓ Default schedule created![/green]\n\n"
        "Tasks configured:\n"
        "• Daily scoring at 6:00 AM\n"
        "• Daily digest at 8:00 AM\n"
        "• Weekly hot leads export (Monday 7:00 AM)\n"
        "• Daily database backup at 3:00 AM\n\n"
        "[dim]Run 'socialops schedule start' to activate[/dim]",
        title="Scheduler Setup"
    ))


@schedule.command("run")
@click.argument("task_id")
def schedule_run(task_id: str):
    """Run a scheduled task now."""
    from ..automation.scheduler import TaskScheduler

    scheduler = TaskScheduler()
    result = scheduler.run_task_now(task_id)

    if result.success:
        console.print(f"[green]✓ Task '{task_id}' completed[/green]")
        if result.data:
            console.print(f"[dim]{json.dumps(result.data, indent=2)}[/dim]")
    else:
        console.print(f"[red]Task failed: {result.message}[/red]")


# ============================================================================
# NOTIFICATIONS
# ============================================================================

@cli.command("notify")
@click.argument("lead_id", type=int)
@click.option("--channel", "-c", type=click.Choice(["slack", "sms", "email", "all"]), default="slack")
@click.option("--db", "db_path", help="Custom database path")
def notify(lead_id: int, channel: str, db_path: Optional[str]):
    """Send notification about a lead."""
    db = get_db(db_path)
    lead = db.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead #{lead_id} not found[/red]")
        return

    _send_lead_notification(lead, channel)


@cli.command("test-notify")
@click.argument("channel", type=click.Choice(["slack", "sms", "email"]))
def test_notify(channel: str):
    """Send a test notification."""
    from ..automation.webhooks import WebhookManager, WebhookEvent

    test_data = {
        "event": "test",
        "message": "This is a test notification from TD Lead Engine",
        "timestamp": datetime.now().isoformat(),
    }

    if channel == "slack":
        manager = WebhookManager()
        webhooks = [w for w in manager.list_webhooks() if "slack" in w.id]
        if webhooks:
            manager.trigger(WebhookEvent.LEAD_HOT, test_data, async_delivery=False)
            console.print("[green]✓ Test notification sent to Slack[/green]")
        else:
            console.print("[red]Slack not configured. Run 'socialops setup slack'[/red]")

    elif channel == "sms":
        config_path = Path.home() / ".td-lead-engine" / "twilio_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            from ..integrations.twilio_sms import TwilioSMSIntegration, TwilioConfig
            twilio = TwilioSMSIntegration(TwilioConfig(**config))
            for number in config.get("notify_numbers", []):
                twilio._send_sms(number, "Test from TD Lead Engine - SMS working!")
            console.print("[green]✓ Test SMS sent[/green]")
        else:
            console.print("[red]Twilio not configured. Run 'socialops setup twilio'[/red]")

    elif channel == "email":
        console.print("[yellow]Email test not implemented yet[/yellow]")


# ============================================================================
# UTILITY COMMANDS
# ============================================================================

@cli.command("test-score")
@click.argument("text")
def test_score(text: str):
    """Test scoring on text."""
    scorer = LeadScorer()
    result = scorer.score_text(text)

    console.print(Panel(
        scorer.explain_score(result),
        title=f"Score: {result.total_score} ({result.tier.upper()})"
    ))


@cli.command()
def sources():
    """List available import sources."""
    table = Table(title="Available Import Sources")
    table.add_column("Source")
    table.add_column("Description")
    table.add_column("Example")

    sources_info = [
        ("instagram", "Instagram data export", "socialops import -s instagram -p ./export.zip"),
        ("facebook", "Facebook data export", "socialops import -s facebook -p ./export.zip"),
        ("csv", "Generic CSV file", "socialops import -s csv -p ./contacts.csv"),
        ("zillow", "Zillow Premier Agent", "socialops import -s zillow -p ./leads.csv"),
        ("google_business", "Google Business Profile", "socialops import -s google_business -p ./takeout/"),
        ("google_contacts", "Google Contacts export", "socialops import -s google_contacts -p ./contacts.csv"),
        ("google_forms", "Google Forms responses", "socialops import -s google_forms -p ./responses.csv"),
        ("google_ads", "Google Ads lead forms", "socialops import -s google_ads -p ./leads.csv"),
        ("linkedin", "LinkedIn connections", "socialops import -s linkedin -p ./Connections.csv"),
        ("sales_navigator", "Sales Navigator export", "socialops import -s sales_navigator -p ./leads.csv"),
        ("nextdoor", "Nextdoor messages", "socialops import -s nextdoor -p ./messages.json"),
        ("website", "Website lead events", "socialops import -s website -p ./events.jsonl"),
    ]

    for source, desc, example in sources_info:
        table.add_row(source, desc, f"[dim]{example}[/dim]")

    console.print(table)


@cli.command()
@click.option("--db", "db_path", help="Custom database path")
def sync_hubspot(db_path: Optional[str]):
    """Sync leads to HubSpot CRM."""
    config_path = Path.home() / ".td-lead-engine" / "hubspot_config.json"

    if not config_path.exists():
        console.print("[red]HubSpot not configured. Run 'socialops setup hubspot'[/red]")
        return

    with open(config_path) as f:
        config = json.load(f)

    from ..integrations.hubspot import HubSpotIntegration, HubSpotConfig

    db = get_db(db_path)
    integration = HubSpotIntegration(HubSpotConfig(api_key=config["api_key"]))

    # Sync hot and warm leads
    leads = db.get_all_leads(tier="hot", limit=100)
    leads.extend(db.get_all_leads(tier="warm", limit=100))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Syncing to HubSpot...", total=len(leads))

        synced = 0
        for lead in leads:
            try:
                integration.sync_lead_to_hubspot(lead)
                synced += 1
            except Exception as e:
                console.print(f"[yellow]Failed to sync lead #{lead.id}: {e}[/yellow]")
            progress.advance(task)

    console.print(f"[green]✓ Synced {synced} leads to HubSpot[/green]")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _send_hot_lead_notifications(leads):
    """Send notifications for hot leads."""
    from ..automation.webhooks import WebhookManager, WebhookEvent

    manager = WebhookManager()

    for lead in leads:
        lead_data = {
            "lead_id": lead.id,
            "name": lead.display_name,
            "email": lead.email,
            "phone": lead.phone,
            "score": lead.score,
            "tier": lead.tier,
            "source": lead.source,
        }
        manager.trigger(WebhookEvent.LEAD_HOT, lead_data)


def _send_lead_notification(lead, channel: str):
    """Send notification about a specific lead."""
    from ..automation.webhooks import WebhookManager, WebhookEvent

    lead_data = {
        "lead_id": lead.id,
        "name": lead.display_name,
        "email": lead.email,
        "phone": lead.phone,
        "score": lead.score,
        "tier": lead.tier,
        "source": lead.source,
    }

    if channel in ["slack", "all"]:
        manager = WebhookManager()
        manager.trigger(WebhookEvent.LEAD_HOT, lead_data, async_delivery=False)
        console.print("[green]✓ Slack notification sent[/green]")

    if channel in ["sms", "all"]:
        config_path = Path.home() / ".td-lead-engine" / "twilio_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            from ..integrations.twilio_sms import TwilioSMSIntegration, TwilioConfig
            twilio = TwilioSMSIntegration(TwilioConfig(**config))
            twilio.send_hot_lead_alert(lead)
            console.print("[green]✓ SMS notification sent[/green]")


if __name__ == "__main__":
    cli()
