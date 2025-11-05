"""
Advanced usage example showing configuration and filtering.
"""

from paperseek import UnifiedSearchClient
from paperseek.core.config import AcademicSearchConfig, DatabaseConfig


def main():
    """Advanced usage examples."""

    # Example 1: Custom configuration from dictionary
    print("=" * 60)
    print("Example 1: Custom configuration")
    print("=" * 60)

    config_dict = {
        "email": "researcher@university.edu",
        "log_level": "DEBUG",
        "fallback_mode": "parallel",
        "crossref": {"enabled": True, "rate_limit_per_second": 2.0},
        "openalex": {"enabled": True, "rate_limit_per_second": 3.0},
        "semantic_scholar": {"enabled": False},  # Disable this database
    }

    client = UnifiedSearchClient(config_dict=config_dict)
    print(f"Initialized client with databases: {list(client.clients.keys())}")

    # Example 2: Parallel search across multiple databases
    print("\n" + "=" * 60)
    print("Example 2: Parallel search")
    print("=" * 60)

    results = client.search(title="deep learning", year_range=(2020, 2023), max_results=20)

    print(f"Found {len(results)} papers from {len(results.databases_queried)} databases")
    print(f"Databases: {', '.join(results.databases_queried)}")

    # Example 3: Year range search
    print("\n" + "=" * 60)
    print("Example 3: Year range search")
    print("=" * 60)

    results = client.search(
        venue="CVPR", year_range=(2020, 2023), required_fields=["abstract"], max_results=100
    )

    print(f"Found {len(results)} CVPR papers from 2020-2023 with abstracts")

    # Group by year
    by_year = {}
    for paper in results.papers:
        year = paper.year or "Unknown"
        by_year[year] = by_year.get(year, 0) + 1

    print("\nPapers by year:")
    for year in sorted(by_year.keys()):
        print(f"  {year}: {by_year[year]} papers")

    # Analyze field coverage
    print("\n--- Analyzing 5 papers with most complete metadata ---")
    for paper in results.papers[:5]:
        available = paper.get_available_fields()
        print(f"\n{paper.title[:60]}...")
        print(f"  Fields available: {len(available)}")
        print(f"  Has abstract: {paper.abstract is not None}")
        print(f"  Has citations: {paper.citation_count is not None}")

    # Example 5: Using SearchFilters directly
    print("\n" + "=" * 60)
    print("Example 5: Using SearchFilters")
    print("=" * 60)

    from paperseek.core.models import SearchFilters

    filters = SearchFilters(
        venue="ACL",
        year_start=2020,
        year_end=2023,
        required_fields=["abstract", "doi"],
        max_results=50,
    )

    results = client.search_with_filters(filters)
    print(f"Found {len(results)} ACL papers with abstracts and DOIs")

    # Example 6: Field coverage analysis
    print("\n" + "=" * 60)
    print("Example 6: Field coverage analysis")
    print("=" * 60)

    print(results.get_field_coverage_report())

    # Example 7: Export with custom columns
    print("\n" + "=" * 60)
    print("Example 7: Custom CSV export")
    print("=" * 60)

    from paperseek.exporters.csv_exporter import CSVExporter

    exporter = CSVExporter()
    custom_columns = ["title", "authors", "year", "doi", "citation_count", "venue"]
    exporter.export(results, "custom_export.csv", columns=custom_columns)
    print("Exported with custom columns to custom_export.csv")

    # Example 8: Context manager usage
    print("\n" + "=" * 60)
    print("Example 8: Context manager")
    print("=" * 60)

    with UnifiedSearchClient(databases=["openalex"]) as client:
        results = client.search(venue="ICLR", year=2023, max_results=10)
        print(f"Found {len(results)} ICLR 2023 papers")
    # Client automatically closed

    print("\n" + "=" * 60)
    print("Advanced examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
