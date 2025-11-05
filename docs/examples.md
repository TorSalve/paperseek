# Examples

This page provides code examples for common use cases.

## Basic Searches

### Simple Query Search

```python
from paperseek import UnifiedSearchClient

client = UnifiedSearchClient(databases=["crossref", "openalex"])
results = client.search(query="quantum computing", max_results=50)

for paper in results.papers:
    print(f"{paper.title} ({paper.year})")
```

### Search by Venue

```python
# Find papers from a specific journal or conference
results = client.search(
    venue="Nature",
    year=2023,
    max_results=100
)
```

### Search by Author

```python
# Find papers by a specific author
results = client.search(
    author="Einstein",
    year_range=(1900, 1930),
    max_results=50
)
```

### Search with Multiple Filters

```python
from paperseek import SearchFilters

filters = SearchFilters(
    query="neural networks",
    venue="NeurIPS",
    year=2023,
    min_citations=10,
    max_results=100
)

results = client.search_with_filters(filters)
```

## DOI Lookups

### Single DOI Lookup

```python
doi = "10.1038/nature12345"
results = client.lookup_dois([doi])

if results.papers:
    paper = results.papers[0]
    print(f"Title: {paper.title}")
    print(f"Authors: {', '.join(a.name for a in paper.authors)}")
```

### Batch DOI Lookup

```python
dois = [
    "10.1038/nature12345",
    "10.1126/science.abc123",
    "10.1109/access.2023.1234567"
]

results = client.lookup_dois(dois)
print(f"Found {len(results)} papers out of {len(dois)} DOIs")
```

## Field Statistics and Filtering

### Check Field Availability

```python
# Get statistics on field coverage
stats = results.get_field_statistics()

print("Field Coverage:")
for field, info in stats.items():
    print(f"  {field}: {info['percentage']:.1f}% ({info['count']}/{info['total']})")
```

### Filter by Required Fields

```python
# Only keep papers with specific fields
filtered = results.filter_by_required_fields(["doi", "abstract", "citation_count"])
print(f"Papers with all required fields: {len(filtered)}/{len(results)}")
```

### Export with Field Statistics

```python
# Export CSV with field coverage report
results.to_csv(
    "papers.csv",
    include_field_stats=True,
    columns=["title", "authors", "year", "doi", "abstract", "citation_count"]
)
```

## Export Formats

### CSV Export

```python
# Basic CSV export
results.to_csv("papers.csv")

# Custom columns
results.to_csv(
    "papers_custom.csv",
    columns=["title", "authors", "year", "doi", "venue"]
)

# With field statistics
results.to_csv(
    "papers_stats.csv",
    include_field_stats=True
)
```

### JSON Export

```python
# Pretty-printed JSON
results.to_json("papers.json", indent=2)

# Compact JSON
results.to_json("papers_compact.json")
```

### JSONL Export

```python
# JSON Lines format (one object per line)
results.to_jsonl("papers.jsonl")
```

### BibTeX Export

```python
# For citation managers (Zotero, Mendeley, etc.)
results.to_bibtex("papers.bib")
```

## PDF Downloading

### Basic PDF Download

```python
from paperseek import PDFDownloader

# Initialize with conservative settings
downloader = PDFDownloader(
    output_dir="papers/pdfs",
    delay_seconds=3.0,  # Polite delay
    max_file_size_mb=50
)

# Download PDFs
stats = downloader.download_papers(results.papers)

print(f"✓ Downloaded: {stats['successful']}")
print(f"✗ Failed: {stats['failed']}")
print(f"⊘ Skipped: {stats['skipped']}")
```

### Download with Custom Organization

```python
# Organize by database
downloader = PDFDownloader(
    output_dir="papers/pdfs",
    organize_by_database=True
)

stats = downloader.download_papers(results.papers)
```

### Download with Progress Tracking

```python
# Download and print progress
for i, paper in enumerate(results.papers, 1):
    print(f"Downloading {i}/{len(results)}: {paper.title[:50]}...")
    success = downloader.download_paper(paper)
    if success:
        print("  ✓ Success")
    else:
        print("  ✗ Failed or skipped")

# Get final statistics
stats = downloader.get_statistics()
print(f"\nTotal: {stats['successful']} successful, {stats['failed']} failed")
```

