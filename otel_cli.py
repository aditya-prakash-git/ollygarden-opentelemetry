#!/usr/bin/env python3
"""
OpenTelemetry Instrumentation Validator CLI - Standalone Version
Fixed import issues for easy running
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import track
from dotenv import load_dotenv

# Fix imports by adding paths
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

try:
    from src.rag.pipeline import RAGPipeline
except ImportError:
    print("Import error. Make sure you're running from the project root directory.")
    print(f"Current directory: {os.getcwd()}")
    print(f"Expected src directory: {src_dir}")
    print(f"Src directory exists: {src_dir.exists()}")
    sys.exit(1)

# Initialize rich console for pretty output
console = Console()

@click.group()
@click.option('--kb-path', default='./knowledge_base', help='Path to knowledge base directory')
@click.option('--vector-store', default='./vector_store', help='Path to vector store directory') 
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, kb_path, vector_store, verbose):
    """
    OpenTelemetry Instrumentation Validator
    
    AI-powered tool to validate OpenTelemetry instrumentation against best practices.
    Uses RAG (Retrieval-Augmented Generation) with your knowledge base.
    """
    # Load environment variables
    load_dotenv()
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store configuration
    ctx.obj['kb_path'] = kb_path
    ctx.obj['vector_store'] = vector_store
    ctx.obj['verbose'] = verbose
    
    # Initialize pipeline
    try:
        ctx.obj['pipeline'] = RAGPipeline(kb_path, vector_store)
        
        if verbose:
            console.print(f"[dim]Knowledge base: {kb_path}[/dim]")
            console.print(f"[dim]Vector store: {vector_store}[/dim]")
            
    except Exception as e:
        console.print(f"[red]Failed to initialize pipeline: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.pass_context
def status(ctx):
    """Show pipeline status and statistics"""
    pipeline = ctx.obj['pipeline']
    
    try:
        stats = pipeline.get_stats()
        
        # Status panel
        status_text = f"Status: [bold green]{stats['status']}[/bold green]\n"
        status_text += f"Knowledge Base Files: {stats['kb_files']}\n"
        status_text += f"Vector Store: {'Ready' if stats['vector_store_exists'] else 'Not initialized'}"
        
        console.print(Panel(
            status_text,
            title="Pipeline Status",
            border_style="green" if stats['status'] == 'initialized' else "yellow"
        ))
        
        # KB files table
        if stats['kb_files'] > 0:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Knowledge Base Files")
            
            for filename in stats['kb_file_names']:
                table.add_row(filename)
                
            console.print("\nKnowledge Base:")
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")

@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the knowledge base and vector store"""
    pipeline = ctx.obj['pipeline']
    
    with console.status("[bold green]Building knowledge base..."):
        try:
            pipeline.initialize(force_rebuild=True)
            console.print("[green]Knowledge base initialized successfully![/green]")
            
            # Show stats
            stats = pipeline.get_stats()
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Property")
            table.add_column("Value")
            
            table.add_row("KB Files", str(stats['kb_files']))
            table.add_row("File Names", ", ".join(stats['kb_file_names']))
            table.add_row("Status", stats['status'])
            
            console.print("\nPipeline Statistics:")
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Initialization failed: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.argument('question')
@click.pass_context
def ask(ctx, question):
    """Ask a question about OpenTelemetry best practices"""
    pipeline = ctx.obj['pipeline']
    
    # Initialize pipeline if needed  
    if not pipeline.analyzer:
        with console.status("[dim]Initializing pipeline..."):
            pipeline.initialize()
    
    # Process question
    with console.status(f"[bold blue]Searching knowledge base..."):
        try:
            response = pipeline.interactive_analysis(question)
            
            console.print(Panel(
                response,
                title=f"Answer: {question}",
                border_style="blue"
            ))
            
        except Exception as e:
            console.print(f"[red]Query failed: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.argument('file_path')
@click.option('--query', '-q', help='Specific query to focus the analysis')
@click.option('--format', 'output_format', default='rich', type=click.Choice(['rich', 'json']), 
              help='Output format')
@click.pass_context
def analyze(ctx, file_path, query, output_format):
    """Analyze a specific file for OpenTelemetry violations"""
    pipeline = ctx.obj['pipeline']
    
    # Check if file exists
    if not os.path.exists(file_path):
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)
    
    # Initialize pipeline if needed
    if not pipeline.analyzer:
        with console.status("[dim]Initializing pipeline..."):
            pipeline.initialize()
    
    # Analyze file
    with console.status(f"[bold blue]Analyzing {file_path}..."):
        try:
            result = pipeline.analyze_file(file_path, query)
            
            if output_format == 'json':
                output = {
                    "summary": result.summary,
                    "violations": [
                        {
                            "rule_id": v.rule_id,
                            "severity": v.severity,
                            "file": v.file,
                            "line": v.line,
                            "message": v.message,
                            "fix_suggestion": v.fix_suggestion,
                            "code_snippet": v.code_snippet,
                            "kb_reference": v.kb_reference,
                            "confidence": v.confidence
                        }
                        for v in result.violations
                    ],
                    "rules_applied": result.rules_applied,
                    "kb_sections_used": result.kb_sections_used
                }
                console.print(json.dumps(output, indent=2))
            else:
                # Rich output
                title = f"Analysis Results: {Path(file_path).name}"
                if query:
                    title += f" (Focus: {query})"
                
                if not result.violations:
                    console.print(Panel(
                        "No violations found! Code appears to follow OpenTelemetry best practices.",
                        title=title,
                        border_style="green"
                    ))
                else:
                    # Summary
                    summary = result.summary
                    summary_text = f"Total Violations: [bold red]{summary.get('total_violations', 0)}[/bold red]\n"
                    
                    for severity in ['critical', 'high', 'medium', 'low']:
                        count = summary.get(severity, 0)
                        if count > 0:
                            color = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}[severity]
                            summary_text += f"{severity.capitalize()}: [{color}]{count}[/{color}] "
                    
                    console.print(Panel(summary_text, title="Summary", border_style="blue"))
                    
                    # Violations
                    console.print(f"\nFound {len(result.violations)} violation(s):\n")
                    
                    for i, violation in enumerate(result.violations, 1):
                        severity_colors = {
                            'critical': 'red',
                            'high': 'yellow', 
                            'medium': 'blue',
                            'low': 'dim'
                        }
                        
                        color = severity_colors.get(violation.severity, 'white')
                        
                        violation_text = f"[{color}]{violation.severity.upper()}[/{color}]: {violation.message}\n"
                        violation_text += f"Location: {violation.file}:{violation.line}\n"
                        violation_text += f"Fix: {violation.fix_suggestion}\n"
                        violation_text += f"Reference: {violation.kb_reference}\n"
                        violation_text += f"Confidence: {violation.confidence:.1%}"
                        
                        console.print(Panel(violation_text, title=f"Violation {i}", border_style=color))
                        console.print()
                
        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            if ctx.obj.get('verbose'):
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)

if __name__ == '__main__':
    cli()