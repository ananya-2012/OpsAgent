"""Company memory system with BM25 retrieval + persistent facts.
Loads company context documents and provides relevant information to the agent."""
import os
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from opsagent.config import COMPANY_CONTEXT_DIR


class CompanyMemory:
    """BM25-based retrieval over company context documents + persistent facts."""

    def __init__(self, context_dir: str | Path = None):
        self.context_dir = Path(context_dir) if context_dir else COMPANY_CONTEXT_DIR
        self.documents: list[dict] = []  # {path, title, content, chunks}
        self.chunks: list[str] = []
        self.chunk_sources: list[dict] = []
        self.bm25 = None
        self._load_documents()

    def _load_documents(self):
        """Load all markdown files from company context directory."""
        if not self.context_dir.exists():
            return

        for filepath in sorted(self.context_dir.glob("*.md")):
            content = filepath.read_text(encoding='utf-8')
            title = filepath.stem.replace('_', ' ').title()

            # Extract title from first heading if present
            first_line = content.strip().split('\n')[0]
            if first_line.startswith('#'):
                title = first_line.lstrip('#').strip()

            doc = {
                "path": str(filepath),
                "title": title,
                "content": content,
            }
            self.documents.append(doc)

            # Chunk by sections
            sections = self._split_into_sections(content)
            for section in sections:
                self.chunks.append(section)
                self.chunk_sources.append({
                    "path": str(filepath),
                    "title": title,
                })

        if self.chunks:
            tokenized = [self._tokenize(c) for c in self.chunks]
            self.bm25 = BM25Okapi(tokenized)

    def _split_into_sections(self, content: str) -> list[str]:
        """Split markdown content into sections for better retrieval."""
        sections = []
        current = []

        for line in content.split('\n'):
            if line.startswith('#') and current:
                sections.append('\n'.join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            sections.append('\n'.join(current))

        # Don't return empty sections
        return [s.strip() for s in sections if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        # Remove very common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'and', 'or', 'but',
                     'not', 'no', 'if', 'then', 'else', 'this', 'that', 'it'}
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search company context for relevant information."""
        if not self.bm25 or not self.chunks:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)),
                           key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "content": self.chunks[idx],
                    "source": self.chunk_sources[idx],
                    "score": float(scores[idx]),
                })
        return results

    def get_all_context(self) -> str:
        """Get all company context as a single string (for initial prompt)."""
        parts = []
        for doc in self.documents:
            parts.append(f"=== {doc['title']} ===\n{doc['content']}")
        return "\n\n".join(parts)

    def get_relevant_context(self, task_description: str) -> str:
        """Get relevant context for a specific task."""
        results = self.search(task_description, top_k=5)
        if not results:
            return self.get_all_context()

        parts = []
        seen = set()
        for r in results:
            key = r['content'][:100]
            if key not in seen:
                seen.add(key)
                parts.append(f"[From: {r['source']['title']}]\n{r['content']}")
        return "\n\n".join(parts)
