"""Database client implementations."""

from .crossref import CrossRefClient
from .openalex import OpenAlexClient
from .semantic_scholar import SemanticScholarClient
from .doi import DOIClient
from .pubmed import PubMedClient
from .arxiv import ArXivClient
from .core import COREClient
from .unpaywall import UnpaywallClient
from .dblp import DBLPClient

__all__ = [
    "CrossRefClient",
    "OpenAlexClient",
    "SemanticScholarClient",
    "DOIClient",
    "PubMedClient",
    "ArXivClient",
    "COREClient",
    "UnpaywallClient",
    "DBLPClient",
]
