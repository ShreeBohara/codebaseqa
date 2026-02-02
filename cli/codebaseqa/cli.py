"""
CodebaseQA CLI - AI-powered codebase understanding from the terminal.

Commands:
    index <github_url>     - Index a GitHub repository
    ask <repo_id> <question> - Ask a question about an indexed repo
    list                   - List all indexed repositories
"""

import click
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
import time

console = Console()
API_URL = "http://localhost:8000"


def get_client() -> httpx.Client:
    """Get HTTP client."""
    return httpx.Client(base_url=API_URL, timeout=300.0)


def handle_api_error(e: Exception):
    """Handle API errors gracefully."""
    console.print(f"\n[red]Error:[/] {e}")
    if isinstance(e, httpx.ConnectError):
        console.print("[dim]Is the API server running? Start it with 'uvicorn src.main:app' in apps/api[/]")
    raise click.Abort()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CodebaseQA - AI-powered codebase understanding.
    
    Understand any GitHub repository through natural language Q&A.
    """
    pass


@cli.command()
@click.argument("github_url")
@click.option("--branch", "-b", default=None, help="Branch to index (default: main)")
@click.option("--wait/--no-wait", default=True, help="Wait for indexing to complete")
def index(github_url: str, branch: str, wait: bool):
    """Index a GitHub repository for Q&A.
    
    Example:
        codebaseqa index https://github.com/expressjs/express
    """
    with get_client() as client:
        # Start indexing
        console.print(f"\n[bold blue]📦 Indexing repository:[/] {github_url}\n")
        
        try:
            payload = {"github_url": github_url}
            if branch:
                payload["branch"] = branch
            
            response = client.post("/api/repos/", json=payload)
            
            if response.status_code == 409:
                console.print("[yellow]⚠️  Repository already indexed.[/]\n")
                data = response.json()
                console.print(f"Status: {data.get('detail', 'Already exists')}")
                return
            
            response.raise_for_status()
            repo = response.json()
            
            console.print(f"[green]✓[/] Repository added: [bold]{repo['github_owner']}/{repo['github_name']}[/]")
            console.print(f"  ID: [cyan]{repo['id']}[/]")
            
            if not wait:
                console.print("\n[dim]Indexing started in background. Use 'codebaseqa list' to check status.[/]")
                return
            
            # Poll for completion
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Indexing...", total=None)
                
                while True:
                    time.sleep(2)
                    status_response = client.get(f"/api/repos/{repo['id']}")
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    status = status_data["status"]
                    progress.update(task, description=f"Status: {status}")
                    
                    if status == "completed":
                        progress.update(task, description="[green]✓ Complete![/]")
                        break
                    elif status == "failed":
                        progress.update(task, description="[red]✗ Failed[/]")
                        console.print(f"\n[red]Error:[/] {status_data.get('indexing_error', 'Unknown error')}")
                        return
            
            console.print(f"\n[green]✅ Repository indexed successfully![/]")
            console.print(f"   Files: {status_data['total_files']}")
            console.print(f"   Chunks: {status_data['total_chunks']}")
            console.print(f"\n[dim]Use 'codebaseqa ask {repo['id']} \"your question\"' to start asking questions.[/]")
            
        except Exception as e:
            handle_api_error(e)


@cli.command()
@click.argument("repo_id")
@click.argument("question")
def ask(repo_id: str, question: str):
    """Ask a question about an indexed repository.
    
    Example:
        codebaseqa ask abc123 "What is the main entry point?"
    """
    with get_client() as client:
        console.print(f"\n[bold blue]💬 Asking:[/] {question}\n")
        
        try:
            # Create session
            session_response = client.post("/api/chat/sessions", json={"repo_id": repo_id})
            session_response.raise_for_status()
            session = session_response.json()
            
            # Send message and stream response
            with client.stream(
                "POST",
                f"/api/chat/sessions/{session['id']}/messages",
                json={"content": question},
            ) as response:
                response.raise_for_status()
                
                full_response = ""
                sources = []
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        import json
                        try:
                            data = json.loads(line[6:])
                            
                            if data["type"] == "sources":
                                sources = data.get("sources", [])
                            elif data["type"] == "content":
                                content = data.get("content", "")
                                console.print(content, end="")
                                full_response += content
                            elif data["type"] == "error":
                                console.print(f"\n[red]Error:[/] {data.get('error')}")
                                return
                        except json.JSONDecodeError:
                            pass
                
                console.print("\n")
                
                # Show sources
                if sources:
                    console.print("[dim]─" * 50 + "[/]")
                    console.print("[bold]📚 Sources:[/]")
                    for i, source in enumerate(sources[:5], 1):
                        console.print(f"  {i}. [cyan]{source['file']}[/] L{source['start_line']}-{source['end_line']}")
                    console.print()
                    
        except Exception as e:
            handle_api_error(e)


@cli.command(name="list")
def list_repos():
    """List all indexed repositories."""
    with get_client() as client:
        try:
            response = client.get("/api/repos/")
            response.raise_for_status()
            data = response.json()
            
            if not data["repositories"]:
                console.print("\n[dim]No repositories indexed yet.[/]")
                console.print("[dim]Use 'codebaseqa index <github_url>' to add one.[/]\n")
                return
            
            table = Table(title="Indexed Repositories")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Repository", style="white")
            table.add_column("Status", style="green")
            table.add_column("Files", justify="right")
            table.add_column("Chunks", justify="right")
            
            for repo in data["repositories"]:
                status_style = {
                    "completed": "green",
                    "failed": "red",
                    "pending": "yellow",
                    "cloning": "blue",
                    "parsing": "blue",
                    "embedding": "blue",
                }.get(repo["status"], "white")
                
                table.add_row(
                    repo["id"][:8] + "...",
                    f"{repo['github_owner']}/{repo['github_name']}",
                    f"[{status_style}]{repo['status']}[/]",
                    str(repo["total_files"]),
                    str(repo["total_chunks"]),
                )
            
            console.print()
            console.print(table)
            console.print()
            
        except Exception as e:
            handle_api_error(e)


@cli.command()
@click.argument("repo_id")
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Number of results to show")
def search(repo_id: str, query: str, limit: int):
    """Search code in an indexed repository.
    
    Example:
        codebaseqa search abc123 "authentication middleware"
    """
    with get_client() as client:
        try:
            response = client.post(
                "/api/search/",
                json={"repo_id": repo_id, "query": query, "limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data["results"]:
                console.print("\n[dim]No results found.[/]\n")
                return
            
            console.print(f"\n[bold]Found {data['total']} results[/] ({data['query_time_ms']:.1f}ms)\n")
            
            for i, result in enumerate(data["results"], 1):
                console.print(f"[bold cyan]{i}. {result['file_path']}[/]")
                console.print(f"   [dim]L{result['start_line']}-{result['end_line']} | {result['chunk_type']} | Score: {result['score']:.3f}[/]")
                
                # Show snippet
                snippet = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
                console.print(Panel(snippet, border_style="dim"))
                console.print()
                
        except Exception as e:
            handle_api_error(e)


@cli.command()
@click.argument("repo_id")
def lessons(repo_id: str):
    """List available learning lessons."""
    with get_client() as client:
        try:
            # We need to fetch the syllabus. Since there is no list-syllabus endpoint,
            # we try to fetch the default persona or list personas first?
            # Actually, `generate_curriculum` creates/fetches one. But that triggers generation.
            # We need a way to list EXISTING syllabi or generate one if missing?
            # For CLI, let's assume we want to see the default track.
            
            # First, check if repo exists
            repo_res = client.get(f"/api/repos/{repo_id}")
            repo_res.raise_for_status()
            
            # Fetch default syllabus (implicitly generates if missing, might take time)
            console.print("[dim]Fetching curriculum (this may take a moment)...[/]")
            response = client.post(f"/api/learning/{repo_id}/curriculum", json={"persona": "new_hire"})
            response.raise_for_status()
            syllabus = response.json()
            
            console.print(f"\n[bold]🎓 Curriculum:[/] {syllabus['title']}\n")
            
            for m_idx, module in enumerate(syllabus["modules"], 1):
                console.print(f"[bold blue]{m_idx}. {module['title']}[/]")
                for lesson in module["lessons"]:
                    console.print(f"   • {lesson['title']} [dim](ID: {lesson['id']})[/]")
                console.print()
                
        except Exception as e:
            handle_api_error(e)


@cli.command(name="export-tour")
@click.argument("repo_id")
@click.argument("lesson_id")
@click.option("--output", "-o", default=None, help="Output filename")
def export_tour(repo_id: str, lesson_id: str, output: str):
    """Export a lesson as a VS Code CodeTour file."""
    with get_client() as client:
        try:
            console.print(f"[dim]Exporting lesson {lesson_id}...[/]")
            response = client.get(f"/api/learning/{repo_id}/lessons/{lesson_id}/export/codetour")
            response.raise_for_status()
            tour = response.json()
            
            if not output:
                # Sanitize title for filename
                slug = tour["title"].lower().replace(" ", "_")
                output = f"{slug}.tour"
            
            import json
            with open(output, "w") as f:
                json.dump(tour, f, indent=2)
                
            console.print(f"[green]✓ Exported to:[/] {output}")
            
        except Exception as e:
            handle_api_error(e)


if __name__ == "__main__":
    cli()
