# Architecture

This document describes the internal architecture of Academic Search Unified.

## Overview

The package is designed with modularity and extensibility in mind, following object-oriented principles and clean architecture patterns.

## Package Structure

```
src/academic_search_unified/
├── __init__.py                 # Package exports
├── core/                       # Core functionality
│   ├── base.py                # Base client interface
│   ├── exceptions.py          # Custom exceptions
│   ├── models.py              # Pydantic data models
│   └── unified_client.py      # Main unified client
├── clients/                    # Database clients
│   ├── crossref.py
│   ├── openalex.py
│   ├── semantic_scholar.py
│   ├── doi.py
│   ├── pubmed.py
│   ├── arxiv.py
│   ├── core.py
│   ├── unpaywall.py
│   └── dblp.py
├── utils/                      # Utilities
│   ├── config.py              # Configuration management
│   ├── rate_limiter.py        # Rate limiting
│   └── pdf_downloader.py      # PDF downloading
└── config/                     # Default configuration
    └── databases.yaml         # Database defaults
```

## Core Components

### Base Client (`DatabaseClient`)

Abstract base class that defines the interface all database clients must implement:

```python
class DatabaseClient(ABC):
    @abstractmethod
    def search(self, filters: SearchFilters) -> SearchResult:
        """Search the database."""
        pass
    
    @abstractmethod
    def lookup_doi(self, doi: str) -> Optional[Paper]:
        """Look up a paper by DOI."""
        pass
```

Key features:
- Rate limiting integration
- Retry logic with exponential backoff
- Consistent error handling
- HTTP session management

### Data Models (`models.py`)

Pydantic models ensure type safety and validation:

- **`Paper`**: Normalized paper metadata with 20+ fields
- **`Author`**: Author information with optional ORCID
- **`SearchResult`**: Collection of papers with metadata
- **`SearchFilters`**: Query parameters and constraints

Benefits:
- Automatic validation
- Type hints for IDE support
- Easy serialization/deserialization
- Immutable by default (with frozen authors)

### Unified Client (`UnifiedSearchClient`)

Orchestrates searches across multiple databases:

1. **Initialization**: Loads configuration and creates client instances
2. **Search**: Routes queries to appropriate databases
3. **Merging**: Combines results from multiple sources
4. **Deduplication**: Removes duplicate papers based on DOI/title

Fallback modes:
- **Sequential**: Try databases one by one
- **Parallel**: Query all simultaneously
- **First-only**: Use only the first enabled database

## Database Clients

Each client implements the `DatabaseClient` interface:

### Client Responsibilities

1. **API Communication**: HTTP requests with proper headers
2. **Response Parsing**: Convert API responses to `Paper` objects
3. **Field Mapping**: Map database-specific fields to unified schema
4. **Error Handling**: Handle API errors gracefully
5. **Rate Limiting**: Respect API rate limits

### Example: CrossRef Client

```python
class CrossRefClient(DatabaseClient):
    def search(self, filters: SearchFilters) -> SearchResult:
        # Build query parameters
        params = self._build_query_params(filters)
        
        # Make API request with rate limiting
        response = self._make_request("/works", params)
        
        # Parse response
        papers = [self._parse_paper(item) for item in response["items"]]
        
        return SearchResult(papers=papers, databases_queried=["crossref"])
    
    def _parse_paper(self, data: dict) -> Paper:
        # Map CrossRef fields to unified schema
        return Paper(
            doi=data.get("DOI"),
            title=data.get("title", [""])[0],
            authors=self._parse_authors(data.get("author", [])),
            # ... more field mappings
        )
```

## Utility Components

### Rate Limiter

Two implementations:

1. **`RateLimiter`**: Uses `pyrate-limiter` for precise rate limiting
2. **`SimpleRateLimiter`**: Fallback using sliding window

Features:
- Per-second and per-minute limits
- Thread-safe operation
- Automatic waiting when limits reached

