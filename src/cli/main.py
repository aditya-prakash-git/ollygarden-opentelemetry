#!/usr/bin/env python3
"""
OpenTelemetry Instrumentation Validator CLI
Main command-line interface for the RAG-powered OTel validator
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

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.pipeline import RAGPipeline

# Initialize rich console for pretty output
console = Console()

@click.group()
@click.option('--kb-path', default='./knowledge_base', help='Path to knowledge base directory')
@click.option('--vector-store', default='./vector_store', help='Path to vector store directory') 
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, kb_path, vector_store, verbose):
    """
    🔍 OpenTelemetry Instrumentation Validator
    
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
def init(ctx):
    """
    🚀 Initialize the knowledge base and vector store
    """
    pipeline = ctx.obj['pipeline']
    
    with console.status("[bold green]Building knowledge base..."):
        try:
            pipeline.initialize(force_rebuild=True)
            console.print("✅ [green]Knowledge base initialized successfully![/green]")
            
            # Show stats
            stats = pipeline.get_stats()
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Property")
            table.add_column("Value")
            
            table.add_row("KB Files", str(stats['kb_files']))
            table.add_row("File Names", ", ".join(stats['kb_file_names']))
            table.add_row("Status", stats['status'])
            
            console.print("\n📊 Pipeline Statistics:")
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Initialization failed: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.argument('file_path')
@click.option('--query', '-q', help='Specific query to focus the analysis')
@click.option('--format', 'output_format', default='rich', type=click.Choice(['rich', 'json', 'markdown']), 
              help='Output format')
@click.pass_context
def analyze(ctx, file_path, query, output_format):
    """
    🔍 Analyze a specific file for OpenTelemetry violations
    
    FILE_PATH: Path to the source code file to analyze
    """
    pipeline = ctx.obj['pipeline']
    
    # Check if file exists
    if not os.path.exists(file_path):
        console.print(f"[red]❌ File not found: {file_path}[/red]")
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
                _output_json(result)
            elif output_format == 'markdown':
                _output_markdown(result, file_path, query)
            else:
                _output_rich(result, file_path, query)
                
        except Exception as e:
            console.print(f"[red]❌ Analysis failed: {e}[/red]")
            if ctx.obj.get('verbose'):
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)

@cli.command()
@click.argument('directory')
@click.option('--patterns', '-p', multiple=True, default=['*.py'], 
              help='File patterns to analyze (e.g., *.py, *.go)')
@click.option('--query', '-q', help='Specific query to focus the analysis')
@click.option('--format', 'output_format', default='rich', type=click.Choice(['rich', 'json']),
              help='Output format')
@click.pass_context  
def scan(ctx, directory, patterns, query, output_format):
    """
    🔍 Scan a directory for OpenTelemetry instrumentation issues
    
    DIRECTORY: Path to the directory to scan
    """
    pipeline = ctx.obj['pipeline']
    
    # Check if directory exists
    if not os.path.exists(directory):
        console.print(f"[red]❌ Directory not found: {directory}[/red]")
        sys.exit(1)
    
    # Initialize pipeline if needed
    if not pipeline.analyzer:
        with console.status("[dim]Initializing pipeline..."):
            pipeline.initialize()
    
    # Scan directory
    with console.status(f"[bold blue]Scanning {directory}..."):
        try:
            results = pipeline.analyze_directory(directory, list(patterns), query)
            
            if output_format == 'json':
                _output_scan_json(results)
            else:
                _output_scan_rich(results, directory, query)
                
        except Exception as e:
            console.print(f"[red]❌ Scan failed: {e}[/red]")
            if ctx.obj.get('verbose'):
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)

@cli.command()
@click.argument('question')
@click.pass_context
def ask(ctx, question):
    """
    💬 Ask a question about OpenTelemetry best practices
    
    QUESTION: Natural language question about OpenTelemetry instrumentation
    """
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
                title=f"💡 Answer: {question}",
                border_style="blue"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Query failed: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.pass_context
def status(ctx):
    """
    📊 Show pipeline status and statistics
    """
    pipeline = ctx.obj['pipeline']
    
    try:
        stats = pipeline.get_stats()
        
        # Status panel
        status_text = f"Status: [bold green]{stats['status']}[/bold green]\n"
        status_text += f"Knowledge Base Files: {stats['kb_files']}\n"
        status_text += f"Vector Store: {'✅ Ready' if stats['vector_store_exists'] else '❌ Not initialized'}"
        
        console.print(Panel(
            status_text,
            title="🔧 Pipeline Status",
            border_style="green" if stats['status'] == 'initialized' else "yellow"
        ))
        
        # KB files table
        if stats['kb_files'] > 0:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Knowledge Base Files")
            
            for filename in stats['kb_file_names']:
                table.add_row(filename)
                
            console.print("\n📚 Knowledge Base:")
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Status check failed: {e}[/red]")

