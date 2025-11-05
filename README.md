# PaperSeek

A production-ready Python package providing a unified interface for searching multiple academic databases (CrossRef, OpenAlex, Semantic Scholar, DOI.org, PubMed, arXiv, CORE, Unpaywall, DBLP) with comprehensive features including rate limiting, field tracking, and multiple export formats.

## Features

### Core Capabilities

- **Unified API**: Single interface for searching across multiple academic databases
- **Multiple Databases**: 
  - CrossRef: Comprehensive metadata for scholarly publications
  - OpenAlex: Open catalog of scholarly papers, authors, and institutions
  - Semantic Scholar: AI-powered academic search with citation context
  - DOI.org: DOI resolution service
  - PubMed: Biomedical and life sciences literature (36M+ citations)
  - arXiv: Physics, mathematics, computer science preprints
  - CORE: World's largest collection of open access papers
  - Unpaywall: Open access article finder
  - DBLP: Computer science bibliography
- **Flexible Search**: Search by venue, year, author, title, DOI, keywords, and more
- **Fallback Support**: Automatic fallback between databases (sequential, parallel, or first-only modes)
- **Batch Lookups**: Efficiently look up multiple papers by identifier

### Field Tracking & Statistics

- **Field Availability Tracking**: Track which fields are present in results
- **Coverage Statistics**: Generate reports showing field availability percentages
- **Required Fields Filtering**: Filter results to only include papers with specific fields

### Rate Limiting & Polite Requests

- **Configurable Rate Limiting**: Per-database rate limits (requests per second/minute)
- **Automatic Retry Logic**: Exponential backoff for failed requests
- **Polite Requests**: User-Agent headers and email addresses following API guidelines
- **Request Throttling**: Respect API limits with automatic throttling

### Export Formats

- **CSV**: With customizable columns and field statistics
- **JSON/JSONL**: For programmatic use
- **BibTeX**: For citation management
- **Streaming Exports**: Handle large datasets efficiently

### PDF Downloading

- **Polite Downloading**: Conservative rate limiting (3+ seconds between downloads)
- **Open Access Focus**: Download only OA papers respecting copyright
- **Smart Verification**: Checks content type and file size before downloading
- **Progress Tracking**: Monitor download statistics and success rates
- **Organization**: Organize downloads by database or custom subdirectories
- **Resume Support**: Skip already downloaded files
- **Batch Operations**: Download entire search results efficiently

### Code Quality

- **Type Hints**: Throughout the codebase
- **Comprehensive Error Handling**: Custom exception classes
- **Logging**: Configurable verbosity levels
- **Documentation**: Detailed docstrings (Google style)
- **PEP 8 Compliant**: Follows Python style guidelines

## Installation

```bash
# Clone the repository
git clone https://github.com/TorSalve/paperseek.git
cd paperseek

# Install the package
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

### Dependencies

- Python >= 3.8
- requests >= 2.31.0
- pydantic >= 2.0.0
- pandas >= 1.5.0
- pyyaml >= 6.0
- pyrate-limiter >= 3.0.0
- python-dotenv >= 1.0.0

## Quick Start

```python
from paperseek import UnifiedSearchClient

# Initialize client
client = UnifiedSearchClient(
    databases=['openalex', 'crossref', 'semantic_scholar'],
    fallback_mode='sequential'
)

# Search for papers
results = client.search(
    venue='ICML',
    year_range=(2020, 2023),
    required_fields=['abstract', 'citations'],
    max_results=100
)

# Get field statistics
stats = results.field_statistics()
print(stats['abstract'])  # abstract: 95/100 (95.0%)

# Export results
results.to_csv('icml_papers.csv', include_field_stats=True)
results.to_json('icml_papers.json')
results.to_bibtex('icml_papers.bib')

