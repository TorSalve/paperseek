"""
Example demonstrating streaming exports for large datasets.

This is useful when dealing with thousands of papers that might
not fit comfortably in memory.
"""

from paperseek import UnifiedSearchClient
from paperseek.exporters.csv_exporter import StreamingCSVExporter
from paperseek.exporters.json_exporter import StreamingJSONLExporter
from paperseek.exporters.bibtex_exporter import StreamingBibTeXExporter


def main():
    """Main streaming example."""

    print("=" * 60)
    print("Streaming Export Example")
    print("=" * 60)

    # Initialize client
    client = UnifiedSearchClient(databases=["openalex", "crossref"], fallback_mode="parallel")

    # Example 1: Stream to CSV
    print("\nExample 1: Streaming CSV export")
    print("-" * 60)

    venues = ["ICML", "NeurIPS", "ICLR", "CVPR", "ACL"]
    years = range(2020, 2024)

    total_papers = 0

    with StreamingCSVExporter("large_ml_dataset.csv") as csv_exporter:
        for venue in venues:
            for year in years:
                print(f"Fetching {venue} {year}...")

                try:
                    results = client.search(venue=venue, year=year, max_results=100)

                    csv_exporter.write_papers(results.papers)
                    total_papers += len(results)

                    print(f"  Added {len(results)} papers (total: {total_papers})")

                except Exception as e:
                    print(f"  Error: {e}")
                    continue

    print(f"\nTotal papers exported to CSV: {total_papers}")

    # Example 2: Stream to JSONL
    print("\n" + "=" * 60)
    print("Example 2: Streaming JSONL export")
    print("-" * 60)

    total_papers = 0

    with StreamingJSONLExporter("large_ml_dataset.jsonl") as jsonl_exporter:
        for venue in ["ICML", "NeurIPS"]:
            for year in [2022, 2023]:
                print(f"Fetching {venue} {year}...")

                try:
                    results = client.search(venue=venue, year=year, max_results=100)

                    jsonl_exporter.write_papers(results.papers, include_raw=False)
                    total_papers += len(results)

                    print(f"  Added {len(results)} papers")

                except Exception as e:
                    print(f"  Error: {e}")
                    continue

    print(f"\nTotal papers exported to JSONL: {total_papers}")

    # Example 3: Stream to BibTeX
    print("\n" + "=" * 60)
    print("Example 3: Streaming BibTeX export")
    print("-" * 60)

    total_papers = 0

    with StreamingBibTeXExporter("large_ml_dataset.bib") as bib_exporter:
        for author in ["Yann LeCun", "Geoffrey Hinton", "Yoshua Bengio"]:
            print(f"Fetching papers by {author}...")

            try:
                results = client.search(author=author, year_range=(2015, 2023), max_results=50)

                bib_exporter.write_papers(results.papers)
                total_papers += len(results)

                print(f"  Added {len(results)} papers")

            except Exception as e:
                print(f"  Error: {e}")
                continue

    print(f"\nTotal papers exported to BibTeX: {total_papers}")

    # Example 4: Memory-efficient processing
    print("\n" + "=" * 60)
    print("Example 4: Process and filter while streaming")
    print("-" * 60)

    # Only export papers with abstracts and high citations
    with StreamingCSVExporter("high_impact_papers.csv") as csv_exporter:
        venues = ["ICML", "NeurIPS", "CVPR"]
        total_papers = 0
        filtered_papers = 0

        for venue in venues:
            for year in range(2018, 2024):
                print(f"Processing {venue} {year}...")

                try:
                    results = client.search(venue=venue, year=year, max_results=200)

                    total_papers += len(results)

                    # Filter for high-impact papers
                    for paper in results.papers:
                        # Only include papers with abstract and 50+ citations
                        if paper.abstract and paper.citation_count and paper.citation_count >= 50:
                            csv_exporter.write_paper(paper)
                            filtered_papers += 1

                    print(f"  Total: {len(results)}, High-impact: {filtered_papers}")

                except Exception as e:
                    print(f"  Error: {e}")
                    continue

        print(f"\nProcessed {total_papers} papers")
        print(f"Exported {filtered_papers} high-impact papers")

    # Example 5: Custom column selection for CSV streaming
    print("\n" + "=" * 60)
    print("Example 5: Custom columns in streaming CSV")
    print("-" * 60)

    # Create custom columns
    custom_columns = ["title", "authors", "year", "citation_count", "doi", "venue"]

    with StreamingCSVExporter("custom_columns.csv", columns=custom_columns) as exporter:
        results = client.search(venue="ICML", year=2023, max_results=50)
        exporter.write_papers(results.papers)
        print(f"Exported {len(results)} papers with custom columns")

    # Clean up
    client.close()

    print("\n" + "=" * 60)
    print("Streaming examples completed!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - large_ml_dataset.csv")
    print("  - large_ml_dataset.jsonl")
    print("  - large_ml_dataset.bib")
    print("  - high_impact_papers.csv")
    print("  - custom_columns.csv")


if __name__ == "__main__":
    main()
