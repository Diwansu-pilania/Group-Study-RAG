"""
Run this once to ingest your knowledge base into ChromaDB.
Usage: python ingest_kb.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.services.rag_service import ingest_file

KB_DIR = "./data/knowledge_base"

def main():
    print("📚 Ingesting knowledge base into ChromaDB...")
    files = [f for f in os.listdir(KB_DIR)
             if f.endswith((".md", ".txt"))]

    if not files:
        print("⚠️  No .md or .txt files found in data/knowledge_base/")
        return

    for filename in files:
        path = os.path.join(KB_DIR, filename)
        ingest_file(path)

    print(f"\n✅ Done! Ingested {len(files)} file(s) into ChromaDB.")
    print("   Vector store ready at: ./rag/vectorstore/chroma_db")

if __name__ == "__main__":
    main()