# Close client
client.close()
```

## Configuration

### Configuration Methods

The package supports multiple configuration methods (in priority order):

1. **Direct parameters** (highest priority)
2. **YAML configuration file**
3. **Environment variables**

### YAML Configuration

Create a `config.yaml` file:

```yaml
# General settings
email: your.email@example.com
user_agent: PaperSeek/0.1.0
log_level: INFO

# Fallback behavior
fallback_mode: sequential  # Options: sequential, parallel, first
fail_fast: false

# Database configurations
crossref:
  enabled: true
  rate_limit_per_second: 1.0
  timeout: 30
  max_retries: 3

openalex:
  enabled: true
  rate_limit_per_second: 2.0
  timeout: 30

semantic_scholar:
  enabled: true
  api_key: your_api_key  # Optional but recommended
  rate_limit_per_second: 1.0
  rate_limit_per_minute: 100

doi:
  enabled: true
  rate_limit_per_second: 2.0
```

Load configuration:

```python
client = UnifiedSearchClient(config_file='config.yaml')
```

### Environment Variables

Set environment variables with the prefix `ACADEMIC_SEARCH_`:

```bash
export ACADEMIC_SEARCH_EMAIL=your.email@example.com
export ACADEMIC_SEARCH_CROSSREF__RATE_LIMIT_PER_SECOND=1.0
export ACADEMIC_SEARCH_SEMANTIC_SCHOLAR__API_KEY=your_key
```

See `.env.example` for a complete list.

## Usage Examples

### Basic Search

```python
from paperseek import UnifiedSearchClient

client = UnifiedSearchClient()

# Search by venue and year
results = client.search(
    venue='NeurIPS',
    year=2023,
    max_results=50
)

print(f"Found {len(results)} papers")
for paper in results[:5]:
    print(f"- {paper.title} ({paper.year})")
```

### Search with Multiple Filters

```python
# Search by multiple criteria
results = client.search(
    venue='CVPR',
    year_range=(2020, 2023),
    author='Kaiming He',
    required_fields=['abstract', 'doi'],
    max_results=100
)

# Filter results
filtered = results.filter_by_required_fields(['citation_count'])
print(f"Papers with citations: {len(filtered)}")
```

### Lookup by Identifier

```python
# Single DOI lookup
paper = client.get_by_doi("10.48550/arXiv.1706.03762")
print(paper.title)  # "Attention is All You Need"

# Batch lookup
dois = [
    "10.48550/arXiv.1706.03762",
    "10.48550/arXiv.1512.03385",
    "10.48550/arXiv.1409.1556"
]
results = client.batch_lookup(dois, id_type='doi')
print(f"Found {len(results)} papers")
```

### Field Statistics

```python
results = client.search(venue='ICML', year=2023, max_results=100)

# Get field statistics
stats = results.field_statistics()

for field_name, stat in stats.items():
    print(f"{stat}")
    # Output: abstract: 85/100 (85.0%)

# Get coverage report
print(results.get_field_coverage_report())
```

### Export to Multiple Formats

```python
# CSV export
results.to_csv('papers.csv', include_field_stats=True)

# JSON export
results.to_json('papers.json', pretty=True)

# JSONL export (one paper per line)
results.to_jsonl('papers.jsonl')

# BibTeX export
results.to_bibtex('papers.bib')

# Custom CSV columns
from paperseek.exporters.csv_exporter import CSVExporter

exporter = CSVExporter()
columns = ['title', 'authors', 'year', 'doi', 'citation_count']
exporter.export(results, 'custom.csv', columns=columns)
```

### Parallel vs Sequential Search

```python
# Sequential mode: try databases in order until success
client = UnifiedSearchClient(
    databases=['crossref', 'openalex', 'semantic_scholar'],
    fallback_mode='sequential'
)
results = client.search(venue='ICML', year=2023, max_results=100)

