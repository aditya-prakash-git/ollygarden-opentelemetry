#!/usr/bin/env python3
"""
Test script to verify knowledge base processing
Run this to test the RAG pipeline setup
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from rag.pipeline import RAGPipeline

def main():
    # Load environment variables
    load_dotenv()
    
    print("🚀 Testing OpenTelemetry RAG Pipeline")
    print("=" * 50)
    
    # Initialize pipeline
    try:
        pipeline = RAGPipeline(
            kb_path="./knowledge_base",
            vector_store_path="./vector_store"
        )
        
        # Get initial stats
        stats = pipeline.get_stats()
        print(f"📊 Pipeline Stats: {stats}")
        
        # Initialize (this will build vector store)
        print("\n🔧 Initializing pipeline...")
        pipeline.initialize(force_rebuild=True)  # Force rebuild for testing
        
        # Test KB queries
        print("\n🔍 Testing Knowledge Base Queries...")
        
        test_queries = [
            "span creation rules",
            "error handling patterns",
            "naming conventions for spans",
            "what are anti-patterns",
            "metric naming best practices"
        ]
        
        for query in test_queries:
            print(f"\n❓ Query: {query}")
            results = pipeline.query_kb(query)
            print(f"   📝 Found {len(results)} relevant chunks")
            
            if results:
                # Show first result
                first = results[0]
                print(f"   🎯 Top result: {first['source']} ({first['type']})")
                print(f"   📄 Content preview: {first['content'][:150]}...")
        
        print("\n✅ Knowledge base processing test completed!")
        
        # Test interactive queries
        print("\n🤖 Testing Interactive Analysis...")
        
        interactive_queries = [
            "Tell me about OpenTelemetry span creation best practices",
            "What are common instrumentation anti-patterns?",
            "How should I name my OpenTelemetry metrics?"
        ]
        
        for query in interactive_queries:
            print(f"\n🗣️  Interactive Query: {query}")
            response = pipeline.interactive_analysis(query)
            print(f"🤖 Response:\n{response[:300]}...")
        
        print("\n🎉 All tests passed! RAG pipeline is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())