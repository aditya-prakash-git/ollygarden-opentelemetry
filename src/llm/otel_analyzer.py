"""
Smart Hybrid OpenTelemetry Analyzer
RAG-first approach with accuracy fallbacks for precise line detection
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from pydantic import BaseModel
import time
from dataclasses import dataclass

@dataclass
class CodeLocation:
    line_number: int
    column: int
    function_name: str
    code_snippet: str
    context_lines: List[str]

@dataclass 
class SpanViolation:
    violation_id: str
    severity: str
    file_path: str
    location: CodeLocation
    violation_type: str
    rule_violated: str
    description: str
    fix_suggestion: str
    kb_reference: str
    confidence: float
    detection_method: str  # "learned_from_kb" or "fallback_pattern"

class SmartPatternDetector:
    """RAG-first pattern detection with accuracy fallbacks"""
    
    def __init__(self, vectorstore: Chroma, llm: ChatOpenAI):
        self.vectorstore = vectorstore
        self.llm = llm
        
        # Try to learn patterns from KB first
        print("🧠 Learning patterns from knowledge base...")
        self.learned_patterns = self._learn_patterns_from_kb()
        
        # Essential fallback patterns for accuracy guarantee
        self.fallback_patterns = {
            "span_creation": {
                "regex": r"(tracer\.start_span|with\s+.*\.start_span)\s*\(\s*[\"']([^\"']+)[\"']",
                "violation_type": "span_creation",
                "description": "Manual span creation detected"
            },
            "nested_spans": {
                "regex": r"with\s+.*start_span.*:\s*\n(?:.*\n)*?\s+with\s+.*start_span",
                "violation_type": "span_boundary", 
                "description": "Nested span creation detected"
            },
            "span_in_function": {
                "regex": r"def\s+(\w+).*?:\s*(?:[^\n]*\n)*?\s*with.*start_span",
                "violation_type": "span_boundary",
                "description": "Span creation in function definition"
            },
            "error_record_and_raise": {
                "regex": r"(span\.record_exception|span\.set_status).*\n.*raise",
                "violation_type": "error_handling",
                "description": "Recording error and raising exception"
            }
        }
        
        print(f"✅ Learned {len(self.learned_patterns)} patterns from KB")
        print(f"🛡️ Fallback patterns available: {len(self.fallback_patterns)}")
    
    def _learn_patterns_from_kb(self) -> Dict[str, Dict]:
        """Learn violation patterns from knowledge base using RAG"""
        
        # Query KB for different types of violations
        pattern_queries = [
            "span creation violations anti-patterns boundary",
            "error handling violations span record exception",
            "naming convention violations span names",
            "internal function span violations boundaries"
        ]
        
        learned_patterns = {}
        
        for query in pattern_queries:
            try:
                # Get relevant KB content
                docs = self.vectorstore.similarity_search(query, k=3)
                
                if not docs:
                    continue
                
                # Extract patterns using LLM
                kb_content = "\n\n".join([doc.page_content for doc in docs])
                patterns = self._extract_patterns_with_llm(kb_content, query)
                
                # Merge patterns
                learned_patterns.update(patterns)
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"⚠️ Failed to learn patterns for '{query}': {e}")
                continue
        
        return learned_patterns
    
    def _extract_patterns_with_llm(self, kb_content: str, query_context: str) -> Dict[str, Dict]:
        """Extract regex patterns from KB content using LLM"""
        
        prompt = f"""
Extract code violation patterns from this OpenTelemetry knowledge base content.

QUERY CONTEXT: {query_context}

KNOWLEDGE BASE CONTENT:
{kb_content}

TASK: For each violation mentioned, create a regex pattern that can detect it in Python code.

REQUIREMENTS:
1. Only extract patterns for violations explicitly mentioned in the KB
2. Create Python regex patterns that match the violation code
3. Focus on patterns that can give precise line locations
4. Include violation metadata

