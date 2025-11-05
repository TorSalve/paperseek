# PaperSeek

A production-ready Python package providing a unified interface for searching multiple academic databases with comprehensive features including rate limiting, field tracking, and multiple export formats.

## Overview

PaperSeek provides a single, consistent API to search across 9 major academic databases:

- **CrossRef** - Comprehensive metadata for scholarly publications
- **OpenAlex** - Open catalog of scholarly papers, authors, and institutions
- **Semantic Scholar** - AI-powered academic search with citation context
- **DOI.org** - DOI resolution service
- **PubMed** - Biomedical and life sciences literature (36M+ citations)
- **arXiv** - Physics, mathematics, computer science preprints
- **CORE** - World's largest collection of open access papers
- **Unpaywall** - Open access article finder
- **DBLP** - Computer science bibliography

## Key Features

### 🔍 Unified Search Interface
Search across multiple databases with a single API call, with automatic result merging and deduplication.

### 📊 Field Tracking & Statistics
Track field availability across results, generate coverage reports, and filter by required fields.

### ⏱️ Polite Rate Limiting
Configurable per-database rate limits with automatic retry logic and exponential backoff.

### 📄 Multiple Export Formats
Export results to CSV, JSON, JSONL, or BibTeX with customizable fields and streaming support.

### 📥 PDF Downloader
Conservative, polite PDF downloader for open access papers with progress tracking and verification.

### 🔄 Flexible Fallback Modes
Configure fallback behavior between databases: sequential, parallel, or first-only.

## Quick Example

```python
from paperseek import UnifiedSearchClient

# Initialize client with multiple databases
client = UnifiedSearchClient(databases=["crossref", "openalex", "semantic_scholar"])

# Search for papers
results = client.search(
    query="machine learning",
    year=2023,
    max_results=100
)

# Access results
print(f"Found {len(results)} papers")
for paper in results.papers[:5]:
    print(f"- {paper.title}")
    print(f"  Authors: {', '.join(a.name for a in paper.authors[:3])}")
    print(f"  Citations: {paper.citation_count}")
```

## Installation

```bash
pip install paperseek
```

Or install from source:

```bash
git clone https://github.com/TorSalve/paperseek.git
cd paperseek
pip install -e .
```

## Next Steps

- [Installation Guide](installation.md) - Detailed installation instructions
- [Quick Start](quickstart.md) - Get started in 5 minutes
- [Database Overview](databases.md) - Learn about each database
- [API Reference](api/unified_client.md) - Complete API documentation
- [Examples](examples.md) - Code examples for common tasks

## License

MIT License - see LICENSE file for details.
