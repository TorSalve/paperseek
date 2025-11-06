"""
Example: Search for all papers published

This example demonstrates how to search for papers from a specific conference
and year using PaperSeek. 

The script searches multiple databases and exports results to various formats.

"""

from paperseek import UnifiedSearchClient
from paperseek.core.models import SearchFilters
from paperseek.exporters.bibtex_exporter import BibTeXExporter
from paperseek.exporters.csv_exporter import CSVExporter
from paperseek.exporters.json_exporter import JSONExporter
from paperseek.utils.pdf_downloader import PDFDownloader
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

RESULTS_DIR = "./search_results"


def search(venue: str, year: int):
    
    print("=" * 70)
    print(f"Searching for {venue} {year} Conference Papers")
    print("=" * 70)
    print()
    
    # Initialize the unified search client with config that uses environment variables
    print("Initializing search client...")
    print("Loading API keys from .env file...")
    
    client = UnifiedSearchClient(
        # databases=["arxiv", "crossref", "dblp", "semantic_scholar", "openalex"]
        databases=["semantic_scholar"]
    )
    
    print(f"Enabled databases: {', '.join(client.clients.keys())}")
    print()
    
    # CHI 2025 conference search strategy:
    # Since CHI 2025 might not be fully indexed yet, we'll search broadly
    # and use multiple strategies

    print(f"Strategy 1: Searching by venue '{venue}' and year {year}...")
    filters = SearchFilters(
        venue=venue,
        year=year,
        max_results=100
    )
    
   
    results_strategy = client.search(filters=filters, mode="parallel")
    print(f"  Found {len(results_strategy.papers)} papers")
    
    # Combine and deduplicate results
    print("\nCombining and deduplicating results...")
    all_papers = []
    seen_dois = set()
    seen_titles = set()

    for results in [results_strategy]:
        for paper in results.papers:
            is_duplicate = False
            
            if paper.doi and paper.doi in seen_dois:
                is_duplicate = True
            elif paper.title.lower().strip() in seen_titles:
                is_duplicate = True
            
            if not is_duplicate:
                all_papers.append(paper)
                if paper.doi:
                    seen_dois.add(paper.doi)
                seen_titles.add(paper.title.lower().strip())
    
    # Create combined results
    from paperseek.core.models import SearchResult
    results = SearchResult(
        query_info={"venue": venue, "year": year,},
        databases_queried=list(client.clients.keys())
    )
    for paper in all_papers:
        results.add_paper(paper)

    print(f"Searching for papers from {venue} {year}...")
    print(f"  Combined unique papers: {len(results.papers)}")
    print(f"  Databases queried: {', '.join(results.databases_queried)}")
    print()
    
    # Perform the search
    try:
        print(f"✓ Search completed!")
        print(f"  Found {len(results.papers)} unique papers across all strategies")
        print(f"  Queried {len(results.databases_queried)} databases")
        print()
        
        # Display statistics
        print("-" * 70)
        print("Search Statistics:")
        print("-" * 70)
        
        if len(results.papers) == 0:
            print("  No papers found.")
            print(f"\n  Note: {venue} {year} may not be indexed yet in these databases,")
            print("  or the venue name format may differ.")
            return results
        
        # Papers by database
        db_counts = {}
        for paper in results.papers:
            db = paper.source_database
            db_counts[db] = db_counts.get(db, 0) + 1
        
        for db, count in sorted(db_counts.items()):
            print(f"  {db:20s}: {count:3d} papers")
        
        # Open access statistics
        open_access_count = sum(1 for p in results.papers if p.is_open_access)
        open_access_pct = 100 * open_access_count / len(results.papers) if results.papers else 0
        print(f"\n  Open Access Papers  : {open_access_count}/{len(results.papers)} ({open_access_pct:.1f}%)")
        
        # Papers with PDFs
        pdf_count = sum(1 for p in results.papers if p.pdf_url)
        pdf_pct = 100 * pdf_count / len(results.papers) if results.papers else 0
        print(f"  Papers with PDF URL : {pdf_count}/{len(results.papers)} ({pdf_pct:.1f}%)")
        
        # Papers with DOI
        doi_count = sum(1 for p in results.papers if p.doi)
        doi_pct = 100 * doi_count / len(results.papers) if results.papers else 0
        print(f"  Papers with DOI     : {doi_count}/{len(results.papers)} ({doi_pct:.1f}%)")
        
        # Papers with abstracts
        abstract_count = sum(1 for p in results.papers if p.abstract)
        abstract_pct = 100 * abstract_count / len(results.papers) if results.papers else 0
        print(f"  Papers with Abstract: {abstract_count}/{len(results.papers)} ({abstract_pct:.1f}%)")
        
        print()
        
        # Display sample papers
        print("-" * 70)
        print("Sample Papers (first 5):")
        print("-" * 70)
        
        for i, paper in enumerate(results.papers[:5], 1):
            print(f"\n{i}. {paper.title}")
            authors = ", ".join([a.name for a in paper.authors[:3]])
            if len(paper.authors) > 3:
                authors += f" et al. ({len(paper.authors)} authors)"
            print(f"   Authors: {authors}")
            print(f"   Year: {paper.year}")
            print(f"   Source: {paper.source_database}")
            if paper.doi:
                print(f"   DOI: {paper.doi}")
            if paper.url:
                print(f"   URL: {paper.url}")
            if paper.pdf_url:
                print(f"   PDF: {paper.pdf_url}")
            if paper.citation_count:
                print(f"   Citations: {paper.citation_count}")
        
        print()
        
        # Export results
        print("-" * 70)
        print("Exporting Results:")
        print("-" * 70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(RESULTS_DIR, f"{venue.lower()}_{year}_results")
        os.makedirs(output_dir, exist_ok=True)
        
        # Export to BibTeX
        bibtex_file = os.path.join(output_dir, f"{venue.lower()}_{year}_{timestamp}.bib")
        bibtex_exporter = BibTeXExporter()
        bibtex_exporter.export(results, bibtex_file)
        print(f"✓ BibTeX exported to: {bibtex_file}")
        
        # Export to CSV
        csv_file = os.path.join(output_dir, f"{venue.lower()}_{year}_{timestamp}.csv")
        csv_exporter = CSVExporter()
        csv_exporter.export(results, csv_file)
        print(f"✓ CSV exported to: {csv_file}")
        
        # Export to JSON
        json_file = os.path.join(output_dir, f"{venue.lower()}_{year}_{timestamp}.json")
        json_exporter = JSONExporter()
        json_exporter.export(results, json_file)
        print(f"✓ JSON exported to: {json_file}")
        
        print()
        
        # Optional: Download PDFs
        download_pdfs = input("Would you like to download available PDFs? (y/n): ").strip().lower()
        
        if download_pdfs == 'y':
            print()
            print("-" * 70)
            print("Downloading PDFs:")
            print("-" * 70)
            
            pdf_dir = os.path.join(output_dir, "pdfs")
            downloader = PDFDownloader(download_dir=pdf_dir)
            
            # Filter papers with PDF URLs
            papers_with_pdf = [p for p in results.papers if p.pdf_url]
            print(f"Found {len(papers_with_pdf)} papers with PDF URLs")
            print(f"Starting downloads...")
            print()
            
            # Download papers one by one (PDFDownloader doesn't have batch_download)
            success_count = 0
            for i, paper in enumerate(papers_with_pdf, 1):
                print(f"Downloading {i}/{len(papers_with_pdf)}: {paper.title[:60]}...")
                if downloader.download_paper(paper):
                    success_count += 1
            
            print(f"\n✓ Downloaded {success_count}/{len(papers_with_pdf)} PDFs")
            print(f"  PDFs saved to: {pdf_dir}")
        
        print()
        print("=" * 70)
        print("Search Complete!")
        print("=" * 70)
        print(f"Total papers found: {len(results.papers)}")
        print(f"Results saved to: {output_dir}/")
        print()
        
        return results
        
    except Exception as e:
        print(f"✗ Error during search: {e}")
        raise


def main():
    print("\nPaper Search Tool")
    print("=" * 70)
    print("\nThis tool will search for papers")
    print("across multiple academic databases.\n")
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_file):
        print("⚠️  WARNING: No .env file found!")
        print(f"   Expected location: {env_file}")
        print("\n   To use API keys (recommended for better results):")
        print("   1. Copy .env.example to .env")
        print("   2. Add your API keys")
        print("\n   Continuing without API keys (may have rate limits)...\n")
        input("Press Enter to continue...")
    else:
        print(f"✓ Found .env file at: {env_file}")
        print()
    
    results = search(venue="CHI", year=2019)
    
    return results


if __name__ == "__main__":
    main()
