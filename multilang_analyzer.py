"""
AST + MULTI LANG SUPPORT, Hi Juraci, here I tried to solve some challenges and shortcomings from previous version.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from pydantic import BaseModel
import json
from dataclasses import dataclass

@dataclass
class CodeLocation:
    line_number: int
    column: int
    function_name: str
    code_snippet: str
    context_lines: List[str]

@dataclass 
class TelemetryViolation:
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
    detection_method: str
    language: str

class MultiLanguagePatternDetector:
    """Enhanced detector with better context extraction and deduplication"""
    
    def __init__(self, vectorstore: Chroma, llm: ChatOpenAI):
        self.vectorstore = vectorstore
        self.llm = llm
        
        # Track processed patterns to avoid duplicates
        self.processed_patterns = set()
        
        # Language-specific patterns for OpenTelemetry
        self.language_patterns = {
            "go": self._get_go_patterns(),
            "python": self._get_python_patterns(), 
            "javascript": self._get_javascript_patterns(),
            "typescript": self._get_typescript_patterns(),
            "java": self._get_java_patterns(),
            "csharp": self._get_csharp_patterns()
        }
        
        print(f"Multi-language analyzer ready for {len(self.language_patterns)} languages")
    
    def _detect_language(self, file_path: str, code: str) -> str:
        """Auto-detect programming language from file extension and code patterns"""
        
        file_ext = Path(file_path).suffix.lower()
        
        # File extension mapping
        ext_map = {
            ".go": "go",
            ".py": "python", 
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cs": "csharp",
            ".kt": "java",  # Kotlin uses similar patterns
            ".scala": "java"  # Scala uses similar JVM patterns
        }
        
        if file_ext in ext_map:
            return ext_map[file_ext]
        
        # Fallback: detect from code patterns
        if "package main" in code or "import (" in code:
            return "go"
        elif "def " in code and "import " in code:
            return "python"
        elif "function " in code or "const " in code:
            return "javascript" 
        elif "class " in code and "public " in code:
            return "java"
        
        return "unknown"
    
    def _get_go_patterns(self) -> Dict[str, Dict]:
        """Enhanced OpenTelemetry patterns for Go"""
        return {
            # Span creation patterns
            "tracer_start_span": {
                "regex": r'tracer\.Start\s*\(\s*\w+\s*,\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "Go tracer.Start() span creation",
                "extract_name": 1
            },
            "tracer_start_with_options": {
                "regex": r'tracer\.Start\s*\(\s*\w+\s*,\s*["\']([^"\']+)["\'].*trace\.WithSpanKind',
                "violation_type": "span_naming",
                "description": "Go tracer.Start() with span options",
                "extract_name": 1
            },
            
            # Metric patterns
            "meter_counter": {
                "regex": r'\.NewCounter\s*\([^,]*,\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming",
                "description": "Go meter counter creation",
                "extract_name": 1
            },
            "meter_histogram": {
                "regex": r'\.NewHistogram\s*\([^,]*,\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming", 
                "description": "Go meter histogram creation",
                "extract_name": 1
            },
            
            # Attribute patterns - more specific to avoid false positives
            "span_set_attributes": {
                "regex": r'span\.SetAttributes\s*\([^)]*attribute\.\w+\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "attribute_naming",
                "description": "Go span.SetAttributes() usage",
                "extract_name": 1
            },
            "attribute_string": {
                "regex": r'attribute\.String\s*\(\s*["\']([^"\']+)["\'][^)]*\)',
                "violation_type": "attribute_naming",
                "description": "Go attribute.String() usage",
                "extract_name": 1
            },
            "attribute_int": {
                "regex": r'attribute\.Int\d*\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "attribute_naming",
                "description": "Go attribute.Int() usage",
                "extract_name": 1
            },
            "attribute_float": {
                "regex": r'attribute\.Float\d*\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "attribute_naming",
                "description": "Go attribute.Float() usage",
                "extract_name": 1
            },
            "attribute_bool": {
                "regex": r'attribute\.Bool\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "attribute_naming",
                "description": "Go attribute.Bool() usage",
                "extract_name": 1
            },
            
            # Span event patterns
            "span_add_event": {
                "regex": r'span\.AddEvent\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "event_naming",
                "description": "Go span.AddEvent() usage",
                "extract_name": 1
            },
            
            # Producer span patterns (for Kafka/messaging)
            "producer_span": {
                "regex": r'tracer\.Start\s*\([^,]+,\s*fmt\.Sprintf\s*\(\s*["\']([^"\']*%s[^"\']*)["\']',
                "violation_type": "span_naming",
                "description": "Go messaging producer span with format string",
                "extract_name": 1
            }
        }
    
    def _get_python_patterns(self) -> Dict[str, Dict]:
        """OpenTelemetry patterns for Python"""
        return {
            "tracer_start_span": {
                "regex": r'tracer\.start_span\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "Python tracer.start_span() usage",
                "extract_name": 1
            },
            "with_tracer_span": {
                "regex": r'with\s+tracer\.start_span\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "Python with tracer.start_span() context manager",
                "extract_name": 1
            },
            "start_as_current_span": {
                "regex": r'\.start_as_current_span\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "Python start_as_current_span() usage",
                "extract_name": 1
            },
            "create_counter": {
                "regex": r'\.create_counter\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming",
                "description": "Python create_counter() usage",
                "extract_name": 1
            },
            "create_histogram": {
                "regex": r'\.create_histogram\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming",
                "description": "Python create_histogram() usage", 
                "extract_name": 1
            }
        }
    
    def _get_javascript_patterns(self) -> Dict[str, Dict]:
        """OpenTelemetry patterns for JavaScript/Node.js"""
        return {
            "tracer_start_span": {
                "regex": r'tracer\.startSpan\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "JavaScript tracer.startSpan() usage",
                "extract_name": 1
            },
            "start_active_span": {
                "regex": r'\.startActiveSpan\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "JavaScript startActiveSpan() usage", 
                "extract_name": 1
            },
            "create_counter": {
                "regex": r'\.createCounter\s*\(\s*{\s*name:\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming",
                "description": "JavaScript createCounter() usage",
                "extract_name": 1
            }
        }
    
    def _get_typescript_patterns(self) -> Dict[str, Dict]:
        """OpenTelemetry patterns for TypeScript (extends JavaScript)"""
        return self._get_javascript_patterns()
    
    def _get_java_patterns(self) -> Dict[str, Dict]:
        """OpenTelemetry patterns for Java"""
        return {
            "tracer_span_builder": {
                "regex": r'tracer\.spanBuilder\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "Java tracer.spanBuilder() usage",
                "extract_name": 1
            },
            "span_builder_start": {
                "regex": r'\.spanBuilder\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming", 
                "description": "Java spanBuilder() usage",
                "extract_name": 1
            },
            "counter_builder": {
                "regex": r'\.counterBuilder\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming",
                "description": "Java counterBuilder() usage",
                "extract_name": 1
            }
        }
    
    def _get_csharp_patterns(self) -> Dict[str, Dict]:
        """OpenTelemetry patterns for C#"""
        return {
            "activity_source_start": {
                "regex": r'activitySource\.StartActivity\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "span_naming",
                "description": "C# ActivitySource.StartActivity() usage",
                "extract_name": 1
            },
            "create_counter": {
                "regex": r'\.CreateCounter<[^>]+>\s*\(\s*["\']([^"\']+)["\']',
                "violation_type": "metric_naming",
                "description": "C# CreateCounter<T>() usage",
                "extract_name": 1
            }
        }
    
    def _extract_span_context(self, lines: List[str], line_num: int, language: str) -> Dict[str, Any]:
        """Extract additional context around telemetry usage for better validation"""
        
        # Get the line with telemetry call
        if line_num <= 0 or line_num > len(lines):
            return {"type": "unknown", "hints": [], "surrounding_code": ""}
        
        target_line = lines[line_num - 1]
        
        # Get surrounding lines for context
        start_idx = max(0, line_num - 5)
        end_idx = min(len(lines), line_num + 3)
        surrounding_lines = lines[start_idx:end_idx]
        surrounding_code = "\n".join(surrounding_lines)
        
        context = {
            "type": "unknown", 
            "hints": [],
            "surrounding_code": surrounding_code,
            "is_http_handler": False,
            "is_database_op": False,
            "is_messaging": False
        }
        
        # Analyze surrounding code for context clues
        context_text = surrounding_code.lower()
        
        # HTTP handler detection
        http_indicators = [
            r'http\.handler', r'gin\.context', r'router\.', r'handler\s*func',
            r'http\.request', r'http\.response', r'\.method\s*==', r'req\.', r'resp\.',
            r'get\s*/|post\s*/|put\s*/|delete\s*/', r'endpoint', r'api'
        ]
        
        for pattern in http_indicators:
            if re.search(pattern, context_text):
                context["type"] = "http"
                context["is_http_handler"] = True
                context["hints"].append("HTTP span should follow 'METHOD /path' format")
                break
        
        
        db_indicators = [
            r'sql\.|db\.|database', r'query|select|insert|update|delete',
            r'prepare|execute|scan', r'rows\.|tx\.|conn\.', r'gorm\.',
            r'mongo|redis|postgres|mysql'
        ]
        
        for pattern in db_indicators:
            if re.search(pattern, context_text):
                context["type"] = "database"
                context["is_database_op"] = True
                context["hints"].append("Database span should follow 'OPERATION table' format")
                break
        
        # Messaging detection  
        messaging_indicators = [
            r'kafka|rabbitmq|pubsub|message|producer|consumer',
            r'publish|subscribe|send|receive', r'topic|queue|exchange'
        ]
        
        for pattern in messaging_indicators:
            if re.search(pattern, context_text):
                context["type"] = "messaging"
                context["is_messaging"] = True
                context["hints"].append("Messaging span should follow 'send/receive destination' format")
                break
        
        return context
    
    def find_patterns(self, code: str, file_path: str) -> List[Dict]:
        """Find OpenTelemetry patterns with enhanced context extraction"""
        
        # Reset processed patterns for new file
        self.processed_patterns.clear()
        
        # LANGUAGE DETECTION , SO WE CAN ALSO DETECT JS, TS , GO AND PY
        language = self._detect_language(file_path, code)
        
        if language == "unknown" or language not in self.language_patterns:
            print(f"Unsupported language detected for {file_path}")
            return []
        
        print(f"Analyzing {language.upper()} code ({len(code.split('\n'))} lines)")
        
        patterns = self.language_patterns[language]
        detected_patterns = []
        lines = code.split('\n')
        
        for pattern_name, pattern_info in patterns.items():
            try:
                regex = pattern_info["regex"]
                matches = list(re.finditer(regex, code, re.MULTILINE | re.IGNORECASE))
                
                for match in matches:
                    # GET TOTAL NUMBER OF LINES
                    line_num = code[:match.start()].count('\n') + 1
                    
                    # Create unique identifier 
                    pattern_id = f"{file_path}:{line_num}:{match.start()}"
                    if pattern_id in self.processed_patterns:
                        continue
                    self.processed_patterns.add(pattern_id)
                    
                    # Extract the name if pattern specifies
                    extracted_name = ""
                    if "extract_name" in pattern_info:
                        name_group = pattern_info["extract_name"]
                        if len(match.groups()) >= name_group:
                            extracted_name = match.group(name_group)
                    
                    # Get context lines
                    start_context = max(0, line_num - 3)
                    end_context = min(len(lines), line_num + 2)
                    context_lines = lines[start_context:end_context]
                    
                    # Extract enhanced context
                    span_context = self._extract_span_context(lines, line_num, language)
                    
                    detected_patterns.append({
                        "pattern_name": pattern_name,
                        "line_number": line_num,
                        "column": match.start() - code.rfind('\n', 0, match.start()),
                        "matched_text": match.group(0),
                        "extracted_name": extracted_name,
                        "violation_type": pattern_info["violation_type"],
                        "severity": "medium",
                        "description": pattern_info["description"],
                        "context_lines": context_lines,
                        "function_name": self._get_function_name(lines, line_num - 1, language),
                        "detection_method": "multi_language_pattern",
                        "language": language,
                        "confidence": 0.85,
                        "span_context": span_context  # Enhanced context
                    })
                    
            except re.error as e:
                print(f"Regex error in pattern '{pattern_name}': {e}")
                continue
        
        print(f"Found {len(detected_patterns)} telemetry patterns")
        return detected_patterns
    
    def _get_function_name(self, lines: List[str], current_line: int, language: str) -> str:
        """Find function name containing current line, language-aware"""
        
        function_patterns = {
            "go": r'func\s+(\w+)',
            "python": r'def\s+(\w+)',
            "javascript": r'(?:function\s+(\w+)|const\s+(\w+)\s*=|(\w+)\s*:\s*function)',
            "typescript": r'(?:function\s+(\w+)|const\s+(\w+)\s*=|(\w+)\s*:\s*function)',
            "java": r'(?:public|private|protected)?\s*\w*\s*(\w+)\s*\(',
            "csharp": r'(?:public|private|protected)?\s*\w*\s*(\w+)\s*\('
        }
        
        pattern = function_patterns.get(language, r'(\w+)\s*\(')
        
        for i in range(current_line, max(0, current_line - 20), -1):
            if i < len(lines):
                match = re.search(pattern, lines[i])
                if match:
                    # Return first non-empty group
                    for group in match.groups():
                        if group:
                            return group
        return "global"

