# Installation

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Basic Installation

Install the package using pip:

```bash
pip install paperseek
```

## Development Installation

To install for development with all dev dependencies:

```bash
# Clone the repository
git clone https://github.com/TorSalve/paperseek.git
cd paperseek

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

Or using requirements files:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Dependencies

### Core Dependencies

The package requires the following runtime dependencies:

- `requests>=2.31.0` - HTTP client for API requests
- `pydantic>=2.0.0` - Data validation and models
- `pydantic-settings>=2.0.0` - Settings management
- `pandas>=1.5.0` - Data manipulation for exports
- `pyyaml>=6.0` - YAML configuration support
- `pyrate-limiter>=3.0.0` - Rate limiting
- `python-dotenv>=1.0.0` - Environment variable management
- `bibtexparser>=1.4.0` - BibTeX export support

### Development Dependencies

For development, testing, and documentation:

- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.11.0` - Mocking support
- `black>=23.0.0` - Code formatting
- `mypy>=1.5.0` - Type checking
- `ruff>=0.0.290` - Linting
- `mkdocs>=1.5.0` - Documentation
- `mkdocs-material>=9.4.0` - Documentation theme

## Configuration

After installation, you may want to set up API keys for certain databases:

### Required API Keys

- **CORE**: Requires API key ([get one here](https://core.ac.uk/services/api))
- **Unpaywall**: Requires email address ([read more](https://unpaywall.org/products/api))

### Optional API Keys

Some databases work better with API keys but don't require them:

- **OpenAlex**: Works without key, but rate limits are higher with one
- **Semantic Scholar**: Works without key, but rate limits are higher with one

### Setting Up Keys

Create a `.env` file in your project root:

```bash
# Required for CORE
CORE_API_KEY=your_core_api_key

# Required for Unpaywall
UNPAYWALL_EMAIL=your.email@example.com

# Optional but recommended
OPENALEX_EMAIL=your.email@example.com
SEMANTIC_SCHOLAR_API_KEY=your_s2_api_key
```

Or create a `config.yaml` file:

```yaml
databases:
  core:
    enabled: true
    api_key: "your_core_api_key"
  
  unpaywall:
    enabled: true
    email: "your.email@example.com"
  
  openalex:
    enabled: true
    email: "your.email@example.com"
```

## Verifying Installation

Test your installation:

```python
from paperseek import UnifiedSearchClient

client = UnifiedSearchClient(databases=["crossref"])
results = client.search(query="test", max_results=1)
print(f"Installation successful! Found {len(results)} result(s)")
```

## Troubleshooting

### Import Errors

If you get import errors, ensure the package is installed:

```bash
pip list | grep paperseek
```

### API Key Issues

If you get authentication errors:

1. Check that your `.env` file is in the correct location
2. Verify your API keys are valid
3. Check that `python-dotenv` is installed

### Rate Limiting

If you hit rate limits:

1. Configure rate limiting in your config file
2. Use fewer databases simultaneously
3. Add delays between searches

For more help, see the [Contributing Guide](contributing.md) or open an issue on GitHub.