OUTPUT FORMAT (JSON only):
{{
  "patterns": [
    {{
      "name": "descriptive_name",
      "regex": "python_regex_pattern",
      "violation_type": "span_creation|span_boundary|error_handling|span_naming", 
      "severity": "critical|high|medium|low",
      "description": "what this pattern detects",
      "kb_rule": "the specific rule from KB this relates to"
    }}
  ]
}}

Focus on creating patterns that are:
- Specific enough to avoid false positives
- Broad enough to catch real violations
- Able to provide exact line locations

Response:"""
        
        try:
            response = self.llm.invoke(prompt)
            result = json.loads(response.content.strip())
            
            patterns = {}
            for pattern_info in result.get("patterns", []):
                name = pattern_info.get("name", f"learned_pattern_{len(patterns)}")
                patterns[name] = {
                    "regex": pattern_info["regex"],
                    "violation_type": pattern_info["violation_type"],
                    "severity": pattern_info.get("severity", "medium"),
                    "description": pattern_info["description"],
                    "kb_rule": pattern_info.get("kb_rule", "Extracted from KB"),
                    "source": "learned_from_kb"
                }
            
            return patterns
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ Pattern extraction failed: {e}")
            return {}
    
    def find_patterns(self, code: str, file_path: str) -> List[Dict]:
        """Find patterns using learned patterns first, fallback if needed"""
        
        detected_patterns = []
        lines = code.split('\n')
        
        # Method 1: Try learned patterns first (RAG-driven)
        if self.learned_patterns:
            detected_patterns.extend(
                self._detect_with_patterns(code, lines, self.learned_patterns, "learned_from_kb")
            )
        
        # Method 2: Use fallback patterns for coverage guarantee
        fallback_detected = self._detect_with_patterns(
            code, lines, self.fallback_patterns, "fallback_pattern"
        )
        
        # Merge results, avoiding duplicates (prefer learned patterns)
        detected_patterns.extend(self._merge_patterns(detected_patterns, fallback_detected))
        
        return detected_patterns
    
    def _detect_with_patterns(self, code: str, lines: List[str], 
                             patterns: Dict, detection_method: str) -> List[Dict]:
        """Detect patterns using given pattern set"""
        
        detected = []
        
        for pattern_name, pattern_info in patterns.items():
            try:
                regex = pattern_info["regex"]
                
                # Multi-line search
                matches = list(re.finditer(regex, code, re.MULTILINE | re.DOTALL))
                
                for match in matches:
                    # Find the line number
                    line_num = code[:match.start()].count('\n') + 1
                    
                    # Get context
                    start_context = max(0, line_num - 4)
                    end_context = min(len(lines), line_num + 3)
                    context_lines = lines[start_context:end_context]
                    
                    detected.append({
                        "pattern_name": pattern_name,
                        "line_number": line_num,
                        "column": match.start() - code.rfind('\n', 0, match.start()),
                        "matched_text": match.group(0),
                        "violation_type": pattern_info["violation_type"],
                        "severity": pattern_info.get("severity", "medium"),
                        "description": pattern_info["description"],
                        "kb_rule": pattern_info.get("kb_rule", "Pattern-based detection"),
                        "context_lines": context_lines,
                        "function_name": self._get_function_name(lines, line_num - 1),
                        "detection_method": detection_method,
                        "confidence": 0.9 if detection_method == "learned_from_kb" else 0.8
                    })
                    
            except re.error as e:
                print(f"⚠️ Invalid regex in pattern '{pattern_name}': {e}")
                continue
        
        return detected
    
    def _merge_patterns(self, learned_patterns: List[Dict], fallback_patterns: List[Dict]) -> List[Dict]:
        """Merge patterns, avoiding duplicates (prefer learned patterns)"""
        
        merged = []
        learned_lines = {p["line_number"] for p in learned_patterns}
        
        for pattern in fallback_patterns:
            # Only add fallback if no learned pattern detected on same line
            if pattern["line_number"] not in learned_lines:
                merged.append(pattern)
        
        return merged
    
    def _get_function_name(self, lines: List[str], current_line: int) -> str:
        """Find function containing current line"""
        for i in range(current_line, max(0, current_line - 30), -1):
            if i < len(lines):
                func_match = re.match(r'\s*def\s+(\w+)', lines[i])
                if func_match:
                    return func_match.group(1)
        return "unknown"

class SmartHybridSpanAnalyzer:
    """Smart hybrid analyzer: RAG-first with accuracy fallbacks"""
    
    def __init__(self, vector_store_path: str):
        self.vector_store_path = vector_store_path
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,  # Zero temperature for consistency
            max_tokens=1500
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = self._load_vector_store()
        
        # Initialize smart pattern detector
        self.pattern_detector = SmartPatternDetector(self.vectorstore, self.llm)
    
    def _load_vector_store(self) -> Chroma:
        """Load existing vector store"""
        if not os.path.exists(self.vector_store_path):
            raise ValueError(f"Vector store not found at {self.vector_store_path}")
        
        return Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )
    
    def analyze_spans(self, code: str, file_path: str, query: str = None) -> Dict[str, Any]:
        """
        Smart hybrid span analysis:
        1. Detect patterns using learned + fallback patterns
        2. Validate each pattern against KB using RAG
        3. Return high-confidence violations only
        """
        
        # Step 1: Pattern detection (hybrid approach)
        print("🔍 Detecting span patterns...")
        detected_patterns = self.pattern_detector.find_patterns(code, file_path)
        
        if not detected_patterns:
            return {
                "file_path": file_path,
                "total_patterns": 0,
                "violations": [],
                "summary": {"total_violations": 0},
                "kb_sections_used": []
            }
        
        print(f"📊 Found {len(detected_patterns)} potential patterns")
        
        # Step 2: KB-driven validation of each pattern
        print("🧠 Validating patterns against knowledge base...")
        violations = []
        kb_docs_used = []
        
        for pattern in detected_patterns:
            # Get relevant KB rules for this pattern type
            kb_query = f"{pattern['violation_type']} violations {query or ''} OpenTelemetry"
            relevant_docs = self.vectorstore.similarity_search(kb_query, k=3)
            kb_docs_used.extend(relevant_docs)
            
            # Validate pattern against KB
            violation = self._validate_pattern_with_rag(pattern, relevant_docs, code)
            if violation and violation.confidence > 0.7:
                violations.append(violation)
        
        return {
            "file_path": file_path,
            "total_patterns": len(detected_patterns),
            "violations": violations,
            "summary": self._create_summary(violations),
            "kb_sections_used": list(set([doc.metadata.get("source", "unknown") for doc in kb_docs_used]))
        }
    
    def _validate_pattern_with_rag(self, pattern: Dict, kb_docs: List[Document], 
                                  full_code: str) -> Optional[SpanViolation]:
        """Validate detected pattern against KB rules using RAG"""
        
        # Build KB context
        kb_context = "\n\n".join([
            f"Rule Source: {doc.metadata.get('source', 'unknown')}\n"
            f"Content: {doc.page_content[:400]}"
            for doc in kb_docs
        ])
        
        prompt = f"""
