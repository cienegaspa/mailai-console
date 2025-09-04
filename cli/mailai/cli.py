#!/usr/bin/env python3
"""
MailAI Console CLI

Command-line interface for Gmail evidence analysis runs.
Mirrors all functionality available in the web UI.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional, List

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

# Initialize Rich console
console = Console()

# API client configuration
API_BASE = os.getenv("MAILAI_API_BASE", "http://127.0.0.1:5170")


class MailAIClient:
    """HTTP client for MailAI Console API."""
    
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def create_run(
        self, 
        question: str,
        after: Optional[str] = None,
        before: Optional[str] = None,
        domains: Optional[List[str]] = None,
        max_iters: int = 4,
        use_api_planner: bool = False,
        polish_with_api: bool = False
    ) -> dict:
        """Create a new run."""
        payload = {
            "question": question,
            "max_iters": max_iters,
            "use_api_planner": use_api_planner,
            "polish_with_api": polish_with_api
        }
        
        if after:
            payload["after"] = after
        if before:
            payload["before"] = before  
        if domains:
            payload["domains"] = domains
        
        response = await self.client.post("/runs", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def list_runs(self) -> List[dict]:
        """List all runs."""
        response = await self.client.get("/runs")
        response.raise_for_status()
        return response.json()
    
    async def get_run(self, run_id: str) -> dict:
        """Get run details."""
        response = await self.client.get(f"/runs/{run_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_run_threads(self, run_id: str) -> List[dict]:
        """Get thread summaries for run."""
        response = await self.client.get(f"/runs/{run_id}/threads")
        response.raise_for_status()  
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    MailAI Console CLI
    
    Local Gmail Evidence Console for Attorney Questions
    """
    pass


@cli.command()
@click.argument("question")
@click.option("--after", help="Start date filter (YYYY-MM-DD)")
@click.option("--before", help="End date filter (YYYY-MM-DD)")
@click.option("--domains", help="Comma-separated list of email domains")
@click.option("--max-iters", default=4, help="Maximum iterations (default: 4)")
@click.option("--planner-api", is_flag=True, help="Use API for query planning")
@click.option("--polish-api", is_flag=True, help="Polish summaries with API")
@click.option("--wait", is_flag=True, help="Wait for completion and show results")
def run(question: str, after: str, before: str, domains: str, max_iters: int, 
        planner_api: bool, polish_api: bool, wait: bool):
    """Create and execute a new run."""
    
    async def _run():
        client = MailAIClient()
        
        try:
            console.print(f"[bold blue]Creating run:[/bold blue] {question}")
            
            domain_list = domains.split(",") if domains else None
            if domain_list:
                domain_list = [d.strip() for d in domain_list]
            
            result = await client.create_run(
                question=question,
                after=after,
                before=before,
                domains=domain_list,
                max_iters=max_iters,
                use_api_planner=planner_api,
                polish_with_api=polish_api
            )
            
            run_id = result["run_id"]
            console.print(f"[green]✓ Run created:[/green] {run_id}")
            
            if wait:
                console.print("[yellow]Waiting for completion...[/yellow]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Processing...", total=None)
                    
                    # Poll for completion
                    while True:
                        run_data = await client.get_run(run_id)
                        status = run_data["status"]
                        
                        if status in ["done", "failed", "cancelled"]:
                            break
                        
                        progress.update(task, description=f"Status: {status}")
                        await asyncio.sleep(2)
                
                # Show results
                if run_data["status"] == "done":
                    console.print("[green]✓ Run completed successfully![/green]")
                    
                    threads = await client.get_run_threads(run_id)
                    if threads:
                        console.print(f"\n[bold]Found {len(threads)} relevant threads:[/bold]")
                        
                        for i, thread in enumerate(threads[:3], 1):
                            console.print(f"\n[bold cyan]{i}. Thread {thread['thread_id'][-8:]}[/bold cyan]")
                            console.print(f"Score: {thread['top_score']:.2f}")
                            console.print(f"Participants: {', '.join(thread['participants'])}")
                            
                            if thread.get('bullets'):
                                for bullet in thread['bullets'][:2]:
                                    console.print(f"• {bullet['text']}")
                                    console.print(f"  [dim]Citation: [{bullet['gmail_id']}|{bullet['thread_id']}|{bullet['date']}][/dim]")
                else:
                    console.print(f"[red]✗ Run {run_data['status']}: {run_data.get('stop_reason', 'Unknown error')}[/red]")
            
            else:
                console.print(f"[dim]Use `mailai show {run_id}` to check progress[/dim]")
                
        finally:
            await client.close()
    
    asyncio.run(_run())


