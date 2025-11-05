"""
Example: Using different database clients for specialized searches.

This example demonstrates how to use specific database clients based on
your research domain and requirements.
"""

from paperseek import UnifiedSearchClient

# Example 1: Biomedical research using PubMed
print("=" * 80)
print("Example 1: Biomedical Research (PubMed)")
print("=" * 80)

client = UnifiedSearchClient(databases=["pubmed"])

results = client.search(title="COVID-19 vaccine", year_range=(2020, 2023), max_results=10)
print(f"Found {len(results.papers)} papers in PubMed")

if results.papers:
    paper = results.papers[0]
    print(f"\nFirst result:")
    print(f"  Title: {paper.title}")
    print(f"  PMID: {paper.source_id}")
    print(f"  Journal: {paper.journal}")
    print(f"  Year: {paper.year}")
    print(f"  Keywords: {', '.join(paper.keywords[:5]) if paper.keywords else 'N/A'}")

client.close()


# Example 2: Preprints from arXiv
print("\n" + "=" * 80)
print("Example 2: Physics/CS Preprints (arXiv)")
print("=" * 80)

client = UnifiedSearchClient(databases=["arxiv"])

results = client.search(title="transformer neural network", author="Vaswani", max_results=5)
print(f"Found {len(results.papers)} papers in arXiv")

if results.papers:
    paper = results.papers[0]
    print(f"\nFirst result:")
    print(f"  Title: {paper.title}")
    print(f"  arXiv ID: {paper.source_id}")
    print(f"  Year: {paper.year}")
    print(f"  PDF: {paper.pdf_url}")
    print(f"  Open Access: {paper.is_open_access}")

client.close()


# Example 3: Open Access papers from CORE
print("\n" + "=" * 80)
print("Example 3: Open Access Papers (CORE)")
print("=" * 80)

client = UnifiedSearchClient(databases=["core"])

results = client.search(title="machine learning education", year_range=(2022, 2025), max_results=5)
print(f"Found {len(results.papers)} open access papers in CORE")

for i, paper in enumerate(results.papers[:3], 1):
    print(f"\n{i}. {paper.title[:70]}...")
    print(f"   Year: {paper.year}")
    print(f"   PDF Available: {'Yes' if paper.pdf_url else 'No'}")

client.close()


# Example 4: Finding open access versions with Unpaywall
print("\n" + "=" * 80)
print("Example 4: Finding Open Access Versions (Unpaywall)")
print("=" * 80)

client = UnifiedSearchClient(databases=["unpaywall"])

# Unpaywall works best with DOI lookup
dois = ["10.1038/nature12373", "10.1126/science.1260419", "10.1038/s41586-021-03819-2"]

for doi in dois:
    paper = client.get_by_doi(doi)
    if paper:
        print(f"\nDOI: {doi}")
        print(f"  Title: {paper.title[:60]}...")
        print(f"  Open Access: {paper.is_open_access}")
        if paper.pdf_url:
            print(f"  PDF URL: {paper.pdf_url}")
        else:
            print(f"  PDF: Not available")

client.close()


# Example 5: Computer Science bibliography from DBLP
print("\n" + "=" * 80)
print("Example 5: Computer Science Papers (DBLP)")
print("=" * 80)

client = UnifiedSearchClient(databases=["dblp"])

results = client.search(venue="ICML", year=2023, max_results=10)
print(f"Found {len(results.papers)} papers from ICML 2023 in DBLP")

for i, paper in enumerate(results.papers[:5], 1):
    print(f"\n{i}. {paper.title[:70]}...")
    print(f"   Authors: {', '.join(a.name for a in paper.authors[:3])}")
    print(f"   Venue: {paper.conference or paper.journal}")

client.close()


# Example 6: Multi-database search for comprehensive coverage
print("\n" + "=" * 80)
print("Example 6: Multi-Database Search (All Databases)")
print("=" * 80)

# Use all databases in parallel mode for maximum coverage
client = UnifiedSearchClient(
    databases=["crossref", "openalex", "semantic_scholar", "pubmed", "arxiv", "core", "dblp"],
    fallback_mode="parallel",
)

results = client.search(
    title="deep learning", author="Hinton", year_range=(2015, 2020), max_results=5  # per database
)
print(f"\nTotal papers found: {len(results.papers)}")
print(f"Databases queried: {', '.join(results.databases_queried)}")

# Show field coverage statistics
stats = results.field_statistics()
print("\nField coverage across all databases:")
for field in ["abstract", "citation_count", "pdf_url", "keywords"]:
    if field in stats:
        print(f"  {stats[field]}")

# Show papers by database
by_database = {}
for paper in results.papers:
    db = paper.source_database
    by_database[db] = by_database.get(db, 0) + 1

print("\nPapers by database:")
for db, count in sorted(by_database.items()):
    print(f"  {db}: {count}")

client.close()


# Example 7: Domain-specific multi-database search
print("\n" + "=" * 80)
print("Example 7: Biomedical Search (PubMed + OpenAlex + CORE)")
print("=" * 80)

# For biomedical research, combine PubMed with open databases
client = UnifiedSearchClient(databases=["pubmed", "openalex", "core"], fallback_mode="parallel")

results = client.search(title="CRISPR gene editing", year_range=(2020, 2025), max_results=5)
print(f"Found {len(results.papers)} papers across biomedical databases")

# Filter for open access papers only
open_access_papers = [p for p in results.papers if p.is_open_access]
print(f"Open access papers: {len(open_access_papers)}/{len(results.papers)}")

# Export open access papers
if open_access_papers:
    print("\nSample open access papers:")
    for i, paper in enumerate(open_access_papers[:3], 1):
        print(f"\n{i}. {paper.title[:60]}...")
        print(f"   Source: {paper.source_database}")
        print(f"   Year: {paper.year}")
        if paper.pdf_url:
            print(f"   PDF: {paper.pdf_url}")

client.close()


print("\n" + "=" * 80)
print("Examples complete!")
print("=" * 80)
