# Database Support Documentation

This document provides detailed information about all supported academic databases.

## Supported Databases

### 1. CrossRef
- **Website**: https://www.crossref.org/
- **Description**: Comprehensive metadata for scholarly publications from publishers
- **API Key**: Optional (not required for basic access)
- **Rate Limits**: ~50 requests/second (higher with polite pool)
- **Specialization**: General academic publications, DOI metadata
- **Key Features**:
  - Extensive DOI coverage
  - Publisher metadata
  - Citation data
  - Funder information

### 2. OpenAlex
- **Website**: https://openalex.org/
- **Description**: Fully open catalog of scholarly papers, authors, and institutions
- **API Key**: Optional (Premium tier for enhanced features)
- **Rate Limits**: ~10 req/sec with polite pool, higher with Premium
- **Specialization**: Open academic data, comprehensive coverage
- **Key Features**:
  - Completely open data
  - Author profiles
  - Institution data
  - Citation networks
  - Concepts/topics
  - Open access status

### 3. Semantic Scholar
- **Website**: https://www.semanticscholar.org/
- **Description**: AI-powered academic search with citation context
- **API Key**: Recommended for higher limits
- **Rate Limits**: ~1 req/sec (without key), ~10 req/sec (with key)
- **Specialization**: Computer science, neuroscience, biomedical
- **Key Features**:
  - AI-generated paper summaries
  - Influential citations
  - Citation context
  - Author impact metrics
  - Batch lookup support

### 4. DOI.org
- **Website**: https://www.doi.org/
- **Description**: DOI resolution service for content negotiation
- **API Key**: Not required
- **Rate Limits**: ~2 req/sec recommended
- **Specialization**: DOI metadata resolution
- **Key Features**:
  - Metadata from publishers
  - Content negotiation
  - Multiple format support

### 5. PubMed
- **Website**: https://pubmed.ncbi.nlm.nih.gov/
- **Description**: NCBI's database of biomedical and life sciences literature
- **API Key**: Optional (10 req/sec with key vs 3 req/sec without)
- **Rate Limits**: 3 req/sec (without key), 10 req/sec (with key)
- **Specialization**: Biomedical, life sciences, clinical research
- **Key Features**:
  - 36+ million citations
  - MeSH terms (Medical Subject Headings)
  - Clinical trials
  - PubMed Central full-text links
  - Author affiliations
  - Grant information
- **Registration**: Get API key at https://www.ncbi.nlm.nih.gov/account/

### 6. arXiv
- **Website**: https://arxiv.org/
- **Description**: Preprint repository for physics, mathematics, CS, and more
- **API Key**: Not required
- **Rate Limits**: 1 request per 3 seconds recommended
- **Specialization**: Preprints in physics, math, CS, quantitative biology/finance
- **Key Features**:
  - Free full-text access
  - Latest research (preprints)
  - LaTeX source available
  - Version history
  - Category classification
  - All papers are open access
- **Note**: No DOI-based search; use arXiv ID for direct lookup

### 7. CORE
- **Website**: https://core.ac.uk/
- **Description**: World's largest collection of open access research papers
- **API Key**: Required (free registration)
- **Rate Limits**: 10,000 requests/day (free tier)
- **Specialization**: Open access papers from repositories and journals
- **Key Features**:
  - 300+ million papers
  - Full-text search
  - Repository aggregation
  - Download links
  - All papers are open access
- **Registration**: Get API key at https://core.ac.uk/services/api

### 8. Unpaywall
- **Website**: https://unpaywall.org/
- **Description**: Database of free scholarly articles, finds legal open access versions
- **API Key**: Not required (email required)
- **Rate Limits**: 100,000 requests/day
- **Specialization**: Finding open access versions of paywalled papers
- **Key Features**:
  - Legal OA link finding
  - Publisher policies
  - Repository copies
  - Best OA location
  - OA status tracking
- **Note**: Primarily DOI-based lookup, not full-text search
- **Best Use**: Check if a specific DOI has an open access version

### 9. DBLP
- **Website**: https://dblp.org/
- **Description**: Computer science bibliography
- **API Key**: Not required
- **Rate Limits**: Be respectful, ~2 req/sec recommended
- **Specialization**: Computer science publications
- **Key Features**:
  - Comprehensive CS coverage
  - Conference proceedings
  - Journal articles
  - Author pages
  - Venue information
  - Clean bibliographic data
- **Best Use**: Computer science papers, especially conferences

## Database Selection Guide

### By Research Domain

#### Biomedical & Life Sciences
- **Primary**: PubMed
- **Secondary**: OpenAlex, CORE
- **Open Access**: Unpaywall, CORE

#### Computer Science
- **Primary**: DBLP, Semantic Scholar
- **Secondary**: arXiv (for preprints), OpenAlex
- **Conferences**: DBLP

#### Physics & Mathematics
- **Primary**: arXiv
- **Secondary**: OpenAlex, CORE

#### General Academic
- **Primary**: OpenAlex, CrossRef
- **Secondary**: Semantic Scholar, CORE

### By Use Case

#### Finding Open Access PDFs
1. Unpaywall (DOI-based)
2. CORE
3. arXiv (preprints)
4. OpenAlex (OA status)

#### Comprehensive Metadata
1. OpenAlex
2. CrossRef
3. Semantic Scholar

