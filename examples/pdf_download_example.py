"""
Example: Downloading PDFs from open access papers.

This example demonstrates how to use the PDF downloader to fetch
PDFs from various academic databases that provide open access links.
"""

from paperseek import UnifiedSearchClient
from paperseek.utils.pdf_downloader import PDFDownloader

# Example 1: Download arXiv papers
print("=" * 80)
print("Example 1: Downloading arXiv Papers")
print("=" * 80)

client = UnifiedSearchClient(databases=["arxiv"])

# Search for machine learning papers on arXiv
results = client.search(title="attention mechanism", author="Vaswani", max_results=5)

print(f"Found {len(results.papers)} papers")

# Initialize PDF downloader with conservative settings
with PDFDownloader(
    download_dir="./downloads/arxiv",
    rate_limit_seconds=3.0,  # Wait 3 seconds between downloads
    max_file_size_mb=50,
    email="your.email@example.com",
) as downloader:

    # Download PDFs
    downloaded = downloader.download_search_results(
        results, only_open_access=True, max_downloads=3  # Limit to 3 papers for demo
    )

    print(f"\nSuccessfully downloaded {len(downloaded)} PDFs:")
    for title, filepath in downloaded.items():
        print(f"  - {title[:60]}...")
        print(f"    → {filepath}")

    # Print statistics
    downloader.print_statistics()

client.close()


# Example 2: Download from multiple open access databases
print("\n" + "=" * 80)
print("Example 2: Download from Multiple OA Databases")
print("=" * 80)

# Search across arXiv, CORE, and OpenAlex for open access papers
client = UnifiedSearchClient(databases=["arxiv", "core", "openalex"], fallback_mode="parallel")

results = client.search(title="climate change modeling", year_range=(2022, 2023), max_results=10)

print(f"Found {len(results.papers)} papers across databases")

# Count papers with PDF URLs
papers_with_pdfs = [p for p in results.papers if p.pdf_url]
print(f"Papers with PDF URLs: {len(papers_with_pdfs)}")

# Download PDFs with very conservative rate limiting
with PDFDownloader(
    download_dir="./downloads/climate",
    rate_limit_seconds=5.0,  # Extra conservative: 5 seconds between downloads
    max_file_size_mb=30,
    email="your.email@example.com",
    overwrite=False,  # Skip already downloaded files
) as downloader:

    downloaded = downloader.download_search_results(results, only_open_access=True, max_downloads=5)

    print(f"\nDownloaded {len(downloaded)} PDFs")
    downloader.print_statistics()

client.close()


# Example 3: Download specific papers by DOI using Unpaywall
print("\n" + "=" * 80)
print("Example 3: Finding and Downloading OA Versions via Unpaywall")
print("=" * 80)

# First, search for papers
client_search = UnifiedSearchClient(databases=["openalex"])
results = client_search.search(title="neural networks", year=2020, max_results=20)

print(f"Found {len(results.papers)} papers")

# Now check for OA versions using Unpaywall
client_unpaywall = UnifiedSearchClient(databases=["unpaywall"])

oa_papers = []
for paper in results.papers:
    if paper.doi:
        # Check Unpaywall for OA version
        oa_paper = client_unpaywall.get_by_doi(paper.doi)
        if oa_paper and oa_paper.is_open_access and oa_paper.pdf_url:
            oa_papers.append(oa_paper)
            print(f"Found OA version: {paper.title[:60]}...")

print(f"\nFound {len(oa_papers)} papers with OA PDFs via Unpaywall")

# Download the OA PDFs
if oa_papers:
    with PDFDownloader(
        download_dir="./downloads/unpaywall_oa",
        rate_limit_seconds=2.0,
        email="your.email@example.com",
    ) as downloader:

        downloaded = downloader.download_papers(oa_papers, max_downloads=5)

        print(f"\nDownloaded {len(downloaded)} OA PDFs")
        downloader.print_statistics()

client_search.close()
client_unpaywall.close()


# Example 4: Download PubMed Central papers (if available)
print("\n" + "=" * 80)
print("Example 4: Biomedical Papers with Open Access")
print("=" * 80)