class MultiLanguageOTelAnalyzer:
    """Multi-language OpenTelemetry analyzer with enhanced validation"""
    
    def __init__(self, vector_store_path: str):
        self.vector_store_path = vector_store_path
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=2000
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = self._load_vector_store()
        
        # USING ENHANCED PATTERN DETECTION
        self.pattern_detector = MultiLanguagePatternDetector(self.vectorstore, self.llm)
    
    def _load_vector_store(self) -> Chroma:
        if not os.path.exists(self.vector_store_path):
            raise ValueError(f"Vector store not found at {self.vector_store_path}")
        
        return Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )
    
    def analyze_telemetry_patterns(self, code: str, file_path: str, query: str = None) -> Dict[str, Any]:
        """Analyze telemetry patterns with enhanced context-aware validation"""
        
        print(f"Starting multi-language analysis for {Path(file_path).name}")
        
        # Step 1:DETECT PATTERNS
        detected_patterns = self.pattern_detector.find_patterns(code, file_path)
        
        if not detected_patterns:
            return {
                "file_path": file_path,
                "language": self.pattern_detector._detect_language(file_path, code),
                "total_patterns": 0,
                "violations": [],
                "summary": {"total_violations": 0},
                "kb_sections_used": []
            }
        
        # Step 2: validate NAMING CONVENTION USING RAG
        print(f"Validating {len(detected_patterns)} patterns against naming conventions...")
        violations = []
        kb_docs_used = []
        
        for pattern in detected_patterns:
           
            kb_query = f"{pattern['violation_type']} naming conventions OpenTelemetry {pattern['language']}"
            relevant_docs = self.vectorstore.similarity_search(kb_query, k=3)
            kb_docs_used.extend(relevant_docs)
            
            # DEBUG STEP
            print(f"DEBUG: KB query: {kb_query}")
            for doc in relevant_docs:
                print(f"Retrieved rule: {doc.page_content[:100]}...")
            
            # VALIDATE NAMING CONVENTION WITH ACTUAL KB
            violation = self._validate_naming_convention(pattern, relevant_docs)
            if violation and violation.confidence > 0.7:
                violations.append(violation)
        
        return {
            "file_path": file_path,
            "language": detected_patterns[0]["language"] if detected_patterns else "unknown",
            "total_patterns": len(detected_patterns),
            "violations": violations,
            "summary": self._create_summary(violations),
            "kb_sections_used": list(set([doc.metadata.get("source", "unknown") for doc in kb_docs_used]))
        }
    
    def _validate_naming_convention(self, pattern: Dict, kb_docs: List[Document]) -> Optional[TelemetryViolation]:
        """Enhanced validation with context-aware rules and better prompting"""
        
        # BUILDING KB CONTEXT FROM ACTUAL KB
        kb_context = "\n\n".join([
            f"KB Source: {doc.metadata.get('source', 'unknown')}\n"
            f"Rule: {doc.page_content[:400]}"
            for doc in kb_docs
        ])
        
        extracted_name = pattern.get("extracted_name", "")
        violation_type = pattern['violation_type']
        span_context = pattern.get('span_context', {})
        
        # CONTEXT AWARE RULES
        if violation_type == "span_naming":
            validation_rules = """
SPAN NAMING RULES FROM KNOWLEDGE BASE:
- Span names MUST follow "{verb} {object}" pattern (e.g., "GET /users", "SELECT orders")
- NEVER use camelCase (e.g., "getUserData" is WRONG)
- NEVER use snake_case (e.g., "get_user_data" is WRONG)
- HTTP spans: "{method} {route}" with route templates like "/users/{id}" are CORRECT
- Database spans: "{operation} {table}" (e.g., "SELECT users")
- Route templates with path parameters like "/users/{id}" are VALID for HTTP spans
- Messaging spans: "send/receive destination"

CORRECT EXAMPLES:
- "GET /users/{id}" - HTTP route template (CORRECT)
- "POST /checkout" - HTTP endpoint (CORRECT)
- "SELECT users" - Database operation (CORRECT)
- "send orders" - Messaging (CORRECT)

INCORRECT EXAMPLES:
- "getUserData" - camelCase (WRONG)
- "get_user_data" - snake_case (WRONG)
- "processUserData" - camelCase (WRONG)
"""
            
            #  HERE WE CAN ADD SOME CONTEXT SPECIFIC HINTS, SO IT CAN BASICALLY POINT TO OUR KB
            if span_context.get('is_http_handler'):
                validation_rules += "\nCONTEXT: This appears to be an HTTP handler - span should follow HTTP naming conventions."
            elif span_context.get('is_database_op'):
                validation_rules += "\nCONTEXT: This appears to be a database operation - span should follow database naming conventions."
            elif span_context.get('is_messaging'):
                validation_rules += "\nCONTEXT: This appears to be messaging code - span should follow messaging naming conventions."
                
        elif violation_type == "attribute_naming":
            validation_rules = """
ATTRIBUTE NAMING RULES FROM KNOWLEDGE BASE:
- Use lowercase with dots for hierarchy (e.g., "http.method", "user.id")
- Standard namespaces: http.*, db.*, messaging.*, app.*, service.*
- CORRECT: "app.user.id", "http.status_code", "messaging.kafka.producer.success"
- These are VALID attribute names from semantic conventions
- Avoid uppercase letters in attribute names

CORRECT EXAMPLES:
- "user.id" - Simple attribute (CORRECT)
- "http.method" - Standard semantic convention (CORRECT)
- "messaging.kafka.producer.success" - Messaging attribute (CORRECT)
- "app.order.total" - Application-specific (CORRECT)

INCORRECT EXAMPLES:
- "MyServiceName.user" - Contains uppercase (WRONG)
- "HTTPMethod" - All uppercase (WRONG)
"""     
        elif violation_type == "event_naming":
            validation_rules = """
EVENT NAMING RULES FROM KNOWLEDGE BASE:
- Business milestone events should be simple and descriptive
- CORRECT: "charged", "shipped", "prepared", "order.placed"
- CORRECT: "error" for exception events
- These represent critical business milestones that need positive confirmation

CORRECT EXAMPLES:
- "charged" - Payment processed (CORRECT)
- "shipped" - Order shipped (CORRECT)  
- "prepared" - Order prepared (CORRECT)
- "error" - Exception occurred (CORRECT)

Only flag events that are unclear or meaningless without context.
"""

        elif violation_type == "metric_naming":
            validation_rules = """
METRIC NAMING RULES FROM KNOWLEDGE BASE:
- Follow "{domain}.{component}.{property}" pattern
- NEVER include service name (e.g., "myservice.http.duration" is WRONG)
- CORRECT: "http.server.request.duration", "db.client.operation.duration"
- App-specific metrics: "app.*" namespace is acceptable for application metrics

CORRECT EXAMPLES:
- "http.server.request.duration" - Standard HTTP metric (CORRECT)
- "db.client.operation.duration" - Database metric (CORRECT)
- "app.order.items.count" - Application-specific (CORRECT)

INCORRECT EXAMPLES:
- "myservice.http.duration" - Contains service name (WRONG)
- "checkoutservice.orders.count" - Contains service name (WRONG)
"""
        else:
            validation_rules = "Use general OpenTelemetry naming conventions."
        
        prompt = f"""
You are validating OpenTelemetry naming conventions using ONLY the provided knowledge base rules.

{validation_rules}

KNOWLEDGE BASE CONTEXT:
{kb_context}

TELEMETRY ELEMENT TO VALIDATE:
- Type: {violation_type}
- Name: "{extracted_name}"
- Language: {pattern['language']}
- Code: {pattern['matched_text']}
- Context: {span_context.get('type', 'unknown')}

VALIDATION TASK:
Check if "{extracted_name}" violates the rules above. Be STRICT about following KB rules but AVOID false positives.

CRITICAL RULES:
- Route templates like "GET /users/{{id}}" are CORRECT for HTTP spans
- Standard semantic conventions are CORRECT
- Only flag clear violations of the naming patterns above

Respond with VALID JSON only:
{{"has_violation": true, "rule_violated": "specific rule from KB", "description": "exact issue", "fix_suggestion": "correct format", "confidence": 0.9}}

OR if no violation:
{{"has_violation": false}}

JSON Response:"""
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()
            
            
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
          
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                return None
            
            # Only create violations for high confidence, clear issues
            if result.get("has_violation", False) and result.get("confidence", 0) >= 0.8:
                location = CodeLocation(
                    line_number=pattern['line_number'],
                    column=pattern['column'], 
                    function_name=pattern['function_name'],
                    code_snippet=pattern['matched_text'],
                    context_lines=pattern['context_lines']
                )
                
                return TelemetryViolation(
                    violation_id=f"{pattern['violation_type'].upper()}_{pattern['line_number']}",
                    severity="high" if result.get("confidence", 0) > 0.9 else "medium",
                    file_path="current_file",
                    location=location,
                    violation_type=pattern['violation_type'],
                    rule_violated=result.get("rule_violated", "Naming convention violation"),
                    description=result.get("description", f"Naming issue in {extracted_name}"),
                    fix_suggestion=result.get("fix_suggestion", "Follow OpenTelemetry naming conventions"),
                    kb_reference=result.get("kb_reference", "Knowledge base rules"),
                    confidence=result.get("confidence", 0.8),
                    detection_method="rag_validated_enhanced",
                    language=pattern['language']
                )
            
            return None
            
        except Exception as e:
            print(f"Validation error: {e}")
            return None

    def _create_summary(self, violations: List[TelemetryViolation]) -> Dict[str, Any]:
        """Create violation summary"""
        
        summary = {
            "total_violations": len(violations),
            "by_severity": {},
            "by_type": {},
            "by_language": {}
        }
        
        for violation in violations:
            # Count by severity
            severity = violation.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # Count by type
            vtype = violation.violation_type
            summary["by_type"][vtype] = summary["by_type"].get(vtype, 0) + 1
            
            # Count by language
            lang = violation.language
            summary["by_language"][lang] = summary["by_language"].get(lang, 0) + 1
        
        return summary

# Maintain compatibility
SmartHybridSpanAnalyzer = MultiLanguageOTelAnalyzer