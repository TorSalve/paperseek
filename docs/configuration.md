# Configuration Guide# General settings

email: your.email@example.com  # For polite API requests

This guide covers all configuration options for Academic Search Unified.user_agent: AcademicSearchUnified/0.1.0

log_level: INFO

## Configuration Methods# log_file: academic_search.log  # Optional: log to file



You can configure the client in three ways:# Default search settings

default_max_results: 100

### 1. Configuration File (Recommended)default_timeout: 30



Create a `config.yaml` file:# Fallback behavior

fallback_mode: sequential  # Options: sequential, parallel, first

```yamlfail_fast: false  # If true, stop on first error

# Database configuration

databases:# Database configurations

  crossref:crossref:

    enabled: true  enabled: true

    rate_limit_per_second: 1.0  # api_key: optional_api_key  # Not required for CrossRef

    rate_limit_per_minute: 50  rate_limit_per_second: 1.0

    timeout: 30

  openalex:  max_retries: 3

    enabled: true  retry_delay: 1.0

    email: "your.email@example.com"  # Polite requests

    rate_limit_per_second: 10.0openalex:

    enabled: true

  semantic_scholar:  # api_key: your_openalex_api_key  # Optional: For Premium users only

    enabled: true  # Email is automatically added via mailto parameter for polite pool access

    api_key: "your_api_key_here"  # Optional but recommended  # Free tier with polite pool: ~10 req/sec, Premium tier: higher limits + special filters

    rate_limit_per_second: 1.0  rate_limit_per_second: 5.0  # Conservative for polite pool (10/sec limit)

  timeout: 30

# Global settings  max_retries: 3

fallback_mode: "sequential"  # Options: sequential, parallel, first_only  retry_delay: 1.0

default_max_results: 100

deduplication: truesemantic_scholar:

```  enabled: true

  api_key: your_semantic_scholar_api_key  # Recommended for higher limits

Load the configuration:  rate_limit_per_second: 1.0  # Without API key: ~1/sec, with key: ~10/sec

  rate_limit_per_minute: 100

```python  timeout: 30

from paperseek import UnifiedSearchClient  max_retries: 3

  retry_delay: 1.0

client = UnifiedSearchClient(config_path="config.yaml")

```doi:

  enabled: true

### 2. Environment Variables  rate_limit_per_second: 2.0

  timeout: 30

Create a `.env` file:  max_retries: 3

  retry_delay: 1.0

```bash

# API Keyspubmed:

SEMANTIC_SCHOLAR_API_KEY=your_s2_api_key  enabled: true

CORE_API_KEY=your_core_api_key  # api_key: your_ncbi_api_key  # Optional: For 10 req/sec (vs 3 req/sec without)

  # Email is recommended by NCBI for tracking usage

# Email addresses (for polite requests)  rate_limit_per_second: 2.5  # Conservative (3/sec without key, 10/sec with key)

OPENALEX_EMAIL=your.email@example.com  timeout: 30

PUBMED_EMAIL=your.email@example.com  max_retries: 3

UNPAYWALL_EMAIL=your.email@example.com  retry_delay: 1.0

```

arxiv:

The client will automatically load these when initialized.  enabled: true

  # No API key required

### 3. Config Dictionary  # Rate limiting: 1 request per 3 seconds recommended by arXiv

  rate_limit_per_second: 0.33  # ~1 request per 3 seconds

Pass configuration directly to the client:  timeout: 30

  max_retries: 3

```python  retry_delay: 1.0

config = {

    "crossref": {core:

        "enabled": True,  enabled: true

        "rate_limit_per_second": 1.0  api_key: your_core_api_key  # Required - register at https://core.ac.uk/services/api

    },  # Free tier: 10,000 requests/day

    "openalex": {  rate_limit_per_second: 2.0

        "enabled": True,  timeout: 30

        "email": "your.email@example.com"  max_retries: 3

    }  retry_delay: 1.0

}

unpaywall:

client = UnifiedSearchClient(  enabled: true

    databases=["crossref", "openalex"],  # No API key required, but email is required

    config_dict=config  # Free for non-commercial use - 100,000 requests/day

)  rate_limit_per_second: 5.0

```  timeout: 30

  max_retries: 3

See the [example configuration file](https://github.com/TorSalve/paperseek/blob/main/config.yaml.example) for a complete reference.  retry_delay: 1.0



For detailed information about each database, see the [Database Overview](databases.md).dblp:

  enabled: true
  # No API key required
  # Be respectful with rate limiting
  rate_limit_per_second: 2.0
  timeout: 30
  max_retries: 3
  retry_delay: 1.0
