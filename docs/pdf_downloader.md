# PDF Downloader Documentation

## Overview

The `PDFDownloader` utility provides a polite, conservative way to download open access PDFs from academic papers. It includes built-in rate limiting, content verification, and progress tracking to ensure respectful use of academic resources.

## Key Features

### Polite & Conservative
- **Rate Limiting**: Default 3 seconds between downloads (configurable)
- **Content Verification**: Validates downloaded files are actually PDFs
- **File Size Limits**: Prevents downloading excessively large files (default: 50 MB)
- **User-Agent Headers**: Identifies the downloader properly
- **Email Support**: Include email for tracking and polite requests
- **SSL Verification**: Respects HTTPS certificates

### Smart Download Management
- **Duplicate Detection**: Skip already downloaded files
- **Resume Capability**: Won't re-download existing valid PDFs
- **Organize by Database**: Automatically organize files by source
- **Progress Tracking**: Monitor success rates and statistics
- **Error Handling**: Gracefully handles timeouts, HTTP errors, and invalid content

### Batch Operations
- **Download from Search Results**: Process entire result sets
- **Filter by Open Access**: Only download OA papers (respects copyright)
- **Max Download Limits**: Set maximum number of files to download
- **Subdirectory Support**: Organize downloads into folders

## Basic Usage

### Simple Download

```python
from paperseek import UnifiedSearchClient, PDFDownloader

# Search for papers
client = UnifiedSearchClient(databases=['arxiv'])
results = client.search(title='neural networks', max_results=10)

# Download PDFs
with PDFDownloader(
    download_dir='./papers',
    email='you@example.com'
) as downloader:
    downloaded = downloader.download_search_results(results)
    print(f"Downloaded {len(downloaded)} PDFs")
```

### Download Individual Paper

```python
from paperseek import PDFDownloader
from paperseek.core.models import Paper

# Create downloader
downloader = PDFDownloader(
    download_dir='./downloads',
    rate_limit_seconds=3.0,
    email='you@example.com'
)

# Download a single paper
paper = Paper(
    title='Attention Is All You Need',
    pdf_url='https://arxiv.org/pdf/1706.03762.pdf',
    doi='10.48550/arXiv.1706.03762'
)

filepath = downloader.download_paper(paper)
if filepath:
    print(f"Downloaded to: {filepath}")

downloader.close()
```

## Configuration Options

### Constructor Parameters

```python
PDFDownloader(
    download_dir='./downloads',        # Where to save PDFs
    rate_limit_seconds=3.0,           # Seconds between downloads
    timeout=60,                        # Request timeout
    max_file_size_mb=50,              # Max file size to download
    user_agent='...',                  # User-Agent string
    email=None,                        # Email for polite requests
    overwrite=False,                   # Overwrite existing files
    verify_ssl=True,                   # Verify SSL certificates
)
```

### Recommended Settings by Use Case

#### Conservative (Default)
Best for public use, respects all server limits:
```python
downloader = PDFDownloader(
    rate_limit_seconds=3.0,  # 3 seconds between downloads
    max_file_size_mb=50,
    email='you@example.com'
)
```

#### Very Conservative
For sensitive sources or high-traffic servers:
```python
downloader = PDFDownloader(
    rate_limit_seconds=5.0,  # 5 seconds between downloads
    max_file_size_mb=30,
    timeout=90,
    email='you@example.com'
)
```

#### Moderate
When downloading from known-friendly sources:
```python
downloader = PDFDownloader(
    rate_limit_seconds=2.0,  # 2 seconds between downloads
    max_file_size_mb=100,
    email='you@example.com'
)
```

## Methods

### download_paper()

Download a single paper's PDF.

```python
def download_paper(
    paper: Paper,
    filename: Optional[str] = None,
    subdirectory: Optional[str] = None,
) -> Optional[Path]
```

**Parameters:**
- `paper`: Paper object with `pdf_url` attribute
- `filename`: Optional custom filename (auto-generated if not provided)
- `subdirectory`: Optional subdirectory within `download_dir`

**Returns:** Path to downloaded file, or None if failed

**Example:**
```python
filepath = downloader.download_paper(
    paper,
    filename='custom_name.pdf',
    subdirectory='arxiv_papers'
)
```

### download_papers()

Download PDFs for multiple papers.

```python
def download_papers(
    papers: List[Paper],
    subdirectory: Optional[str] = None,
    max_downloads: Optional[int] = None,
) -> Dict[str, Path]
```

**Parameters:**
- `papers`: List of Paper objects
- `subdirectory`: Optional subdirectory
- `max_downloads`: Maximum number to download (for testing/limiting)

**Returns:** Dictionary mapping paper titles to file paths

**Example:**
```python
downloaded = downloader.download_papers(
    papers,
    subdirectory='ml_papers',
    max_downloads=5  # Download only first 5
)
```

### download_search_results()

Download PDFs from search results with filtering.

```python
def download_search_results(
    search_result: SearchResult,
    subdirectory: Optional[str] = None,
    max_downloads: Optional[int] = None,
    only_open_access: bool = True,
) -> Dict[str, Path]
```

