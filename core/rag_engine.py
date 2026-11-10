import os
import glob
from typing import List, Dict, Any

class RAGEngine:
    """
    RAG Engine with dual operating modes:
    1. Live ChromaDB vector store with OpenAI text-embedding-3-small when API key is provided.
    2. Zero-dependency lexical TF-IDF / keyword similarity fallback mode for offline/local development.
    """
    def __init__(self, collection_name: str = "saas_docs"):
        self.collection_name = collection_name
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.use_chroma = False
        self.documents: List[Dict[str, str]] = []
        
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                import chromadb
                from chromadb.utils import embedding_functions
                self.chroma_client = chromadb.Client()
                self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=self.api_key,
                    model_name="text-embedding-3-small"
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.openai_ef
                )
                self.use_chroma = True
            except Exception as e:
                print(f"[RAGEngine] ChromaDB initialization failed, falling back to lexical search: {e}")
                self.use_chroma = False

    def ingest_documents(self, docs: List[Dict[str, str]]):
        """Ingests list of {'id': str, 'text': str, 'source': str, 'title': str}"""
        self.documents.extend(docs)
        if self.use_chroma:
            ids = [d['id'] for d in docs]
            documents = [d['text'] for d in docs]
            metadatas = [{'source': d.get('source', 'docs'), 'title': d.get('title', '')} for d in docs]
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def load_local_knowledge_base(self, base_dir: str):
        """Loads all markdown documentation files from a local directory."""
        md_files = glob.glob(os.path.join(base_dir, "*.md"))
        docs = []
        for idx, file_path in enumerate(md_files):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            filename = os.path.basename(file_path)
            docs.append({
                "id": f"doc_{idx}_{filename}",
                "source": f"docs://{filename}",
                "title": filename.replace(".md", "").replace("_", " ").title(),
                "text": content
            })
        self.ingest_documents(docs)
        return len(docs)

    def retrieve_context(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieves top-k relevant document chunks for the ticket query."""
        if self.use_chroma:
            results = self.collection.query(query_texts=[query], n_results=min(top_k, len(self.documents)))
            retrieved = []
            if results and 'documents' in results and results['documents']:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    retrieved.append({
                        "content": doc,
                        "source": meta.get("source", "docs"),
                        "title": meta.get("title", "Documentation")
                    })
            return retrieved
        
        # High-precision keyword matching fallback (Offline/Dev mode)
        query_words = set(query.lower().split())
        scored_docs = []
        for doc in self.documents:
            text_lower = doc['text'].lower()
            score = sum(1 for word in query_words if word in text_lower and len(word) > 3)
            scored_docs.append((score, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        retrieved = []
        for score, doc in scored_docs[:top_k]:
            retrieved.append({
                "content": doc['text'],
                "source": doc.get('source', 'docs'),
                "title": doc.get('title', 'Documentation')
            })
        return retrieved
