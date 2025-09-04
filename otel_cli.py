#!/usr/bin/env python3
"""
Updated OpenTelemetry CLI with Multi-Language Support
Supports Go, Python, JavaScript/TypeScript, Java, C#
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional, Dict
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Import the multi-language analyzer
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from multilang_analyzer import MultiLanguageOTelAnalyzer, TelemetryViolation
except ImportError:
    print("Could not import multilang_analyzer. Make sure the file is in the same directory.")
    sys.exit(1)

console = Console()

@click.group()
@click.option('--vector-store', default='./vector_store', help='Path to vector store directory')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, vector_store, verbose):
    """
    Multi-Language OpenTelemetry Analyzer
    
    Supports: Go, Python, JavaScript/TypeScript, Java, C#
    Validates naming conventions and telemetry best practices.
    """
    load_dotenv()
    ctx.ensure_object(dict)
    
    ctx.obj['vector_store'] = vector_store
    ctx.obj['verbose'] = verbose
    
    # Initialize analyzer with progress indicator
    with console.status("[bold green]Initializing multi-language analyzer..."):
        try:
            ctx.obj['analyzer'] = MultiLanguageOTelAnalyzer(vector_store)
            if verbose:
                console.print("[dim]Multi-language analyzer ready[/dim]")
        except Exception as e:
            console.print(f"[red]Failed to initialize analyzer: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.argument('file_path')
@click.option('--focus', '-f', help='Analysis focus (e.g., "naming conventions", "span patterns")')
@click.option('--format', 'output_format', default='rich', 
              type=click.Choice(['rich', 'json', 'summary']), help='Output format')
@click.option('--confidence-threshold', default=0.7, type=float,
              help='Minimum confidence for reporting violations (0.0-1.0)')
@click.pass_context
def analyze(ctx, file_path, focus, output_format, confidence_threshold):
    """
    Analyze OpenTelemetry patterns in any supported language
    
    FILE_PATH: Source code file to analyze
    """
    analyzer = ctx.obj['analyzer']
    
    if not os.path.exists(file_path):
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)
    
    # Show analysis progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Read file
        task1 = progress.add_task("Reading file...", total=None)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]Failed to read file: {e}[/red]")
            sys.exit(1)
        progress.remove_task(task1)
        
        # Analyze
        task2 = progress.add_task("Multi-language analysis...", total=None)
        try:
            result = analyzer.analyze_telemetry_patterns(code, file_path, focus)
            
            # Apply confidence threshold
            filtered_violations = [
                v for v in result['violations'] 
                if v.confidence >= confidence_threshold
            ]
            result['violations'] = filtered_violations
            result['summary']['total_violations'] = len(filtered_violations)
            
        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            if ctx.obj.get('verbose'):
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)
        progress.remove_task(task2)
    
    # Output results
    if output_format == 'json':
        _output_json(result)
    elif output_format == 'summary':
        _output_summary(result, file_path, focus)
    else:
        _output_rich_detailed(result, file_path, focus, confidence_threshold)

@cli.command()
@click.argument('directory')
@click.option('--patterns', '-p', multiple=True, 
              default=['*.go', '*.py', '*.js', '*.ts', '*.java', '*.cs'], 
              help='File patterns to analyze')
@click.option('--focus', help='Analysis focus')
@click.option('--format', 'output_format', default='rich', 
              type=click.Choice(['rich', 'json']), help='Output format')
@click.pass_context  
def scan(ctx, directory, patterns, focus, output_format):
    """
    Scan directory for OpenTelemetry patterns across languages
    
    DIRECTORY: Path to the directory to scan
    """
    analyzer = ctx.obj['analyzer']
    
    if not os.path.exists(directory):
        console.print(f"[red]Directory not found: {directory}[/red]")
        sys.exit(1)
    
    # Find files
    files_to_analyze = []
    dir_path = Path(directory)
    files_found = set()
    for pattern in patterns:
        files_found.update(dir_path.rglob(pattern))
    files_to_analyze = list(files_found)
    
    if not files_to_analyze:
        console.print(f"[yellow]No files found matching patterns: {patterns}[/yellow]")
        return
    
    console.print(f"Found {len(files_to_analyze)} files to analyze")
    
    # Analyze each file
    results = {}
    with Progress(console=console) as progress:
        task = progress.add_task("Scanning files...", total=len(files_to_analyze))
        
        for file_path in files_to_analyze:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                result = analyzer.analyze_telemetry_patterns(code, str(file_path), focus)
                if result['violations']:  # Only store files with violations
                    results[str(file_path)] = result
                    
                progress.advance(task)
                
            except Exception as e:
                console.print(f"[red]Error analyzing {file_path}: {e}[/red]")
                continue
    
    # Output results
    if output_format == 'json':
        _output_scan_json(results)
    else:
        _output_scan_rich(results, directory, focus)

@cli.command()
@click.argument('question')
@click.pass_context
def ask(ctx, question):
    """
    Ask about OpenTelemetry best practices
    """
    analyzer = ctx.obj['analyzer']
    
    with console.status("Searching knowledge base..."):
        try:
            docs = analyzer.vectorstore.similarity_search(
                f"OpenTelemetry {question}", k=3
            )
            
            if not docs:
                console.print(f"[yellow]No information found for: {question}[/yellow]")
                return
            
            response = f"Knowledge Base Results: {question}\n\n"
            
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get('source', 'unknown')
                content = doc.page_content[:300]
                response += f"**{i}. {source}**\n{content}{'...' if len(doc.page_content) > 300 else ''}\n\n"
            
            console.print(Panel(response, title="Knowledge Base Results", border_style="blue"))
            
        except Exception as e:
            console.print(f"[red]Knowledge base query failed: {e}[/red]")

def _output_rich_detailed(result: Dict, file_path: str, focus: Optional[str], confidence_threshold: float):
    """Rich detailed output with language and detection info"""
    
    title = f"Multi-Language Analysis: {Path(file_path).name}"
    if result.get('language'):
        title += f" ({result['language'].upper()})"
    if focus:
        title += f" (Focus: {focus})"
    
    violations = result['violations']
    summary = result['summary']
    
    if not violations:
        console.print(Panel(
            f"**No violations found!**\n\n"
            f"**Analysis Summary:**\n"
            f"• Language: {result.get('language', 'unknown').upper()}\n"
            f"• Patterns detected: {result['total_patterns']}\n"
            f"• Confidence threshold: {confidence_threshold:.1%}\n"
            f"• All telemetry patterns follow OpenTelemetry best practices",
            title=title,
            border_style="green"
        ))
        return
    
    # Violations summary
    summary_text = f"**{len(violations)} violations found**\n\n"
    summary_text += f"**Analysis Summary:**\n"
    summary_text += f"• Language: {result.get('language', 'unknown').upper()}\n"
    summary_text += f"• Total patterns detected: {result['total_patterns']}\n"
    summary_text += f"• Confidence threshold: {confidence_threshold:.1%}\n"
    
    # Show severity breakdown
    severity_counts = summary.get('by_severity', {})
    if severity_counts:
        summary_text += f"• By severity: "
        for severity, count in severity_counts.items():
            color = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}[severity]
            summary_text += f"[{color}]{severity}: {count}[/{color}] "
    
    # Show type breakdown
    type_counts = summary.get('by_type', {})
    if type_counts:
        summary_text += f"\n• By type: "
        for vtype, count in type_counts.items():
            summary_text += f"{vtype}: {count} "
    
    console.print(Panel(summary_text, title=title, border_style="red"))
    
    # Detailed violations
    console.print(f"\n**Detailed Violations:**\n")
    
    for i, violation in enumerate(violations, 1):
        color = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}[violation.severity]
        
        violation_panel = f"[{color}]{violation.severity.upper()}[/{color}]: {violation.description}\n\n"
        violation_panel += f"**Location**: Line {violation.location.line_number}, Column {violation.location.column}\n"
        violation_panel += f"**Function**: `{violation.location.function_name}`\n"
        violation_panel += f"**Language**: {violation.language.upper()}\n"
        violation_panel += f"**Fix**: {violation.fix_suggestion}\n"
        violation_panel += f"**Rule**: {violation.rule_violated}\n"
        violation_panel += f"**Confidence**: {violation.confidence:.1%}\n\n"
        violation_panel += f"**Code Context:**"
        
        console.print(Panel(
            violation_panel,
            title=f"Violation {i}: {violation.violation_type.replace('_', ' ').title()}",
            border_style=color
        ))
        
        # Show code context with syntax highlighting
        context_code = "\n".join(violation.location.context_lines)
        start_line = max(1, violation.location.line_number - 2)
        
        # Use language for syntax highlighting
        lang_map = {
            'go': 'go',
            'python': 'python', 
            'javascript': 'javascript',
            'typescript': 'typescript',
            'java': 'java',
            'csharp': 'csharp'
        }
        syntax_lang = lang_map.get(violation.language, 'text')
        
        syntax = Syntax(context_code, syntax_lang, line_numbers=True, start_line=start_line,
                       highlight_lines={violation.location.line_number})
        console.print(syntax)
        console.print()

def _output_summary(result: Dict, file_path: str, focus: Optional[str]):
    """Concise summary output"""
    violations = result['violations']
    language = result.get('language', 'unknown')
    
    console.print(f"**{Path(file_path).name}** ({language.upper()})")
    
    if not violations:
        console.print("[green]No violations[/green]")
        return
    
    console.print(f"[red]{len(violations)} violations[/red]")
    
    # Group by severity and type
    by_severity = {}
    by_type = {}
    
    for v in violations:
        by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
    
    # Show severity breakdown
    for severity in ['critical', 'high', 'medium', 'low']:
        count = by_severity.get(severity, 0)
        if count > 0:
            color = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}[severity]
            console.print(f"  [{color}]{severity}: {count}[/{color}]")
    
    # Show top violations
    console.print(f"\n**Top Issues:**")
    for i, v in enumerate(violations[:3], 1):
        console.print(f"Line {v.location.line_number}: {v.description}")

def _output_json(result: Dict):
    """JSON output for programmatic use"""
    
    json_result = {
        "file_path": result["file_path"],
        "language": result.get("language", "unknown"),
        "total_patterns_detected": result["total_patterns"],
        "summary": result["summary"],
        "violations": [
            {
                "violation_id": v.violation_id,
                "severity": v.severity,
                "line_number": v.location.line_number,
                "column": v.location.column,
                "function_name": v.location.function_name,
                "violation_type": v.violation_type,
                "rule_violated": v.rule_violated,
                "description": v.description,
                "fix_suggestion": v.fix_suggestion,
                "kb_reference": v.kb_reference,
                "confidence": v.confidence,
                "detection_method": v.detection_method,
                "language": v.language,
                "code_snippet": v.location.code_snippet,
                "context_lines": v.location.context_lines
            }
            for v in result["violations"]
        ],
        "kb_sections_used": result["kb_sections_used"]
    }
    
    console.print(json.dumps(json_result, indent=2))

def _output_scan_rich(results: Dict, directory: str, focus: Optional[str]):
    """Rich output for directory scan results"""
    
    title = f"Directory Scan: {directory}"
    if focus:
        title += f" (Focus: {focus})"
    
    if not results:
        console.print(Panel(
            "No violations found in scanned files.",
            title=title,
            border_style="green"
        ))
        return
    
    # Overall summary
    total_violations = sum(len(result['violations']) for result in results.values())
    total_files = len(results)
    
    # Group by language
    by_language = {}
    for result in results.values():
        lang = result.get('language', 'unknown')
        by_language[lang] = by_language.get(lang, 0) + len(result['violations'])
    
    summary_text = f"Files with violations: {total_files}\n"
    summary_text += f"Total violations: {total_violations}\n"
    summary_text += f"Languages: {', '.join(by_language.keys())}"
    
    console.print(Panel(summary_text, title="Scan Summary", border_style="blue"))
    
    # Results per file
    for file_path, result in results.items():
        violations = result['violations']
        language = result.get('language', 'unknown')
        
        console.print(f"\n[bold]{Path(file_path).name}[/bold] ({language.upper()}) - {len(violations)} violation(s)")
        
        for violation in violations[:3]:  # Show first 3 violations per file
            severity_colors = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}
            color = severity_colors.get(violation.severity, 'white')
            
            console.print(f"   [{color}]{violation.severity.upper()}[/{color}]: {violation.description}")
            console.print(f"   Line {violation.location.line_number}: {violation.fix_suggestion}")

def _output_scan_json(results: Dict):
    """JSON output for directory scan"""
    output = {}
    
    for file_path, result in results.items():
        output[file_path] = {
            "language": result.get("language", "unknown"),
            "total_patterns": result["total_patterns"],
            "summary": result["summary"],
            "violations": [
                {
                    "violation_id": v.violation_id,
                    "severity": v.severity,
                    "line_number": v.location.line_number,
                    "violation_type": v.violation_type,
                    "rule_violated": v.rule_violated,
                    "description": v.description,
                    "fix_suggestion": v.fix_suggestion,
                    "confidence": v.confidence,
                    "language": v.language
                }
                for v in result["violations"]
            ]
        }
    
    console.print(json.dumps(output, indent=2))

if __name__ == '__main__':
    cli()