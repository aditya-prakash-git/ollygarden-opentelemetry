# OpenTelemetry Instrumentation Validator

**AI-powered CLI tool to validate OpenTelemetry instrumentation across multiple languages using hybrid rule-based + LLM-driven techniques.**

---

## 🚀 Overview

The **OpenTelemetry Instrumentation Validator** ensures that telemetry spans and attributes follow best practices by combining:

- 🧠 **Rule-based detection** (regex + context)
- 🔎 **RAG-powered (Retrieval-Augmented Generation)** validation
- 🌐 **Multi-language support** (Go, Python, JS, Java, C#)
- 📘 **Knowledge-base grounding** using markdown rule files
---

## 📁 Project Structure

```
opentelemetry-validator/
|---test-files/
|    |--span_violation.py
|    |--test_otel_violations.go
|    |--test.go
|
├── knowledge_base/           # Expert-curated OpenTelemetry rules (markdown)
│   ├── instrumentation.md   # Core instrumentation principles
│   └── naming.md            # Naming convention rules
├── vector_store/            # ChromaDB embeddings database
│   └── chroma.sqlite3       # Vectorized knowledge base
├── src/
│   ├── rag/
│   │   ├── knowledge_processor.py  # KB → Vector store conversion
│   │   └── pipeline.py             # RAG orchestrator
│   └── llm/
│       └── otel_analyzer.py        # LLM-based validation (legacy)
├── multilang_analyzer.py     # Multi-language pattern detector
├── otel_cli.py              # Command-line interface
├── requirements.txt         # Dependencies
└── .env                     # Configuration (OpenAI API key)


```
I have added multiple test files such as test.go, test_otel_violations.go and span_violations.py


## 🔧 Key Enhancements

### ✅ 1. Multi-Language Analyzer (`multilang_analyzer.py`)

A major addition that enables span and attribute detection across:

- **Golang** (e.g., `tracer.Start(...)`, `ctx := context.With...`)
- **Python** (e.g., `with tracer.start_as_current_span(...)`)
- **JavaScript / Node**
- **Java**
- **C#**

Key functions:
- `find_patterns()` — Language detection and extraction
- `_extract_span_context()` — Detects parent-child span relationships and surrounding logic
- `_get_go_patterns()` — Maintains Go-specific span/meter patterns (easily extensible)

> This allows cross-language validation without separate pipelines.

---

### 📚 2. Deep Context-Based Prompting (RAG + LLM)

**Core pipeline:**
1. Patterns detected (e.g., malformed span name, missing attributes)
2. Query formed: `"span naming conventions opentelemetry go"`
3. Top 3 rule chunks fetched from `knowledge_base/` via ChromaDB
4. Prompt built with:
   - Span code context
   - Rule examples
   - Language and use-case (e.g., HTTP handler, DB call)
5. **GPT-4o-mini** evaluates if rule is violated
6. Returns **structured JSON** with:
   - Violation message
   - Line number
   - Fix recommendation
   - Severity score

> This drastically reduces hallucination and ensures responses are **grounded in real KB rules**.

---

### 🧪 3. Real-World Test Files

Several test files were introduced to validate pipeline accuracy:

#### 📄 `test.go`

- Language: **Golang**
- Contains: `17 known violations`
- Span patterns: incorrect naming, missing context, duplicate attributes
- Result:
  - Tool detected **all 17 violations**
  - Provided **line-accurate** fixes
  - Categorized by:
    - ❌ Missing span names
    - 🔁 Duplicate instrumentation
    - 🚫 Improper HTTP span kind
    - 🧱 Violation of naming conventions

> **Validation Proven:** MultiLang + RAG + LLM pipeline passed high-coverage test files with precision.

---

## ⚙️ CLI Examples

### Analyze a file
```bash
python otel_cli.py analyze "test.go" --focus "naming conventions"

```

### Scan a folder
```bash
python otel_cli.py scan ./checkout --patterns "*.go"
```

### Query best practices directly
```bash
python otel_cli.py ask "How should I name spans for database operations?"
```


# Dependencies

### OpenAI API
 ### — Embeddings + GPT-4o-mini

### ChromaDB
 ### — Vector search engine

### LangChain
 ### — RAG orchestration

### Python 3.8+




# 🛠️ Future Work

## Auto-fix mode with inline patching
## GitHub PR comments via bot
## Add support for Kotlin, Ruby, and Rust
## Self-healing validator (LLM suggests KB updates)