You are validating a detected code pattern against OpenTelemetry best practices.

KNOWLEDGE BASE RULES:
{kb_context}

DETECTED PATTERN:
- Pattern: {pattern['pattern_name']} 
- Line {pattern['line_number']}: {pattern['matched_text']}
- Function: {pattern['function_name']}
- Detection Method: {pattern['detection_method']}
- Existing Description: {pattern['description']}

CODE CONTEXT:
{chr(10).join(f"{i}: {line}" for i, line in enumerate(pattern['context_lines'], pattern['line_number']-2))}

VALIDATION TASK:
1. Does this pattern violate a SPECIFIC rule mentioned in the KB above?
2. If YES, provide detailed violation analysis
3. If NO, respond with {{"has_violation": false}}

IMPORTANT: Only report violations that are explicitly supported by the KB rules above.

OUTPUT FORMAT (JSON only):
{{
  "has_violation": true/false,
  "rule_violated": "specific rule text from KB",
  "description": "why this specific code violates the rule", 
  "fix_suggestion": "precise fix for this code",
  "kb_reference": "which KB section",
  "confidence": 0.95
}}

Response:"""
        
        try:
            response = self.llm.invoke(prompt)
            result = json.loads(response.content.strip())
            
            if result.get("has_violation", False):
                location = CodeLocation(
                    line_number=pattern['line_number'],
                    column=pattern['column'],
                    function_name=pattern['function_name'],
                    code_snippet=pattern['matched_text'],
                    context_lines=pattern['context_lines']
                )
                
                return SpanViolation(
                    violation_id=f"SPAN_{pattern['pattern_name'].upper()}_{pattern['line_number']}",
                    severity=pattern['severity'],
                    file_path="current_file",
                    location=location,
                    violation_type=pattern['violation_type'],
                    rule_violated=result.get("rule_violated", pattern.get('kb_rule', 'Unknown rule')),
                    description=result.get("description", pattern['description']),
                    fix_suggestion=result.get("fix_suggestion", "Review code against OpenTelemetry best practices"),
                    kb_reference=result.get("kb_reference", "Knowledge base"),
                    confidence=result.get("confidence", pattern.get('confidence', 0.8)),
                    detection_method=pattern['detection_method']
                )
            
            return None
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ Pattern validation failed for {pattern['pattern_name']}: {e}")
            return None
    
    def _create_summary(self, violations: List[SpanViolation]) -> Dict[str, Any]:
        """Create violation summary with detection method breakdown"""
        
        summary = {
            "total_violations": len(violations),
            "by_severity": {},
            "by_type": {},
            "by_detection_method": {}
        }
        
        for violation in violations:
            # Count by severity
            severity = violation.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # Count by type
            vtype = violation.violation_type  
            summary["by_type"][vtype] = summary["by_type"].get(vtype, 0) + 1
            
            # Count by detection method
            method = violation.detection_method
            summary["by_detection_method"][method] = summary["by_detection_method"].get(method, 0) + 1
        
        return summary
    
    def refresh_learned_patterns(self):
        """Refresh patterns learned from KB (call when KB is updated)"""
        print("🔄 Refreshing patterns from updated knowledge base...")
        self.pattern_detector = SmartPatternDetector(self.vectorstore, self.llm)
        print("✅ Pattern refresh complete")

# Example usage
def demo_smart_hybrid_analyzer():
    """Demo the smart hybrid approach"""
    
    analyzer = SmartHybridSpanAnalyzer("./vector_store")
    
    # Sample code with violations
    sample_code = """
