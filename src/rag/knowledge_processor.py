"""
Knowledge Base Processing for RAG Pipeline
Chunks KB markdown and creates embeddings - Fixed for Windows encoding
"""

from typing import List, Dict, Any
from langchain_community.document_loaders import DirectoryLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import re
from pathlib import Path

class UTF8TextLoader:
    """Custom text loader that forces UTF-8 encoding"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self):
        """Load text with UTF-8 encoding"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to other encodings
            encodings = ['utf-8', 'cp1252', 'iso-8859-1', 'latin-1']
            content = None
            for encoding in encodings:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    print(f"Successfully loaded {self.file_path} with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise UnicodeDecodeError(f"Could not decode {self.file_path} with any encoding")
        
        # Return Document-like object
        return [{
            'page_content': content,
            'metadata': {'source': self.file_path}
        }]

class KnowledgeProcessor:
    def __init__(self, kb_path: str, vector_store_path: str):
        self.kb_path = kb_path
        self.vector_store_path = vector_store_path
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"  # Cheaper and faster with 1536 dimensional embeddings
        )
        
    def load_and_chunk_kb(self) -> List[Dict[str, Any]]:
        """Load KB files and chunk into semantic sections"""
        
        # Load markdown files manually with UTF-8 encoding
        documents = []
        kb_path = Path(self.kb_path)
        
        for md_file in kb_path.glob("*.md"):
            print(f"Loading {md_file.name}...")
            loader = UTF8TextLoader(str(md_file))
            file_docs = loader.load()
            
            for doc in file_docs:
                documents.append({
                    'page_content': doc['page_content'],
                    'metadata': doc['metadata']
                })
        
        print(f"Loaded {len(documents)} documents")
        
        chunks = []
        for doc in documents:
            # Extract rules and examples with context
            doc_chunks = self._extract_semantic_chunks(doc['page_content'], doc['metadata'])
            chunks.extend(doc_chunks)
            
        return chunks
    
    def _extract_semantic_chunks(self, content: str, metadata: Dict) -> List[Dict]:
        """Extract rules, examples, and anti-patterns as semantic chunks"""
        chunks = []
        
        # Pattern for extracting structured rules
        patterns = {
            "good_pattern": r"✅.*?(?=\n|$)",
            "bad_pattern": r"❌.*?(?=\n|$)", 
            "rule": r"(?:### |#### )(.+?)\n(.*?)(?=\n### |\n#### |\n## |$)",
            "example": r"```.*?```",
            "anti_pattern": r"Anti-Pattern.*?(?=\n## |\n### |$)"
        }
        
        for pattern_type, pattern in patterns.items():
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            for match in matches:
                chunk_text = match if isinstance(match, str) else " ".join(match)
                chunks.append({
                    "content": chunk_text.strip(),
                    "type": pattern_type,
                    "source": metadata.get("source", "unknown"),
                    "metadata": metadata
                })
        
        # Also add general text chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]
        )
        
        text_chunks = splitter.split_text(content)
        for chunk in text_chunks:
            if chunk.strip():  # Only add non-empty chunks
                chunks.append({
                    "content": chunk.strip(),
                    "type": "text_chunk",
                    "source": metadata.get("source", "unknown"),
                    "metadata": metadata
                })
        
        return chunks
    
    def build_vector_store(self, chunks: List[Dict]) -> Chroma:
        """Build vector store from chunks"""
        
        # Prepare documents for embedding
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [
            {
                "type": chunk["type"],
                "source": chunk["source"],
                **chunk["metadata"]
            } 
            for chunk in chunks
        ]
        
        print(f"Creating embeddings for {len(texts)} chunks...")
        
        # Create vector store
        vectorstore = Chroma.from_texts(
            texts=texts,
            metadatas=metadatas,
            embedding=self.embeddings,
            persist_directory=self.vector_store_path
        )
        
        vectorstore.persist()
        return vectorstore