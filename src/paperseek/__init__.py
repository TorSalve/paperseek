"""
PaperSeek - A unified interface for searching multiple academic databases.
"""

from .core.unified_client import UnifiedSearchClient
from .core.models import Paper, SearchResult, SearchFilters
from .core.config import AcademicSearchConfig
from .clients.crossref import CrossRefClient
from .clients.openalex import OpenAlexClient
from .clients.semantic_scholar import SemanticScholarClient
from .clients.doi import DOIClient
from .clients.pubmed import PubMedClient
from .clients.arxiv import ArXivClient
from .clients.core import COREClient
from .clients.unpaywall import UnpaywallClient
from .clients.dblp import DBLPClient
from .utils.pdf_downloader import PDFDownloader

__version__ = "0.1.0"
__all__ = [
    "UnifiedSearchClient",
    "Paper",
    "SearchResult",
    "SearchFilters",
    "AcademicSearchConfig",
    "CrossRefClient",
    "OpenAlexClient",
    "SemanticScholarClient",
    "DOIClient",
    "PubMedClient",
    "ArXivClient",
    "COREClient",
    "UnpaywallClient",
    "DBLPClient",
    "PDFDownloader",
]