#### Latest Research / Preprints
1. arXiv
2. OpenAlex

#### Citation Analysis
1. Semantic Scholar
2. OpenAlex
3. CrossRef

#### Domain-Specific Search
- **Biomedical**: PubMed → OpenAlex → CORE
- **Computer Science**: DBLP → Semantic Scholar → arXiv
- **Physics/Math**: arXiv → OpenAlex

## Rate Limiting Summary

| Database         | Default Limit | With API Key | Notes                    |
| ---------------- | ------------- | ------------ | ------------------------ |
| CrossRef         | ~50/sec       | N/A          | Higher with polite pool  |
| OpenAlex         | ~10/sec       | Higher       | Need polite pool (email) |
| Semantic Scholar | ~1/sec        | ~10/sec      | API key recommended      |
| DOI.org          | ~2/sec        | N/A          | No official limit        |
| PubMed           | 3/sec         | 10/sec       | Email recommended        |
| arXiv            | ~0.33/sec     | N/A          | 1 per 3 seconds          |
| CORE             | ~2/sec        | N/A          | 10k/day limit            |
| Unpaywall        | ~5/sec        | N/A          | 100k/day limit           |
| DBLP             | ~2/sec        | N/A          | No official limit        |

## API Key Requirements

### Required
- **CORE**: Must register at https://core.ac.uk/services/api

### Recommended
- **Semantic Scholar**: Register at https://www.semanticscholar.org/product/api
- **PubMed**: Register at https://www.ncbi.nlm.nih.gov/account/
- **OpenAlex**: Premium tier at https://openalex.org/pricing

### Optional
- **CrossRef**: Plus service available
- **DOI.org**: Not required
- **arXiv**: Not available
- **Unpaywall**: Not available (email required)
- **DBLP**: Not available

## Email Requirements

Many APIs request an email address for polite pool access or tracking:

- **Required**: Unpaywall
- **Recommended**: OpenAlex, PubMed, CrossRef
- **Optional**: Others

Configure email in your config:
```yaml
email: your.email@example.com
```

## Multi-Database Search Strategies

### Sequential Mode (Default)
Try databases in order until one succeeds:
```python
client = UnifiedSearchClient(
    databases=["pubmed", "openalex", "crossref"],
    fallback_mode="sequential"
)
```

### Parallel Mode (Maximum Coverage)
Query all databases simultaneously and merge results:
```python
client = UnifiedSearchClient(
    databases=["pubmed", "arxiv", "core", "openalex"],
    fallback_mode="parallel"
)
```

### First-Only Mode (Fastest)
Use only the first enabled database:
```python
client = UnifiedSearchClient(
    databases=["dblp"],
    fallback_mode="first"
)
```

## Field Coverage by Database

| Field     | CrossRef | OpenAlex | Sem. Scholar | DOI | PubMed | arXiv | CORE | Unpaywall | DBLP |
| --------- | -------- | -------- | ------------ | --- | ------ | ----- | ---- | --------- | ---- |
| Title     | ✓        | ✓        | ✓            | ✓   | ✓      | ✓     | ✓    | ✓         | ✓    |
| Authors   | ✓        | ✓        | ✓            | ✓   | ✓      | ✓     | ✓    | ✓         | ✓    |
| Abstract  | ✓        | ✓        | ✓            | ✗   | ✓      | ✓     | ✓    | ✗         | ✗    |
| Year      | ✓        | ✓        | ✓            | ✓   | ✓      | ✓     | ✓    | ✓         | ✓    |
| DOI       | ✓        | ✓        | ✓            | ✓   | ✓      | ~     | ✓    | ✓         | ✓    |
| Citations | ✓        | ✓        | ✓            | ✗   | ✗      | ✗     | ✗    | ✗         | ✗    |
| Keywords  | ~        | ✓        | ✓            | ✗   | ✓      | ✓     | ✓    | ✗         | ✗    |
| PDF URL   | ~        | ✓        | ✓            | ✗   | ✗      | ✓     | ✓    | ✓         | ~    |
| OA Status | ~        | ✓        | ~            | ✗   | ✗      | ✓     | ✓    | ✓         | ✗    |

Legend: ✓ = Usually available, ~ = Sometimes available, ✗ = Rarely/never available

## Examples

### Biomedical Research
```python
from paperseek import UnifiedSearchClient

client = UnifiedSearchClient(databases=["pubmed", "openalex", "core"])
results = client.search(
    title="cancer immunotherapy",
    year_range=(2020, 2024),
    max_results=50
)
```

### Computer Science
```python
client = UnifiedSearchClient(databases=["dblp", "semantic_scholar", "arxiv"])
results = client.search(
    venue="NeurIPS",
    year=2023,
    author="Hinton",
    max_results=20
)
```

### Finding Open Access Papers
```python
# First search for papers
client = UnifiedSearchClient(databases=["openalex"])
results = client.search(title="climate change", max_results=100)

# Then check for OA versions using DOIs
unpaywall = UnifiedSearchClient(databases=["unpaywall"])
for paper in results.papers:
    if paper.doi:
        oa_paper = unpaywall.get_by_doi(paper.doi)
        if oa_paper and oa_paper.is_open_access:
            print(f"Open access: {oa_paper.pdf_url}")
```