# Parallel mode: query all databases simultaneously and merge
client = UnifiedSearchClient(
    databases=['crossref', 'openalex', 'semantic_scholar'],
    fallback_mode='parallel'
)
results = client.search(venue='ICML', year=2023, max_results=100)
print(f"Results from {len(results.databases_queried)} databases")
```

### Streaming for Large Datasets

```python
from paperseek.exporters.csv_exporter import StreamingCSVExporter

# Stream results to CSV for large datasets
with StreamingCSVExporter('large_dataset.csv') as exporter:
    for year in range(2015, 2024):
        results = client.search(venue='ICML', year=year, max_results=1000)
        exporter.write_papers(results.papers)
```

### Using SearchFilters

```python
from paperseek.core.models import SearchFilters

# Create custom filters
filters = SearchFilters(
    venue='ACL',
    year_start=2020,
    year_end=2023,
    required_fields=['abstract', 'doi'],
    max_results=200,
    combine_filters_with_and=True
)

results = client.search_with_filters(filters)
```

### Context Manager

```python
# Automatic cleanup with context manager
with UnifiedSearchClient(databases=['openalex']) as client:
    results = client.search(venue='ICLR', year=2023, max_results=50)
    results.to_csv('iclr_2023.csv')
# Client automatically closed
```

### Downloading PDFs (Open Access)

```python
from paperseek import UnifiedSearchClient, PDFDownloader

# Search for open access papers
client = UnifiedSearchClient(databases=['arxiv', 'core', 'openalex'])
results = client.search(
    title='machine learning',
    year_range=(2022, 2023),
    max_results=20
)

# Download PDFs with polite rate limiting
with PDFDownloader(
    download_dir='./downloads',
    rate_limit_seconds=3.0,  # Wait 3 seconds between downloads
    max_file_size_mb=50,
    email='your.email@example.com',
) as downloader:
    
    # Download only open access papers
    downloaded = downloader.download_search_results(
        results,
        only_open_access=True,
        max_downloads=10
    )
    
    print(f"Downloaded {len(downloaded)} PDFs")
    downloader.print_statistics()

client.close()
```

**PDF Downloader Features:**
- Conservative rate limiting (default: 3 seconds between downloads)
- Content verification (ensures downloaded files are actually PDFs)
- File size limits (default: 50 MB max)
- Automatic organization by database
- Skip already downloaded files
- Progress tracking and statistics
- Respects robots.txt and HTTP headers

## Database-Specific Notes

### CrossRef

- **No API key required** but email recommended for polite pool access
- **Rate limit**: ~50 requests/second for polite pool, ~5/second otherwise
- **Best for**: DOI-based lookups, journal articles
- **Field coverage**: Good for basic metadata, limited abstracts

### OpenAlex

- **Polite Pool Access**: Add email to get ~10 requests/second (vs ~1/sec without)
- **API key optional**: Pro users can use API key for premium features and higher limits
- **Rate limit**: ~10 req/sec with polite pool (email), higher with Pro API key
- **Best for**: Broad searches, open access papers, citation counts
- **Field coverage**: Excellent coverage including abstracts
- **Setup**: Email is automatically added via `mailto` parameter when provided

### Semantic Scholar

- **API key recommended** for higher rate limits
- **Rate limit**: ~1/second without key, ~10/second with key
- **Best for**: AI/CS papers, citation graphs, paper recommendations
- **Field coverage**: Excellent for CS papers, good abstract coverage

### DOI.org

- **No API key required**
- **Rate limit**: Generous
- **Best for**: DOI resolution, getting basic metadata
- **Field coverage**: Basic metadata only

## API Documentation

### UnifiedSearchClient

Main class for searching across databases.

#### Methods

- `search(**kwargs)`: Search with keyword arguments
- `search_with_filters(filters)`: Search with SearchFilters object
- `get_by_doi(doi)`: Look up single paper by DOI
- `batch_lookup(identifiers, id_type)`: Look up multiple papers
- `get_client(database)`: Get specific database client
- `close()`: Close all client sessions

### SearchResult

Container for search results with methods for analysis and export.

#### Methods

- `field_statistics()`: Get field availability statistics
- `get_field_coverage_report()`: Generate coverage report
- `filter_by_required_fields(fields)`: Filter results by required fields
- `to_csv(filename, **kwargs)`: Export to CSV
- `to_json(filename, **kwargs)`: Export to JSON
- `to_jsonl(filename)`: Export to JSONL
- `to_bibtex(filename)`: Export to BibTeX

### Paper

Normalized paper metadata model.

#### Key Fields

- `doi`, `pmid`, `arxiv_id`: Identifiers
- `title`, `authors`, `abstract`: Content
- `year`, `publication_date`: Dates
- `venue`, `journal`, `conference`: Publication venue
- `keywords`: Keywords/topics
- `citation_count`, `reference_count`: Metrics
- `url`, `pdf_url`, `is_open_access`: Access
- `source_database`, `source_id`: Source tracking

## Rate Limiting Guidelines

### Recommended Settings

```yaml
crossref:
  rate_limit_per_second: 1.0  # Conservative for public API
  
