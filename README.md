# OpenTelemetry Instrumentation Validator

AI-powered tool that validates OpenTelemetry instrumentation against best practices using RAG (Retrieval-Augmented Generation).

---

## 🚀 Features

- ✅ **Knowledge Base Driven**: Uses markdown files containing OpenTelemetry best practices
- 🔍 **RAG Pipeline**: Retrieves relevant rules and provides grounded analysis
- 💻 **CLI Interface**: Easy-to-use command-line tool with multiple output formats
- 🛑 **Violation Detection**: Identifies instrumentation anti-patterns with confidence scoring
- 📁 **Repository Scanning**: Analyze single files or entire codebases
- 💬 **Interactive Queries**: Ask natural language questions about OpenTelemetry best practices

---

## ⚡ Quick Start

### ✅ Prerequisites

- Python 3.8+
- OpenAI API key

### 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aditya-prakash-git/ollygarden-opentelemetry.git
   cd ollygarden-opentelemetry
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. **Initialize the knowledge base**:
   ```bash
   python otel_cli.py init
   ```

---

## 🛠️ Usage

### 🔍 Analyze a single file
```bash
python otel_cli.py analyze your_file.py
```

### 🎯 Analyze with specific focus
```bash
python otel_cli.py analyze your_file.py -q "naming convention violations"
```

### 📁 Scan a directory
```bash
python otel_cli.py scan ./src --patterns "*.py" "*.go"
```

### 💬 Ask about best practices
```bash
python otel_cli.py ask "What are OpenTelemetry span creation anti-patterns?"
```

### ℹ️ Check tool status
```bash
python otel_cli.py status
```

---

## 📊 Example Output

```
╭─────────────────────── Summary ───────────────────────╮
│ Total Violations: 5                                   │
│ High: 3 Medium: 2                                     │
╰───────────────────────────────────────────────────────╯

╭─────────────────── Violation 1 ───────────────────────╮
│ HIGH: Creating span for internal function violates    │
│ boundary-only principle                               │
│ Location: checkout.py:45                              │
│ Fix: Remove span from validate_item() function        │
│ Reference: instrumentation.md - Span Creation Rules   │
│ Confidence: 90.0%                                     │
╰───────────────────────────────────────────────────────╯
```

---

## 🏗️ Architecture

The tool uses a RAG (Retrieval-Augmented Generation) approach:

1. **Knowledge Processing**: Extracts rules and patterns from markdown files
2. **Vector Store**: Creates embeddings for semantic search
3. **Code Analysis**: Retrieves relevant rules and analyzes code using LLM
4. **Violation Detection**: Provides structured output with fixes and confidence

---

## 📚 Knowledge Base

Includes expert-curated OpenTelemetry instrumentation rules on:

- ✅ Span creation rules and boundaries
- 🏷️ Naming conventions for spans and metrics
- ❌ Error handling patterns
- 🧩 Attribute usage guidelines
- 🚫 Anti-patterns to avoid

---

## 📁 Project Structure

```
ollygarden-opentelemetry/
├── src/
│   ├── rag/              # RAG pipeline components
│   ├── llm/              # LLM integration
│   └── cli/              # Command-line interface
├── knowledge_base/       # OpenTelemetry best practices (markdown)
├── vector_store/         # Generated embeddings
├── otel_cli.py           # Main CLI entry point
├── sample_checkout.py    # Example code with violations
└── test_otel_violations.py # Simple test cases
```

---


**Thank you for using OpenTelemetry Instrumentation Validator!** 🎉
