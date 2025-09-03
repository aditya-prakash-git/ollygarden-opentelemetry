"""
RAG Pipeline Orchestrator
Coordinates knowledge processing, vector store, and analysis
"""

import os
from pathlib import Path
from typing import Dict, List, Any
from .knowledge_processor import KnowledgeProcessor
from ..llm.otel_analyzer import OTelAnalyzer, AnalysisResult
import logging

class RAGPipeline:
    def __init__(self, 
                 kb_path: str = "./knowledge_base",
                 vector_store_path: str = "./vector_store"):
        self.kb_path = kb_path
        self.vector_store_path = vector_store_path
        self.knowledge_processor = KnowledgeProcessor(kb_path, vector_store_path)
        self.analyzer = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, force_rebuild: bool = False):
        """Initialize the RAG pipeline"""
        
        # Check if vector store exists
        if not os.path.exists(self.vector_store_path) or force_rebuild:
            self.logger.info("Building knowledge base vector store...")
            self._build_knowledge_base()
        else:
            self.logger.info("Using existing vector store")
        
        # Initialize analyzer
        self.analyzer = OTelAnalyzer(self.vector_store_path)
        self.logger.info("RAG Pipeline initialized successfully")
    
    def _build_knowledge_base(self):
        """Build the vector store from knowledge base files"""
        
        # Validate KB files exist
        kb_files = list(Path(self.kb_path).glob("*.md"))
        if not kb_files:
            raise ValueError(f"No markdown files found in {self.kb_path}")
        
        self.logger.info(f"Found {len(kb_files)} KB files: {[f.name for f in kb_files]}")
        
        # Process and chunk knowledge base
        chunks = self.knowledge_processor.load_and_chunk_kb()
        self.logger.info(f"Extracted {len(chunks)} knowledge chunks")
        
        # Build vector store
        vectorstore = self.knowledge_processor.build_vector_store(chunks)
        self.logger.info("Vector store built and persisted")
        
        return vectorstore
    
    def analyze_file(self, file_path: str, query: str = None) -> AnalysisResult:
        """Analyze a single file"""
        if not self.analyzer:
            raise ValueError("Pipeline not initialized. Call initialize() first")
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {e}")
        
        # Analyze code
        result = self.analyzer.analyze_code(code, file_path, query)
        
        return result
    
    def analyze_directory(self, dir_path: str, 
                         file_patterns: List[str] = None,
                         query: str = None) -> Dict[str, AnalysisResult]:
        """Analyze multiple files in a directory"""
        if not self.analyzer:
            raise ValueError("Pipeline not initialized. Call initialize() first")
        
        if file_patterns is None:
            file_patterns = ["*.py", "*.go", "*.js", "*.ts", "*.java"]
        
        results = {}
        dir_path = Path(dir_path)
        
        # Find all matching files
        files_to_analyze = []
        for pattern in file_patterns:
            files_to_analyze.extend(dir_path.rglob(pattern))
        
        self.logger.info(f"Found {len(files_to_analyze)} files to analyze")
        
        # Analyze each file
        for file_path in files_to_analyze:
            try:
                self.logger.info(f"Analyzing {file_path}")
                result = self.analyze_file(str(file_path), query)
                results[str(file_path)] = result
            except Exception as e:
                self.logger.error(f"Failed to analyze {file_path}: {e}")
                continue
        
        return results
    
    def query_kb(self, question: str) -> List[Dict[str, Any]]:
        """Query the knowledge base directly"""
        if not self.analyzer:
            raise ValueError("Pipeline not initialized. Call initialize() first")
        
        docs = self.analyzer.query_knowledge_base(question)
        
        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "type": doc.metadata.get("type", "unknown")
            }
            for doc in docs
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        if not os.path.exists(self.vector_store_path):
            return {"status": "not_initialized"}
        
        kb_files = list(Path(self.kb_path).glob("*.md"))
        
        stats = {
            "status": "initialized" if self.analyzer else "loaded",
            "kb_files": len(kb_files),
            "kb_file_names": [f.name for f in kb_files],
            "vector_store_exists": os.path.exists(self.vector_store_path),
            "vector_store_path": self.vector_store_path
        }
        
        return stats
    
    def interactive_analysis(self, prompt: str, file_path: str = None) -> str:
        """
        Handle natural language queries about code analysis
        
        Examples:
        - "Tell me how the tracing instrumentation follows naming conventions"
        - "What violations exist in this code?"
        - "Check for span creation anti-patterns"
        """
        
        if not self.analyzer:
            raise ValueError("Pipeline not initialized. Call initialize() first")
        
        # If file provided, analyze it with the prompt as query
        if file_path and os.path.exists(file_path):
            result = self.analyze_file(file_path, prompt)
            return self._format_analysis_response(result, prompt)
        
        # Otherwise, query the knowledge base
        kb_results = self.query_kb(prompt)
        return self._format_kb_response(kb_results, prompt)
    
    def _format_analysis_response(self, result: AnalysisResult, prompt: str) -> str:
        """Format analysis result as natural language"""
        
        if not result.violations:
            return f"✅ Great! No violations found for: {prompt}\n\nThe code appears to follow OpenTelemetry best practices."
        
        response = f"📋 Analysis Results for: {prompt}\n\n"
        response += f"**Summary**: {result.summary.get('total_violations', 0)} violations found\n\n"
        
        for violation in result.violations:
            severity_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "⚡",
                "low": "💡"
            }.get(violation.severity, "📝")
            
            response += f"{severity_emoji} **{violation.severity.upper()}**: {violation.message}\n"
            response += f"   📍 {violation.file}:{violation.line}\n"
            response += f"   💡 Fix: {violation.fix_suggestion}\n"
            response += f"   📚 Reference: {violation.kb_reference}\n\n"
        
        response += f"**Knowledge Base Sections Used**: {', '.join(result.kb_sections_used)}"
        
        return response
    
    def _format_kb_response(self, kb_results: List[Dict], prompt: str) -> str:
        """Format KB query response as natural language"""
        
        if not kb_results:
            return f"❓ No relevant information found for: {prompt}"
        
        response = f"📚 Knowledge Base Results for: {prompt}\n\n"
        
        for i, result in enumerate(kb_results[:3], 1):  # Show top 3
            response += f"**{i}. {result['source']} ({result['type']})**\n"
            response += f"{result['content'][:300]}{'...' if len(result['content']) > 300 else ''}\n\n"
        
        return response