### Selective PDF Download

```python
# Only download papers with DOI and from specific databases
papers_to_download = [
    p for p in results.papers
    if p.doi and p.source_database in ["arxiv", "core"]
]

downloader = PDFDownloader(output_dir="selected_pdfs")
stats = downloader.download_papers(papers_to_download)
```

## Advanced Usage

### Multiple Database Search with Fallback

```python
# Sequential fallback: try each database until max_results reached
client = UnifiedSearchClient(
    databases=["crossref", "openalex", "semantic_scholar"],
    config_dict={"fallback_mode": "sequential"}
)

results = client.search(query="machine learning", max_results=100)
print(f"Databases queried: {', '.join(results.databases_queried)}")
```

### Parallel Search Across Databases

```python
# Query all databases simultaneously
client = UnifiedSearchClient(
    databases=["crossref", "openalex", "semantic_scholar"],
    config_dict={"fallback_mode": "parallel"}
)

results = client.search(query="quantum computing", max_results=50)
```

### Domain-Specific Searches

#### Biomedical Literature

```python
# Focus on biomedical databases
client = UnifiedSearchClient(databases=["pubmed", "semantic_scholar"])

results = client.search(
    query="CRISPR gene editing",
    year=2023,
    max_results=100
)
```

#### Computer Science

```python
# Focus on CS databases
client = UnifiedSearchClient(databases=["dblp", "arxiv", "semantic_scholar"])

results = client.search(
    query="transformer models",
    venue="NeurIPS OR ICML OR ICLR",
    year=2023,
    max_results=100
)
```

#### Open Access Only

```python
# Prioritize OA databases
client = UnifiedSearchClient(databases=["arxiv", "core", "unpaywall"])

results = client.search(
    query="climate change",
    max_results=100
)

# Download PDFs (all should be OA)
downloader = PDFDownloader(output_dir="oa_papers")
downloader.download_papers(results.papers)
```

### Large-Scale Data Collection

```python
import time

# Collect data for multiple queries
queries = [
    "machine learning",
    "deep learning",
    "neural networks",
    "reinforcement learning"
]

all_results = []

for query in queries:
    print(f"Searching for: {query}")
    results = client.search(query=query, year=2023, max_results=500)
    all_results.append(results)
    
    # Export intermediate results
    results.to_csv(f"results_{query.replace(' ', '_')}.csv")
    
    # Polite delay between queries
    time.sleep(5)

# Combine and export all results
combined = all_results[0]
for r in all_results[1:]:
    combined.extend(r.papers)

combined.to_csv("all_results.csv", include_field_stats=True)
```

### Citation Network Analysis

```python
# Get papers and their citations
results = client.search(query="graph neural networks", max_results=100)

# Filter papers with high citation counts
highly_cited = [p for p in results.papers if (p.citation_count or 0) > 100]

# Look up citing papers for each
citation_network = {}
for paper in highly_cited:
    if paper.doi:
        citing = client.search(query=f'cites:"{paper.doi}"', max_results=50)
        citation_network[paper.doi] = citing.papers

print(f"Built citation network with {len(citation_network)} seed papers")
```

## Command Line Interface

The package includes a CLI tool for quick searches:

```bash
# Basic search
python search_cli.py "machine learning" --max-results 50

# Search with filters
python search_cli.py "quantum computing" \
    --venue "Nature" \
    --year 2023 \
    --max-results 100

# Export to CSV
python search_cli.py "neural networks" \
    --max-results 200 \
    --output papers.csv

# Multiple databases
python search_cli.py "climate change" \
    --databases crossref openalex semantic_scholar \
    --max-results 100
```

For more details, see the [CLI documentation](https://github.com/yourusername/academic-search-unified/blob/main/search_cli.py).

## See Also

- [Database Overview](databases.md) - Learn about each database
- [PDF Downloader](pdf_downloader.md) - Detailed PDF download guide
- [API Reference](api/unified_client.md) - Complete API documentation