### PDF Downloader

Conservative PDF downloading with:

1. **Verification**: Check content type and file size before download
2. **Rate Limiting**: Polite delays between downloads (default 3s)
3. **Organization**: Automatic directory structure
4. **Statistics**: Track success/failure rates

Flow:
```
Paper → Check PDF URL → HEAD request → Verify → Download → Save
```

### Configuration Manager

Hierarchical configuration loading:

1. Default values (in code)
2. Package defaults (`config/databases.yaml`)
3. User config file (`config.yaml`)
4. Environment variables (`.env`)
5. Runtime config dict

Priority: Runtime > Env vars > User config > Package defaults > Code defaults

## Data Flow

### Search Flow

```
User Query
    ↓
SearchFilters
    ↓
UnifiedSearchClient
    ↓
Database Clients (sequential/parallel)
    ↓
API Requests (with rate limiting)
    ↓
Raw API Responses
    ↓
Paper Objects (parsed and normalized)
    ↓
SearchResult (merged and deduplicated)
    ↓
User
```

### Export Flow

```
SearchResult
    ↓
Format Converter (CSV/JSON/BibTeX)
    ↓
File Writer (with optional streaming)
    ↓
Output File
```

## Extension Points

### Adding a New Database

1. Create new client class in `clients/`:

```python
from paperseek.core.base import DatabaseClient

class NewDatabaseClient(DatabaseClient):
    def __init__(self, config: dict):
        super().__init__("newdb", config)
    
    def search(self, filters: SearchFilters) -> SearchResult:
        # Implement search logic
        pass
    
    def lookup_doi(self, doi: str) -> Optional[Paper]:
        # Implement DOI lookup
        pass
```

2. Register in `UnifiedSearchClient`:

```python
DATABASE_CLIENTS = {
    "crossref": CrossRefClient,
    "openalex": OpenAlexClient,
    "newdb": NewDatabaseClient,  # Add here
}
```

3. Add default configuration in `config/databases.yaml`

### Adding Export Formats

Add methods to `SearchResult`:

```python
def to_custom_format(self, filename: str) -> None:
    """Export to custom format."""
    # Implementation
```

## Design Principles

### 1. Single Responsibility
Each class has one clear purpose:
- Clients handle API communication
- Models handle data structure
- Utilities handle cross-cutting concerns

### 2. Open/Closed Principle
Open for extension (new databases), closed for modification (core logic stable).

### 3. Dependency Inversion
High-level `UnifiedSearchClient` depends on abstract `DatabaseClient`, not concrete implementations.

### 4. Composition Over Inheritance
Clients use composition (rate limiters, HTTP sessions) rather than deep inheritance.

### 5. Fail-Safe Defaults
Conservative defaults: low rate limits, polite delays, safe file operations.

## Error Handling

Hierarchical exception system:

```
AcademicSearchException (base)
├── APIException
│   ├── RateLimitException
│   ├── AuthenticationException
│   └── NetworkException
└── ValidationException
```

Strategy:
- Catch specific exceptions close to source
- Log errors with context
- Return partial results when possible
- Never crash on single database failure

## Testing Strategy

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test database clients with real APIs (rate-limited)
- **Mock tests**: Test unified client with mocked database responses
- **Type checking**: Use mypy in standard mode

## Performance Considerations

- **Connection pooling**: Reuse HTTP sessions
- **Rate limiting**: Prevent API throttling
- **Streaming**: Handle large result sets efficiently
- **Deduplication**: Use hash sets for O(1) lookup
- **Lazy loading**: Parse fields only when accessed

## Future Enhancements

Potential improvements:

- **Async support**: Use `asyncio` for parallel queries
- **Caching**: Cache results to reduce API calls
- **Database**: Store results in SQLite/PostgreSQL
- **Web interface**: Flask/FastAPI dashboard
- **Monitoring**: Prometheus metrics for API usage
