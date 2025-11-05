# Data Models

Pydantic models for papers and search results.

## Paper

::: paperseek.core.models.Paper
    options:
      show_root_heading: true
      show_source: false
      members:
        - doi
        - pmid
        - arxiv_id
        - title
        - authors
        - year
        - venue
        - abstract
        - keywords
        - url
        - pdf_url
        - citation_count
        - references
        - source_database
        - retrieved_at
        - get_available_fields
        - to_dict
        - to_bibtex

## Author

::: paperseek.core.models.Author
    options:
      show_root_heading: true
      show_source: false

## SearchResult

::: paperseek.core.models.SearchResult
    options:
      show_root_heading: true
      show_source: false
      members:
        - papers
        - total_results
        - databases_queried
        - __len__
        - __getitem__
        - add_paper
        - extend
        - filter_by_required_fields
        - get_field_statistics
        - to_csv
        - to_json
        - to_jsonl
        - to_bibtex

## SearchFilters

::: paperseek.core.models.SearchFilters
    options:
      show_root_heading: true
      show_source: false
