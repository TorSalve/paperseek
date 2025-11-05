"""
Basic usage example for paperseek.

This example demonstrates how to search for papers and export results.
"""

from paperseek import UnifiedSearchClient


def main():
    """Main example function."""

    # Initialize client with default configuration
    # Will look for config.yaml or use environment variables
    client = UnifiedSearchClient(
        databases=["openalex", "crossref", "semantic_scholar"], fallback_mode="sequential"
    )

    # Example 1: Search by venue and year
    print("=" * 60)
    print("Example 1: Search for ICML 2023 papers")
    print("=" * 60)

    results = client.search(venue="ICML", year=2023, max_results=10)

    print(f"\nFound {len(results)} papers")
    print(f"Databases queried: {', '.join(results.databases_queried)}")

    # Show first few results
    for i, paper in enumerate(results.papers[:3], 1):
        print(f"\n{i}. {paper.title}")
        print(f"   Authors: {', '.join(a.name for a in paper.authors[:3])}")
        print(f"   Year: {paper.year}")
        print(f"   DOI: {paper.doi}")
        print(f"   Citations: {paper.citation_count}")

    # Example 2: Field statistics
    print("\n" + "=" * 60)
    print("Example 2: Field availability statistics")
    print("=" * 60)

    stats = results.field_statistics()
    for field_name in ["abstract", "doi", "citation_count", "keywords"]:
        if field_name in stats:
            print(f"{stats[field_name]}")

    # Example 3: Export to CSV
    print("\n" + "=" * 60)
    print("Example 3: Export results to CSV")
    print("=" * 60)

    results.to_csv("icml_2023_papers.csv", include_field_stats=True)
    print("Exported to icml_2023_papers.csv")
    print("Field statistics exported to icml_2023_papers_field_stats.csv")

    # Example 4: Search with required fields
    print("\n" + "=" * 60)
    print("Example 4: Search with required fields filter")
    print("=" * 60)

    results_with_abstract = client.search(
        venue="NeurIPS", year=2022, required_fields=["abstract", "citation_count"], max_results=50
    )

    print(f"Found {len(results_with_abstract)} papers with abstract and citation count")

    # Example 5: Lookup by DOI
    print("\n" + "=" * 60)
    print("Example 5: Lookup paper by DOI")
    print("=" * 60)

    paper = client.get_by_doi("10.48550/arXiv.1706.03762")  # "Attention is All You Need"
    if paper:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(a.name for a in paper.authors)}")
        print(f"Year: {paper.year}")
        print(f"Citations: {paper.citation_count}")
        print(f"Source: {paper.source_database}")

    # Example 6: Batch lookup
    print("\n" + "=" * 60)
    print("Example 6: Batch lookup by DOIs")
    print("=" * 60)

    dois = [
        "10.48550/arXiv.1706.03762",  # Attention is All You Need
        "10.48550/arXiv.1512.03385",  # ResNet
        "10.48550/arXiv.1409.1556",  # VGG
    ]

    batch_results = client.batch_lookup(dois, id_type="doi")
    print(f"Found {len(batch_results)} papers")

    for paper in batch_results.papers:
        print(f"- {paper.title} ({paper.year})")

    # Example 7: Export to different formats
    print("\n" + "=" * 60)
    print("Example 7: Export to multiple formats")
    print("=" * 60)

    batch_results.to_json("papers.json", pretty=True)
    print("Exported to papers.json")

    batch_results.to_jsonl("papers.jsonl")
    print("Exported to papers.jsonl")

    batch_results.to_bibtex("papers.bib")
    print("Exported to papers.bib")

    # Clean up
    client.close()
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
