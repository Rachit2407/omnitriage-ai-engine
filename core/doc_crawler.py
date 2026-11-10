import os
import re
import urllib.parse
from typing import List, Dict, Any, Set, Optional
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

class DocumentationCrawler:
    """
    1-Click Documentation Crawler & Semantic Chunker.
    Takes a SaaS documentation URL (e.g. https://docs.stripe.com), crawls internal doc subpages,
    strips boilerplate (navbars, scripts, footers), chunks the text semantically,
    and returns chunks formatted for vector ingestion with citation source URLs.
    """
    def __init__(self, max_pages: int = 12, timeout: int = 8):
        self.max_pages = max_pages
        self.timeout = timeout
        self.headers = {
            "User-Agent": "OmniTriage-DocCrawler/2.4 (Enterprise Support Ingestion Bot; https://omnitriage-demo.streamlit.app)"
        }

    def crawl_and_chunk(
        self,
        start_url: str,
        tenant_id: str,
        chunk_words: int = 350,
        overlap_words: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Crawls documentation starting from start_url up to max_pages,
        extracts text, and yields semantic chunks tagged with tenant_id.
        """
        parsed_start = urllib.parse.urlparse(start_url)
        if not parsed_start.scheme or not parsed_start.netloc:
            start_url = "https://" + start_url
            parsed_start = urllib.parse.urlparse(start_url)

        base_domain = parsed_start.netloc
        base_path = parsed_start.path.rstrip('/')

        visited_urls: Set[str] = set()
        queue: List[str] = [start_url]
        pages_content: List[Dict[str, str]] = []

        while queue and len(visited_urls) < self.max_pages:
            batch = queue[:min(4, len(queue))]
            queue = queue[len(batch):]

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self._fetch_and_clean_page, url): url for url in batch if url not in visited_urls}
                for future in as_completed(futures):
                    url = futures[future]
                    visited_urls.add(url)
                    try:
                        page_data = future.result()
                        if page_data and page_data.get("text"):
                            pages_content.append(page_data)
                            # Discover more doc links
                            for link in page_data.get("links", []):
                                if link not in visited_urls and link not in queue and len(visited_urls) + len(queue) < self.max_pages:
                                    queue.append(link)
                    except Exception as e:
                        print(f"[DocCrawler] Error fetching {url}: {e}")

        # Chunk all collected pages
        all_chunks: List[Dict[str, Any]] = []
        for p_idx, page in enumerate(pages_content):
            chunks = self._chunk_text(
                text=page["text"],
                title=page["title"],
                source_url=page["url"],
                tenant_id=tenant_id,
                chunk_words=chunk_words,
                overlap_words=overlap_words,
                page_idx=p_idx
            )
            all_chunks.extend(chunks)

        return all_chunks

    def _fetch_and_clean_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetches a single page and extracts its title, clean body text, and internal links."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove navigation, scripts, styles, footers, headers
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg"]):
                tag.decompose()

            # Target main content area if available
            main_element = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"content|docs|documentation", re.I)) or soup.body
            if not main_element:
                return None

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            h1 = main_element.find("h1")
            if h1 and h1.text.strip():
                title = h1.text.strip()

            raw_text = main_element.get_text(separator="\n", strip=True)
            # Clean up whitespace
            cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text)

            # Discover internal documentation links
            internal_links = []
            parsed_current = urllib.parse.urlparse(url)
            for a_tag in main_element.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urllib.parse.urljoin(url, href)
                parsed_link = urllib.parse.urlparse(full_url)

                # Keep on the same domain and avoid anchors/assets
                if parsed_link.netloc == parsed_current.netloc:
                    if not any(parsed_link.path.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".pdf", ".zip", ".tar.gz"]):
                        clean_link = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                        if clean_link != url and clean_link not in internal_links:
                            internal_links.append(clean_link)

            return {
                "url": url,
                "title": title or url,
                "text": cleaned_text,
                "links": internal_links[:10]
            }
        except Exception:
            return None

    def _chunk_text(
        self,
        text: str,
        title: str,
        source_url: str,
        tenant_id: str,
        chunk_words: int,
        overlap_words: int,
        page_idx: int
    ) -> List[Dict[str, Any]]:
        words = text.split()
        if not words:
            return []

        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(words):
            end = min(start + chunk_words, len(words))
            chunk_slice = " ".join(words[start:end])
            chunk_id = f"{tenant_id}_p{page_idx}_c{chunk_idx}"

            chunks.append({
                "id": chunk_id,
                "tenant_id": tenant_id,
                "title": title,
                "source": source_url,
                "text": chunk_slice
            })
            chunk_idx += 1
            if end >= len(words):
                break
            start += (chunk_words - overlap_words)

        return chunks

# Global crawler instance
doc_crawler = DocumentationCrawler()
