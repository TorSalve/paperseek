# Quick Start

Get started with Academic Search Unified in just a few minutes!

## Basic Usage

### 1. Import and Initialize

```python
from paperseek import UnifiedSearchClient

# Create a client with default databases
client = UnifiedSearchClient(databases=["crossref", "openalex"])
```

### 2. Perform a Search

```python
# Simple query search
results = client.search(
    query="machine learning",
    max_results=50
)

print(f"Found {len(results)} papers")
```

### 3. Access Results

```python
# Iterate through results
for paper in results.papers[:5]:
    print(f"Title: {paper.title}")
    print(f"Authors: {', '.join(a.name for a in paper.authors)}")
    print(f"Year: {paper.year}")
    print(f"DOI: {paper.doi}")
    print(f"Citations: {paper.citation_count}")
    print()
```

## Common Use Cases

### Search by Venue and Year

```python
# Find papers from a specific conference/journal
results = client.search(
    venue="Nature",
    year=2023,
    max_results=100
)
```

### Search with Filters

```python
from paperseek import SearchFilters

# Create filter object
filters = SearchFilters(
    query="neural networks",
    year=2023,
    venue="NeurIPS",
    min_citations=10,
    max_results=100
)

results = client.search_with_filters(filters)
```

### Look Up by DOI

```python
# Look up specific papers by DOI
dois = [
    "10.1038/nature12345",
    "10.1126/science.abc123"
]

results = client.lookup_dois(dois)
```

### Search by Author

```python
# Find papers by author name
results = client.search(
    author="Geoffrey Hinton",
    year=2023,
    max_results=50
)
```

## Export Results

### Export to CSV

```python
# Export with default columns
results.to_csv("papers.csv")

# Export with custom columns
results.to_csv(
    "papers.csv",
    columns=["title", "authors", "year", "doi", "citation_count"]
)
```

### Export to JSON

```python
# Pretty-printed JSON
results.to_json("papers.json", indent=2)

# Compact JSON Lines format
results.to_jsonl("papers.jsonl")
```

### Export to BibTeX

```python
# For citation managers
results.to_bibtex("papers.bib")
```

## Field Statistics

### Check Field Availability

```python
# See what fields are available
stats = results.get_field_statistics()

print("Field Coverage:")
for field, coverage in stats.items():
    print(f"  {field}: {coverage['percentage']:.1f}%")
```

### Filter by Required Fields

```python
# Only keep papers with DOI and abstract
filtered = results.filter_by_required_fields(["doi", "abstract"])
print(f"Papers with DOI and abstract: {len(filtered)}")
```

## Download PDFs

```python
from paperseek import PDFDownloader

# Initialize downloader (conservative by default)
downloader = PDFDownloader(
    output_dir="papers/pdfs",
    delay_seconds=3.0  # Polite delay between downloads
)

# Download PDFs for papers that have OA links
stats = downloader.download_papers(results.papers)

print(f"Downloaded: {stats['successful']}")
print(f"Failed: {stats['failed']}")
print(f"Skipped: {stats['skipped']}")
```

## Configuration

### Using Config File

Create `config.yaml`:

```yaml
databases:
  crossref:
    enabled: true
    rate_limit_per_second: 1.0
  
  openalex:
    enabled: true
    email: "your.email@example.com"
  
  semantic_scholar:
    enabled: true
    api_key: "your_api_key"

fallback_mode: "sequential"
default_max_results: 100
```

Load configuration:

```python
client = UnifiedSearchClient(config_path="config.yaml")
```

### Using Environment Variables

Create `.env`:

```bash
OPENALEX_EMAIL=your.email@example.com
SEMANTIC_SCHOLAR_API_KEY=your_api_key
CORE_API_KEY=your_core_key
```

The client will automatically load these values.

### Using Config Dictionary

```python
config = {
    "crossref": {
        "enabled": True,
        "rate_limit_per_second": 1.0
    },
    "openalex": {
        "enabled": True,
        "email": "your.email@example.com"
    }
}

client = UnifiedSearchClient(
    databases=["crossref", "openalex"],
    config_dict=config
)
```

## Next Steps

- Learn about each [database](databases.md)
- Explore more [examples](examples.md)
- Read the [API reference](api/unified_client.md)
- Set up [PDF downloading](pdf_downloader.md)