def _output_rich(result, file_path, query):
    """Output analysis result in rich format"""
    
    # Header
    title = f"🔍 Analysis Results: {Path(file_path).name}"
    if query:
        title += f" (Focus: {query})"
    
    if not result.violations:
        console.print(Panel(
            "✅ No violations found! Code appears to follow OpenTelemetry best practices.",
            title=title,
            border_style="green"
        ))
        return
    
    # Summary
    summary = result.summary
    summary_text = f"Total Violations: [bold red]{summary.get('total_violations', 0)}[/bold red]\n"
    
    for severity in ['critical', 'high', 'medium', 'low']:
        count = summary.get(severity, 0)
        if count > 0:
            color = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}[severity]
            summary_text += f"{severity.capitalize()}: [{color}]{count}[/{color}] "
    
    console.print(Panel(summary_text, title="📊 Summary", border_style="blue"))
    
    # Violations
    console.print(f"\n🚨 Found {len(result.violations)} violation(s):\n")
    
    for i, violation in enumerate(result.violations, 1):
        severity_colors = {
            'critical': 'red',
            'high': 'yellow', 
            'medium': 'blue',
            'low': 'dim'
        }
        
        color = severity_colors.get(violation.severity, 'white')
        
        violation_text = f"[{color}]{violation.severity.upper()}[/{color}]: {violation.message}\n"
        violation_text += f"📍 Location: {violation.file}:{violation.line}\n"
        violation_text += f"🔧 Fix: {violation.fix_suggestion}\n"
        violation_text += f"📚 Reference: {violation.kb_reference}\n"
        violation_text += f"🎯 Confidence: {violation.confidence:.1%}"
        
        if violation.code_snippet:
            violation_text += f"\n\nCode:\n"
            syntax = Syntax(violation.code_snippet, "python", line_numbers=True)
            console.print(Panel(violation_text, title=f"Violation {i}", border_style=color))
            console.print(syntax)
        else:
            console.print(Panel(violation_text, title=f"Violation {i}", border_style=color))
        
        console.print()

def _output_json(result):
    """Output analysis result in JSON format"""
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

def _output_markdown(result, file_path, query):
    """Output analysis result in Markdown format"""
    md_content = f"# Analysis Results: {Path(file_path).name}\n\n"
    
    if query:
        md_content += f"**Query:** {query}\n\n"
    
    # Summary
    summary = result.summary
    md_content += f"## Summary\n\n"
    md_content += f"- **Total Violations:** {summary.get('total_violations', 0)}\n"
    
    for severity in ['critical', 'high', 'medium', 'low']:
        count = summary.get(severity, 0)
        if count > 0:
            md_content += f"- **{severity.capitalize()}:** {count}\n"
    
    # Violations
    if result.violations:
        md_content += f"\n## Violations\n\n"
        
        for i, violation in enumerate(result.violations, 1):
            md_content += f"### {i}. {violation.severity.upper()}: {violation.message}\n\n"
            md_content += f"- **Location:** `{violation.file}:{violation.line}`\n"
            md_content += f"- **Fix:** {violation.fix_suggestion}\n"
            md_content += f"- **Reference:** {violation.kb_reference}\n"
            md_content += f"- **Confidence:** {violation.confidence:.1%}\n"
            
            if violation.code_snippet:
                md_content += f"\n**Code:**\n```python\n{violation.code_snippet}\n```\n"
            
            md_content += "\n"
    else:
        md_content += "\n## ✅ No Violations Found\n\nCode appears to follow OpenTelemetry best practices.\n"
    
    console.print(md_content)

def _output_scan_rich(results, directory, query):
    """Output scan results in rich format"""
    
    title = f"🔍 Scan Results: {directory}"
    if query:
        title += f" (Focus: {query})"
    
    if not results:
        console.print(Panel(
            "❓ No files found or analyzed.",
            title=title,
            border_style="yellow"
        ))
        return
    
    # Overall summary
    total_violations = sum(len(result.violations) for result in results.values())
    total_files = len(results)
    files_with_issues = sum(1 for result in results.values() if result.violations)
    
    summary_text = f"Files Analyzed: [bold blue]{total_files}[/bold blue]\n"
    summary_text += f"Files with Issues: [bold red]{files_with_issues}[/bold red]\n"
    summary_text += f"Total Violations: [bold red]{total_violations}[/bold red]"
    
    console.print(Panel(summary_text, title="📊 Scan Summary", border_style="blue"))
    
    # Results per file
    for file_path, result in results.items():
        if result.violations:
            console.print(f"\n🚨 [bold red]{Path(file_path).name}[/bold red] - {len(result.violations)} violation(s)")
            
            for violation in result.violations[:3]:  # Show first 3 violations per file
                severity_colors = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}
                color = severity_colors.get(violation.severity, 'white')
                
                console.print(f"   [{color}]{violation.severity.upper()}[/{color}]: {violation.message}")
                console.print(f"   📍 Line {violation.line}")
        else:
            console.print(f"\n✅ [green]{Path(file_path).name}[/green] - No violations")

def _output_scan_json(results):
    """Output scan results in JSON format"""
    output = {}
    
    for file_path, result in results.items():
        output[file_path] = {
            "summary": result.summary,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity,
                    "line": v.line,
                    "message": v.message,
                    "fix_suggestion": v.fix_suggestion,
                    "kb_reference": v.kb_reference,
                    "confidence": v.confidence
                }
                for v in result.violations
            ]
        }
    
    console.print(json.dumps(output, indent=2))

if __name__ == '__main__':
    cli()