def validate_user(user_data):
    with tracer.start_span("validate_user") as span:  # Potential boundary violation
        if not user_data:
            span.record_exception(ValueError("No data"))
            raise ValueError("No user data")  # Error handling violation
        return True

def process_items(items):
    for item in items:  # Loop with spans - critical violation
        with tracer.start_span(f"process_item_{item.id}") as span:
            process_single_item(item)
"""
    
    print("🚀 Analyzing sample code with smart hybrid approach...\n")
    
    result = analyzer.analyze_spans(sample_code, "sample.py", "boundary violations")
    
    print(f"📊 Analysis Results:")
    print(f"• Total patterns detected: {result['total_patterns']}")
    print(f"• Violations found: {len(result['violations'])}")
    print(f"• KB sections used: {len(result['kb_sections_used'])}")
    
    print(f"\n🔍 Violation Details:")
    for violation in result['violations']:
        method_emoji = "🧠" if violation.detection_method == "learned_from_kb" else "🛡️"
        print(f"{method_emoji} Line {violation.location.line_number}: {violation.description}")
        print(f"   Detection: {violation.detection_method}")
        print(f"   Confidence: {violation.confidence:.1%}")
        print(f"   Fix: {violation.fix_suggestion}\n")

if __name__ == "__main__":
    demo_smart_hybrid_analyzer()