# Search PubMed and CORE for biomedical papers
client = UnifiedSearchClient(databases=["pubmed", "core"], fallback_mode="parallel")

results = client.search(title="cancer immunotherapy", year_range=(2022, 2023), max_results=15)

print(f"Found {len(results.papers)} biomedical papers")

# Filter for papers with PDF URLs
papers_with_pdfs = [p for p in results.papers if p.pdf_url]
print(f"Papers with PDF access: {len(papers_with_pdfs)}")

# Download with conservative settings
with PDFDownloader(
    download_dir="./downloads/biomedical",
    rate_limit_seconds=4.0,  # Very conservative for PubMed
    max_file_size_mb=50,
    email="your.email@example.com",
) as downloader:

    downloaded = downloader.download_papers(papers_with_pdfs, max_downloads=5)

    if downloaded:
        print(f"\nSuccessfully downloaded {len(downloaded)} PDFs")
        for title, path in list(downloaded.items())[:3]:
            print(f"  - {path.name}")

    downloader.print_statistics()

client.close()


# Example 5: Organize downloads by database
print("\n" + "=" * 80)
print("Example 5: Organizing Downloads by Source Database")
print("=" * 80)

client = UnifiedSearchClient(databases=["arxiv", "core", "dblp"], fallback_mode="parallel")

results = client.search(title="deep learning computer vision", year=2023, max_results=15)

print(f"Found {len(results.papers)} papers")

# Download and organize by source database
with PDFDownloader(
    download_dir="./downloads",
    rate_limit_seconds=3.0,
    email="your.email@example.com",
) as downloader:

    # Group papers by database
    by_database = {}
    for paper in results.papers:
        if paper.pdf_url:
            db = paper.source_database
            if db not in by_database:
                by_database[db] = []
            by_database[db].append(paper)

    # Download each database's papers to separate subdirectory
    all_downloaded = {}
    for database, papers in by_database.items():
        print(f"\nDownloading {len(papers)} papers from {database}...")
        downloaded = downloader.download_papers(
            papers, subdirectory=database, max_downloads=3  # Limit per database
        )
        all_downloaded.update(downloaded)

    print(f"\nTotal downloaded: {len(all_downloaded)} PDFs")
    downloader.print_statistics()

client.close()


# Example 6: Advanced - Download with custom filtering
print("\n" + "=" * 80)
print("Example 6: Download with Custom Filtering")
print("=" * 80)

client = UnifiedSearchClient(databases=["openalex", "core"])

results = client.search(title="renewable energy", year_range=(2021, 2023), max_results=30)

print(f"Found {len(results.papers)} papers")

# Custom filter: Only papers with abstracts and high citation count
filtered_papers = [
    p for p in results.papers if p.pdf_url and p.abstract and (p.citation_count or 0) > 10
]

print(f"Filtered to {len(filtered_papers)} papers with abstracts and 10+ citations")

with PDFDownloader(
    download_dir="./downloads/renewable_energy",
    rate_limit_seconds=3.0,
    max_file_size_mb=40,
    email="your.email@example.com",
) as downloader:

    downloaded = downloader.download_papers(filtered_papers, max_downloads=5)

    print(f"\nDownloaded {len(downloaded)} PDFs")

    # List downloaded files with metadata
    for title, filepath in downloaded.items():
        paper = next(p for p in filtered_papers if p.title == title)
        print(f"\n{filepath.name}:")
        print(f"  Citations: {paper.citation_count}")
        print(f"  Year: {paper.year}")
        print(f"  Database: {paper.source_database}")

    downloader.print_statistics()

client.close()


print("\n" + "=" * 80)
print("PDF Download Examples Complete!")
print("=" * 80)
print("\nTips for polite downloading:")
print("  - Use rate_limit_seconds >= 3.0 for most sources")
print("  - Set max_downloads to limit batch operations")
print("  - Always provide an email address")
print("  - Use only_open_access=True to respect copyright")
print("  - Set overwrite=False to avoid re-downloading")
print("  - Monitor download statistics")
print("=" * 80)
