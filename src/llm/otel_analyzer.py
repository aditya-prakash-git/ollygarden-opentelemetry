"""
OpenTelemetry Code Analyzer using RAG Pipeline
Analyzes code against OTel best practices using retrieved knowledge
"""

import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from pydantic import BaseModel
import json
import re

class Violation(BaseModel):
    """Structure for code violations"""
    rule_id: str
    severity: str  # critical, high, medium, low
    file: str
    line: int
    message: str
    fix_suggestion: str
    code_snippet: str
    kb_reference: str  # Which KB section this comes from
    confidence: float  # 0.0-1.0

class AnalysisResult(BaseModel):
    """Complete analysis result"""
    summary: Dict[str, Any]
    violations: List[Violation]
    rules_applied: List[str]
    kb_sections_used: List[str]

class OTelAnalyzer:
    def __init__(self, vector_store_path: str):
        self.vector_store_path = vector_store_path
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,  # Low temperature for consistency
            max_tokens=2000
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"  # Cheaper and faster than ada-002
        )
        self.vectorstore = self._load_vector_store()
    
    def _load_vector_store(self) -> Chroma:
        """Load existing vector store"""
        if not os.path.exists(self.vector_store_path):
            raise ValueError(f"Vector store not found at {self.vector_store_path}")
        
        return Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )
    
    def analyze_code(self, code: str, file_path: str, query: str = None) -> AnalysisResult:
        """
        Analyze code against OTel best practices using RAG
        
        Args:
            code: Source code to analyze
            file_path: Path to the file being analyzed
            query: Optional specific query (e.g., "check naming conventions")
        """
        
        # Step 1: Retrieve relevant knowledge
        if query:
            search_query = f"{query} OpenTelemetry instrumentation"
        else:
            search_query = f"OpenTelemetry instrumentation best practices {self._extract_code_context(code)}"
        
        relevant_docs = self.vectorstore.similarity_search(
            search_query, 
            k=8  # Get top 8 most relevant chunks
        )
        
        # Step 2: Build structured prompt with retrieved context
        prompt = self._build_analysis_prompt(code, file_path, relevant_docs, query)
        
        # Step 3: Get LLM analysis
        response = self.llm.invoke(prompt)
        
        # Step 4: Parse structured response
        analysis_result = self._parse_llm_response(response.content, relevant_docs)
        
        return analysis_result
    
    def _extract_code_context(self, code: str) -> str:
        """Extract key context from code for better retrieval"""
        context_keywords = []
        
        # Look for telemetry-related patterns
        patterns = {
            "http": r"(?:http|HTTP|request|response|server|client)",
            "database": r"(?:db|database|sql|query|select|insert|update)",
            "messaging": r"(?:queue|topic|message|publish|subscribe|kafka|rabbitmq)",
            "spans": r"(?:span|trace|tracer|start_span|with_span)",
            "metrics": r"(?:metric|counter|histogram|gauge|meter)",
            "errors": r"(?:error|exception|try|catch|raise)"
        }
        
        for category, pattern in patterns.items():
            if re.search(pattern, code, re.IGNORECASE):
                context_keywords.append(category)
        
        return " ".join(context_keywords)
    
    def _build_analysis_prompt(self, code: str, file_path: str, docs: List[Document], query: str = None) -> str:
        """Build structured prompt for LLM analysis"""
        
        # Extract knowledge base context
        kb_context = "\n\n".join([
            f"KB Reference: {doc.metadata.get('source', 'unknown')}\n"
            f"Type: {doc.metadata.get('type', 'unknown')}\n"
            f"Content: {doc.page_content}"
            for doc in docs
        ])
        
        base_prompt = f"""
You are an OpenTelemetry instrumentation expert. Analyze the provided code against the OpenTelemetry best practices from the knowledge base.

KNOWLEDGE BASE CONTEXT:
{kb_context}

CODE TO ANALYZE:
File: {file_path}
```
{code}
```

ANALYSIS REQUIREMENTS:
1. Only identify violations that are explicitly mentioned in the knowledge base context above
2. Do not make up rules - only use the provided KB references
3. For each violation, provide:
   - Specific rule violated (reference the KB)
   - Exact location in code (line number if possible)
   - Clear explanation of why it's wrong
   - Actionable fix suggestion
   - Confidence level (0.0-1.0)

4. Classify severity as:
   - critical: Will cause production issues
   - high: Violates important best practices
   - medium: Suboptimal but functional
   - low: Style/consistency issues

OUTPUT FORMAT (JSON):
{{
  "violations": [
    {{
      "rule_id": "SPAN_001",
      "severity": "high",
      "file": "{file_path}",
      "line": 45,
      "message": "Creating span for internal function violates boundary-only principle",
      "fix_suggestion": "Remove span from validate_item() function, spans should only be at application boundaries",
      "code_snippet": "with tracer.start_span('validate_item'):",
      "kb_reference": "instrumentation.md - Span Creation Rules",
      "confidence": 0.9
    }}
  ],
  "summary": {{
    "total_violations": 1,
    "critical": 0,
    "high": 1,
    "medium": 0,
    "low": 0
  }},
  "rules_applied": ["span_creation", "error_handling"],
  "kb_sections_used": ["Span Creation Rules", "Error Handling"]
}}
"""

        if query:
            base_prompt += f"\n\nSPECIFIC FOCUS: {query}"
        
        base_prompt += "\n\nProvide your analysis in the exact JSON format above:"
        
        return base_prompt
    
    def _parse_llm_response(self, response: str, kb_docs: List[Document]) -> AnalysisResult:
        """Parse LLM response into structured result"""
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                violations = [
                    Violation(**violation) for violation in data.get("violations", [])
                ]
                
                return AnalysisResult(
                    summary=data.get("summary", {}),
                    violations=violations,
                    rules_applied=data.get("rules_applied", []),
                    kb_sections_used=data.get("kb_sections_used", [])
                )
            else:
                # Fallback: create result from text analysis
                return self._fallback_parse(response, kb_docs)
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse LLM response: {e}")
            return self._fallback_parse(response, kb_docs)
    
    def _fallback_parse(self, response: str, kb_docs: List[Document]) -> AnalysisResult:
        """Fallback parsing when JSON parsing fails"""
        # Simple text-based parsing for demo purposes
        violations = []
        
        # Look for common violation patterns in text
        violation_patterns = [
            r"violation.*?(?=\n|$)",
            r"issue.*?(?=\n|$)",
            r"problem.*?(?=\n|$)"
        ]
        
        for pattern in violation_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for i, match in enumerate(matches[:3]):  # Limit to 3 for demo
                violations.append(Violation(
                    rule_id=f"PARSED_{i+1}",
                    severity="medium",
                    file="unknown",
                    line=0,
                    message=match.strip(),
                    fix_suggestion="Review code against OpenTelemetry best practices",
                    code_snippet="",
                    kb_reference="Knowledge base",
                    confidence=0.5
                ))
        
        return AnalysisResult(
            summary={"total_violations": len(violations)},
            violations=violations,
            rules_applied=["text_analysis"],
            kb_sections_used=[doc.metadata.get("source", "unknown") for doc in kb_docs]
        )
    
    def query_knowledge_base(self, question: str, k: int = 5) -> List[Document]:
        """Direct KB query for interactive use"""
        return self.vectorstore.similarity_search(question, k=k)