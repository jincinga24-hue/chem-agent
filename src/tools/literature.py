"""Literature search via the arxiv Atom API. No API key required."""
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ARXIV_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def _ssl_ctx() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def arxiv_search(query: str, max_results: int = 5) -> dict:
    """Search arxiv by free-text query. Returns up to max_results papers.

    Each paper has: arxiv_id, title, authors, summary (first 500 chars),
    published_date, primary_category, url.
    """
    if max_results < 1 or max_results > 20:
        return {"error": "max_results must be between 1 and 20"}

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=15, context=_ssl_ctx()) as resp:
            xml_body = resp.read().decode("utf-8")
    except Exception as e:
        return {"error": f"arxiv request failed: {type(e).__name__}: {e}"}

    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as e:
        return {"error": f"arxiv response not parseable: {e}"}

    entries = root.findall("a:entry", ATOM_NS)
    papers = []
    for entry in entries:
        arxiv_id_elem = entry.find("a:id", ATOM_NS)
        title_elem = entry.find("a:title", ATOM_NS)
        summary_elem = entry.find("a:summary", ATOM_NS)
        published_elem = entry.find("a:published", ATOM_NS)
        category_elem = entry.find("{http://arxiv.org/schemas/atom}primary_category")

        authors = [
            (a.find("a:name", ATOM_NS).text or "").strip()
            for a in entry.findall("a:author", ATOM_NS)
            if a.find("a:name", ATOM_NS) is not None
        ]

        full_id = (arxiv_id_elem.text if arxiv_id_elem is not None else "").strip()
        short_id = full_id.rsplit("/", 1)[-1] if full_id else ""

        papers.append({
            "arxiv_id": short_id,
            "title": (title_elem.text or "").strip().replace("\n", " "),
            "authors": authors,
            "summary": (summary_elem.text or "").strip().replace("\n", " ")[:500],
            "published": (published_elem.text or "").strip() if published_elem is not None else "",
            "primary_category": category_elem.get("term") if category_elem is not None else "",
            "url": full_id,
        })

    return {"query": query, "count": len(papers), "papers": papers}