**Parameters:**
- `search_result`: SearchResult object from client.search()
- `subdirectory`: Optional subdirectory
- `max_downloads`: Maximum number to download
- `only_open_access`: Only download papers marked as OA (default: True)

**Returns:** Dictionary mapping paper titles to file paths

**Example:**
```python
downloaded = downloader.download_search_results(
    results,
    only_open_access=True,  # Only download OA papers
    max_downloads=10
)
```

### get_statistics() / print_statistics()

Get or print download statistics.

```python
stats = downloader.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Total size: {stats['total_mb']:.2f} MB")

# Or print formatted statistics
downloader.print_statistics()
```

**Statistics included:**
- `attempted`: Number of download attempts
- `successful`: Number of successful downloads
- `failed`: Number of failed downloads
- `skipped`: Number of skipped (already exist)
- `success_rate`: Percentage successful
- `total_mb`: Total data downloaded in MB

## File Naming

The downloader automatically generates safe filenames based on paper metadata:

1. **DOI-based** (preferred): `10.48550_arXiv.1706.03762.pdf`
2. **Source ID**: `arxiv_1706.03762.pdf`
3. **URL hash** (fallback): `paper_a3b2c1d4e5f6.pdf`

### Custom Filenames

```python
# Use custom filename
downloader.download_paper(paper, filename='my_paper.pdf')

# Or generate based on paper attributes
filename = f"{paper.year}_{paper.authors[0].name.split()[0]}.pdf"
downloader.download_paper(paper, filename=filename)
```

## Organization Strategies

### By Database

```python
# Organize by source database
for paper in results.papers:
    if paper.pdf_url:
        downloader.download_paper(
            paper,
            subdirectory=paper.source_database
        )
# Creates: downloads/arxiv/paper1.pdf
#          downloads/core/paper2.pdf
```

### By Year

```python
for paper in results.papers:
    if paper.pdf_url and paper.year:
        downloader.download_paper(
            paper,
            subdirectory=str(paper.year)
        )
```

### By Topic/Query

```python
# Different topics in different folders
topics = {
    'machine learning': ['neural networks', 'deep learning'],
    'nlp': ['natural language', 'transformers'],
}

for topic, keywords in topics.items():
    for keyword in keywords:
        results = client.search(title=keyword, max_results=20)
        downloader.download_search_results(
            results,
            subdirectory=topic,
            max_downloads=10
        )
```

## Error Handling

The downloader handles various error conditions gracefully:

### Common Issues

**File size too large:**
```python
# Increase limit if needed
downloader = PDFDownloader(max_file_size_mb=100)
```

**Timeout errors:**
```python
# Increase timeout for slow connections
downloader = PDFDownloader(timeout=120)
```

**Invalid PDFs:**
- Automatically detected via magic number check
- HTML responses are rejected
- Invalid files are removed

**SSL certificate errors:**
```python
# Disable SSL verification (not recommended for production)
downloader = PDFDownloader(verify_ssl=False)
```

### Logging

Enable debug logging to see detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

downloader = PDFDownloader(...)
# Will show detailed download progress
```

## Best Practices

### 1. Always Use Email

```python
# GOOD: Identifies you for tracking
downloader = PDFDownloader(email='you@example.com')

# BAD: Anonymous downloading
downloader = PDFDownloader()
```

### 2. Respect Rate Limits

```python
# GOOD: Conservative rate limiting
downloader = PDFDownloader(rate_limit_seconds=3.0)

# BAD: Too aggressive
downloader = PDFDownloader(rate_limit_seconds=0.1)
```

### 3. Use Open Access Filtering

```python
# GOOD: Only download OA papers
downloaded = downloader.download_search_results(
    results,
    only_open_access=True
)

# CAUTION: May download copyrighted material
downloaded = downloader.download_search_results(
    results,
    only_open_access=False
)
```

### 4. Limit Batch Operations

```python
# GOOD: Reasonable batch size
downloaded = downloader.download_search_results(
    results,
    max_downloads=20
)

# CAUTION: Large batch, takes time
downloaded = downloader.download_search_results(
    results,
    max_downloads=1000
)
```

### 5. Use Context Managers

```python
# GOOD: Automatic cleanup
with PDFDownloader(...) as downloader:
    downloaded = downloader.download_search_results(results)

# OK: Manual cleanup
downloader = PDFDownloader(...)
try:
    downloaded = downloader.download_search_results(results)
finally:
    downloader.close()
```

## Complete Examples

### Example 1: Download arXiv Papers

```python
from paperseek import UnifiedSearchClient, PDFDownloader

# Search arXiv for recent papers
client = UnifiedSearchClient(databases=['arxiv'])
results = client.search(
    title='transformer architecture',
    year_range=(2023, 2024),
    max_results=20
)

# Download with conservative settings
with PDFDownloader(
    download_dir='./arxiv_papers',
    rate_limit_seconds=3.0,
    email='researcher@university.edu'
) as downloader:
    
    downloaded = downloader.download_search_results(
        results,
        max_downloads=10
    )
    
    print(f"\nDownloaded {len(downloaded)} papers:")
    for title, path in downloaded.items():
        print(f"  {path.name}")
    
    downloader.print_statistics()