@cli.command("list")
def list_runs():
    """List all runs."""
    
    async def _list():
        client = MailAIClient()
        
        try:
            runs = await client.list_runs()
            
            if not runs:
                console.print("[yellow]No runs found. Create one with `mailai run \"your question\"`[/yellow]")
                return
            
            table = Table(title="MailAI Runs")
            table.add_column("Run ID", style="cyan", no_wrap=True)
            table.add_column("Question", style="white", max_width=50)
            table.add_column("Status", style="green")
            table.add_column("Messages", style="blue")
            table.add_column("Created", style="dim")
            
            for run in runs:
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                metrics = run.get("metrics", {})
                
                table.add_row(
                    run["run_id"][-8:],
                    run["question"][:47] + "..." if len(run["question"]) > 50 else run["question"],
                    run["status"].title(),
                    str(metrics.get("total_messages", "-")),
                    created.strftime("%Y-%m-%d %H:%M")
                )
            
            console.print(table)
            
        finally:
            await client.close()
    
    asyncio.run(_list())


@cli.command("show") 
@click.argument("run_id")
def show_run(run_id: str):
    """Show detailed run information."""
    
    async def _show():
        client = MailAIClient()
        
        try:
            run = await client.get_run(run_id)
            
            console.print(f"[bold cyan]Run {run_id}[/bold cyan]")
            console.print(f"[bold]Question:[/bold] {run['question']}")
            console.print(f"[bold]Status:[/bold] {run['status'].title()}")
            
            if run.get("metrics"):
                metrics = run["metrics"]
                console.print(f"[bold]Messages:[/bold] {metrics.get('total_messages', 0)}")
                console.print(f"[bold]Duration:[/bold] {metrics.get('total_duration_ms', 0) / 1000:.1f}s")
                console.print(f"[bold]Iterations:[/bold] {metrics.get('iterations', 0)}")
            
            if run["status"] == "done":
                threads = await client.get_run_threads(run_id)
                
                if threads:
                    console.print(f"\n[bold]Thread Summaries ({len(threads)} found):[/bold]")
                    
                    for thread in threads:
                        console.print(f"\n[cyan]Thread {thread['thread_id'][-8:]}[/cyan] (Score: {thread['top_score']:.2f})")
                        
                        if thread.get('summary_md'):
                            md = Markdown(thread['summary_md'])
                            console.print(md)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"[red]Run {run_id} not found[/red]")
            else:
                console.print(f"[red]Error: {e}[/red]")
        finally:
            await client.close()
    
    asyncio.run(_show())


@cli.command()
@click.argument("run_id") 
@click.argument("question")
@click.option("--mode", default="cached", type=click.Choice(["cached", "auto_expand", "plan"]))
def qa(run_id: str, question: str, mode: str):
    """Ask a follow-up question about a run."""
    console.print(f"[yellow]Q&A functionality not yet implemented[/yellow]")
    console.print(f"Would ask: '{question}' about run {run_id} in {mode} mode")


@cli.command()
@click.argument("run_id")
def export(run_id: str):
    """Export run results (PDF, CSV, JSON)."""
    console.print(f"[yellow]Export functionality not yet implemented[/yellow]")
    console.print(f"Would export run {run_id}")


@cli.command()
@click.argument("run_id")
def cancel(run_id: str):
    """Cancel a running run."""
    console.print(f"[yellow]Cancel functionality not yet implemented[/yellow]")
    console.print(f"Would cancel run {run_id}")


if __name__ == "__main__":
    cli()