openalex:
  rate_limit_per_second: 2.0  # Can be higher with polite requests
  
semantic_scholar:
  rate_limit_per_second: 1.0  # Without API key
  rate_limit_per_second: 5.0  # With API key
  
doi:
  rate_limit_per_second: 2.0
```

### Polite API Usage

Always provide an email address:

```python
client = UnifiedSearchClient(config_dict={'email': 'your.email@example.com'})
```

Or in config.yaml:

```yaml
email: your.email@example.com
```

## Testing

```bash
# Run tests
pytest tests/

```bash
# Run with coverage
pytest --cov=src/paperseek tests/

# Run specific test
pytest tests/test_clients.py::TestCrossRefClient
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

## Error Handling

The package provides custom exception classes:

```python
from paperseek.core.exceptions import (
    AcademicSearchError,      # Base exception
    ConfigurationError,        # Configuration issues
    DatabaseError,             # Database-specific errors
    RateLimitError,           # Rate limit exceeded
    APIError,                 # API request failed
    AuthenticationError,      # Auth failed
    SearchError,              # Search operation failed
    TimeoutError,             # Request timeout
    ExportError               # Export operation failed
)

try:
    results = client.search(venue='ICML', year=2023)
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
except APIError as e:
    print(f"API error: {e}")
```

## Logging

Configure logging:

```python
from paperseek.utils.logging import setup_logging

# Set up logging
setup_logging(level='DEBUG', log_file='academic_search.log')

# Or via config
client = UnifiedSearchClient(config_dict={
    'log_level': 'DEBUG',
    'log_file': 'search.log'
})
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Follow PEP 8 style guidelines
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Citation

If you use this package in your research, please cite:

```bibtex
@software{paperseek,
  title = {PaperSeek},
  author = {Tor-Salve Dalsgaard},
  year = {2025},
  url = {https://github.com/TorSalve/paperseek}
}
```

## Acknowledgments

This package interfaces with:
- [CrossRef API](https://api.crossref.org)
- [OpenAlex API](https://docs.openalex.org)
- [Semantic Scholar API](https://api.semanticscholar.org)
- [DOI.org](https://www.doi.org)

## Support

- **Issues**: [GitHub Issues](https://github.com/TorSalve/paperseek/issues)
- **Documentation**: [GitHub Wiki](https://github.com/TorSalve/paperseek/wiki)
- **Email**: torsalve@di.ku.dk

## Changelog

### Version 0.1.0 (2025-01-01)

- Initial release
- Support for CrossRef, OpenAlex, Semantic Scholar, and DOI.org
- Unified search interface with fallback support
- Field tracking and statistics
- Multiple export formats (CSV, JSON, JSONL, BibTeX)
- Comprehensive rate limiting and retry logic
- Full type hints and documentation