client.close()
```

### Example 2: Find OA Versions with Unpaywall

```python
# Search for papers
client = UnifiedSearchClient(databases=['openalex'])
results = client.search(
    title='climate change',
    year=2023,
    max_results=50
)

# Check for OA versions
unpaywall = UnifiedSearchClient(databases=['unpaywall'])
oa_papers = []

for paper in results.papers:
    if paper.doi:
        oa_version = unpaywall.get_by_doi(paper.doi)
        if oa_version and oa_version.is_open_access and oa_version.pdf_url:
            oa_papers.append(oa_version)

print(f"Found {len(oa_papers)} papers with OA PDFs")

# Download OA versions
with PDFDownloader(
    download_dir='./oa_papers',
    rate_limit_seconds=2.0,
    email='researcher@university.edu'
) as downloader:
    
    downloaded = downloader.download_papers(oa_papers, max_downloads=20)
    downloader.print_statistics()
```

### Example 3: Organize by Database

```python
# Search multiple databases
client = UnifiedSearchClient(
    databases=['arxiv', 'core', 'openalex'],
    fallback_mode='parallel'
)

results = client.search(
    title='deep learning',
    year_range=(2022, 2023),
    max_results=30
)

# Download and organize by source
with PDFDownloader(
    download_dir='./papers',
    rate_limit_seconds=3.0,
    email='researcher@university.edu'
) as downloader:
    
    # Group by database
    by_db = {}
    for paper in results.papers:
        if paper.pdf_url:
            db = paper.source_database
            if db not in by_db:
                by_db[db] = []
            by_db[db].append(paper)
    
    # Download each database's papers
    for db, papers in by_db.items():
        print(f"\nDownloading {len(papers)} papers from {db}...")
        downloaded = downloader.download_papers(
            papers,
            subdirectory=db,
            max_downloads=5
        )
        print(f"Downloaded {len(downloaded)} from {db}")
    
    downloader.print_statistics()
```

## Troubleshooting

### No PDFs Downloaded

**Check if papers have PDF URLs:**
```python
papers_with_pdfs = [p for p in results.papers if p.pdf_url]
print(f"{len(papers_with_pdfs)} papers have PDF URLs")
```

**Check open access filter:**
```python
# Try without OA filter
downloaded = downloader.download_search_results(
    results,
    only_open_access=False  # Download all with PDF URLs
)
```

### Downloads Failing

**Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check statistics for patterns:**
```python
stats = downloader.get_statistics()
if stats['failed'] > stats['successful']:
    print("Many failures - check network or URLs")
```

**Test with single paper:**
```python
# Test download capability
paper = results.papers[0]
filepath = downloader.download_paper(paper)
if not filepath:
    print(f"Failed to download: {paper.pdf_url}")
```

### Slow Downloads

**Reduce rate limiting (carefully):**
```python
# Only if you're sure the source can handle it
downloader = PDFDownloader(rate_limit_seconds=2.0)
```

**Download fewer papers:**
```python
downloaded = downloader.download_search_results(
    results,
    max_downloads=5  # Start small
)
```

## Rate Limiting Guidelines

### By Source

| Source         | Recommended Rate Limit | Notes                     |
| -------------- | ---------------------- | ------------------------- |
| arXiv          | 3.0 seconds            | As per arXiv guidelines   |
| CORE           | 2.0 seconds            | Respectful for free tier  |
| Unpaywall      | 2.0 seconds            | 100k/day limit            |
| OpenAlex       | 3.0 seconds            | Conservative for OA links |
| PubMed Central | 4.0 seconds            | Very conservative         |
| Unknown/Mixed  | 3.0 seconds            | Safe default              |

### General Guidelines

- **Default**: Use 3.0 seconds for mixed sources
- **Single trusted source**: Can use 2.0 seconds
- **High-traffic times**: Increase to 5.0 seconds
- **Personal research**: 3.0 seconds is respectful
- **Large batches**: Consider 4-5 seconds

## Legal & Ethical Considerations

### Copyright

- Only download **open access** papers by default
- Respect copyright and licensing terms
- Use `only_open_access=True` filter
- Check individual paper licenses

### Server Load

- Use conservative rate limiting
- Don't download during peak hours if possible
- Limit batch sizes for large operations
- Include email for tracking

### Terms of Service

Different sources have different terms:

- **arXiv**: Free to download, but be respectful
- **CORE**: Free for non-commercial, respect rate limits
- **Unpaywall**: 100k requests/day, email required
- **PMC**: Free, but follow NCBI guidelines

Always check the specific terms of service for each source.

## Summary

The PDF Downloader provides a responsible way to download open access academic papers:

✅ **Conservative by default** (3 second delays)  
✅ **Respects copyright** (OA filtering)  
✅ **Verifies content** (checks PDF format)  
✅ **Tracks progress** (statistics and logging)  
✅ **Handles errors** (timeouts, invalid files)  
✅ **Organizes files** (by database, year, etc.)  

Use it responsibly and respect server resources!
