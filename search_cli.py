#!/usr/bin/env python3
"""
Simple CLI tool for academic search.

Usage:
    python search_cli.py --venue ICML --year 2023 --max-results 10
    python search_cli.py --doi "10.48550/arXiv.1706.03762"
    python search_cli.py --author "Geoffrey Hinton" --year-start 2015 --year-end 2023
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from paperseek import UnifiedSearchClient
from paperseek.utils.logging import setup_logging


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Search academic databases from the command line")

    # Search parameters
    parser.add_argument("--venue", help="Conference or journal name")
    parser.add_argument("--year", type=int, help="Publication year")
    parser.add_argument("--year-start", type=int, help="Start year for range")
    parser.add_argument("--year-end", type=int, help="End year for range")
    parser.add_argument("--author", help="Author name")
    parser.add_argument("--title", help="Paper title")
    parser.add_argument("--doi", help="Digital Object Identifier")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum results (default: 10)")

    # Configuration
    parser.add_argument(
        "--databases",
        nargs="+",
        choices=["crossref", "openalex", "semantic_scholar", "doi"],
        help="Databases to search",
    )
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument(
        "--fallback-mode",
        choices=["sequential", "parallel", "first"],
        default="sequential",
        help="Fallback mode (default: sequential)",
    )

    # Output options
    parser.add_argument("--output", "-o", help="Output file (CSV, JSON, or BibTeX)")
    parser.add_argument(
        "--format",
        choices=["csv", "json", "jsonl", "bibtex"],
        help="Output format (auto-detected from filename)",
    )
    parser.add_argument("--stats", action="store_true", help="Show field statistics")

    # Other options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (errors only)")

    args = parser.parse_args()

    # Set up logging
    if args.quiet:
        log_level = "ERROR"
    elif args.verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"

    setup_logging(level=log_level)

    # Check if any search parameters provided
    if not any([args.venue, args.author, args.title, args.doi, args.year]):
        parser.error("At least one search parameter required")

    # Initialize client
    try:
        client = UnifiedSearchClient(
            databases=args.databases, fallback_mode=args.fallback_mode, config_file=args.config
        )
    except Exception as e:
        print(f"Error initializing client: {e}", file=sys.stderr)
        return 1

    # Build search parameters
    search_params = {"max_results": args.max_results}

    if args.venue:
        search_params["venue"] = args.venue
    if args.year:
        search_params["year"] = args.year
    if args.year_start or args.year_end:
        search_params["year_range"] = (args.year_start, args.year_end)
    if args.author:
        search_params["author"] = args.author
    if args.title:
        search_params["title"] = args.title
    if args.doi:
        search_params["doi"] = args.doi

    # Perform search
    try:
        print("Searching...", file=sys.stderr)
        results = client.search(**search_params)
        print(f"Found {len(results)} papers", file=sys.stderr)
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return 1
    finally:
        client.close()

    # Display results
    if not args.quiet:
        print("\nResults:")
        print("=" * 80)

        for i, paper in enumerate(results.papers[: args.max_results], 1):
            print(f"\n{i}. {paper.title}")
            if paper.authors:
                authors_str = ", ".join(a.name for a in paper.authors[:3])
                if len(paper.authors) > 3:
                    authors_str += f" et al. ({len(paper.authors)} total)"
                print(f"   Authors: {authors_str}")
            if paper.year:
                print(f"   Year: {paper.year}")
            if paper.venue:
                print(f"   Venue: {paper.venue}")
            if paper.doi:
                print(f"   DOI: {paper.doi}")
            if paper.citation_count is not None:
                print(f"   Citations: {paper.citation_count}")
            print(f"   Source: {paper.source_database}")

    # Show field statistics
    if args.stats:
        print("\n" + "=" * 80)
        print("Field Statistics:")
        print("=" * 80)
        print(results.get_field_coverage_report())

    # Export if output file specified
    if args.output:
        try:
            # Auto-detect format from extension
            output_path = Path(args.output)
            format_type = args.format or output_path.suffix.lstrip(".")

            print(f"\nExporting to {args.output} ({format_type})...", file=sys.stderr)

            if format_type == "csv":
                results.to_csv(args.output, include_field_stats=args.stats)
                if args.stats:
                    print(f"Also created field statistics file", file=sys.stderr)
            elif format_type == "json":
                results.to_json(args.output, pretty=True)
            elif format_type == "jsonl":
                results.to_jsonl(args.output)
            elif format_type in ["bib", "bibtex"]:
                results.to_bibtex(args.output)
            else:
                print(f"Unknown format: {format_type}", file=sys.stderr)
                return 1

            print(f"Exported {len(results)} papers to {args.output}", file=sys.stderr)

        except Exception as e:
            print(f"Export error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
