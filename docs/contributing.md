# Contributing to PaperSeek

Thank you for considering contributing to PaperSeek! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions professional

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/TorSalve/paperseek.git
   cd paperseek
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/TorSalve/paperseek.git
   ```

## Development Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Set up pre-commit hooks** (optional):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/TorSalve/paperseek/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Relevant code snippets or error messages

### Suggesting Features

1. Check existing [Issues](https://github.com/TorSalve/paperseek/issues) and [Pull Requests](https://github.com/TorSalve/paperseek/pulls)
2. Create a new issue describing:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives you've considered
   - Example usage

### Adding New Database Clients

To add support for a new academic database:

1. **Create a new client file** in `src/paperseek/clients/`:
   ```python
   from ..core.base import DatabaseClient
   from ..core.models import Paper, SearchFilters, SearchResult
   
   class NewDatabaseClient(DatabaseClient):
       BASE_URL = "https://api.newdatabase.org"
       
       @property
       def database_name(self) -> str:
           return "newdatabase"
       
       def search(self, filters: SearchFilters) -> SearchResult:
           # Implement search logic
           pass
       
       def get_by_doi(self, doi: str) -> Optional[Paper]:
           # Implement DOI lookup
           pass
       
       def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
           # Normalize API response to Paper model
           pass
   ```

2. **Add configuration** in `core/config.py`:
   ```python
   newdatabase: DatabaseConfig = Field(default_factory=DatabaseConfig)
   ```

3. **Register the client** in `core/unified_client.py`:
   ```python
   available_clients = {
       # ... existing clients
       "newdatabase": NewDatabaseClient,
   }
   ```

4. **Add tests** in `tests/test_newdatabase.py`

5. **Update documentation** in README.md

### Improving Documentation

- Fix typos or unclear explanations
- Add examples for common use cases
- Improve docstrings
- Update README.md with new features

## Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

- Line length: 100 characters (not 79)
- Use type hints for all functions
- Use Google-style docstrings

### Formatting

Format your code with Black:
```bash
black src/ tests/
```

### Linting

Check your code with Ruff:
```bash
ruff check src/ tests/
```

### Type Checking

Run mypy for type checking:
```bash
mypy src/
```

### Example Docstring

```python
def search(
    self,
    venue: Optional[str] = None,
    year: Optional[int] = None,
    max_results: int = 100
) -> SearchResult:
    """
    Search for academic papers.
    
    Args:
        venue: Conference or journal name
        year: Publication year
        max_results: Maximum number of results to return
    
    Returns:
        SearchResult object containing matching papers
    
    Raises:
        SearchError: If search fails
        ConfigurationError: If configuration is invalid
    
    Example:
        >>> client = UnifiedSearchClient()
        >>> results = client.search(venue='ICML', year=2023)
        >>> print(len(results))
        50
    """
    # Implementation
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_unified_client.py

# Run with coverage
pytest --cov=src/paperseek tests/

# Run with verbose output
pytest -v tests/
```

### Writing Tests

1. **Create test file** in `tests/` directory
2. **Use pytest conventions**:
   ```python
   def test_feature_name():
       # Arrange
       client = UnifiedSearchClient()
       
       # Act
       result = client.search(venue='ICML')
       
       # Assert
       assert len(result) > 0
   ```

3. **Mock external API calls**:
   ```python
   from unittest.mock import Mock, patch
   
   def test_with_mock():
       with patch('requests.get') as mock_get:
           mock_get.return_value.json.return_value = {'data': []}
           # Test code
   ```

4. **Test edge cases**:
   - Empty results
   - API errors
   - Invalid input
   - Rate limiting

### Test Coverage

- Aim for >80% code coverage
- Test all public methods
- Include integration tests
- Test error handling

## Documentation

### Docstrings

- Add docstrings to all public classes and methods
- Use Google-style format
- Include type hints
- Provide examples where helpful

### README Updates

When adding features:
1. Update the feature list
2. Add usage examples
3. Update API documentation
4. Note any breaking changes

### Example Scripts

Add examples in `examples/` directory:
```python
"""
Example: Using the new feature.

This example demonstrates how to use the newly added feature.
"""

from paperseek import UnifiedSearchClient

def main():
    # Your example code
    pass

if __name__ == "__main__":
    main()
```

## Pull Request Process

### Before Submitting

1. **Update from upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

4. **Run tests and checks**:
   ```bash
   pytest tests/
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

### Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add support for PubMed database

- Implement PubMedClient class
- Add PMID lookup functionality
- Include tests and documentation
- Update README with usage examples

Closes #123
```

Format:
- First line: Summary (50 chars max)
- Blank line
- Detailed description
- Reference related issues

### Submitting Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub:
   - Clear title
   - Describe your changes
   - Reference related issues
   - List breaking changes (if any)

3. **Pull Request Checklist**:
   - [ ] Tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No merge conflicts
   - [ ] Changes are focused (one feature/fix per PR)

4. **Respond to feedback**:
   - Address review comments
   - Push updates to your branch
   - Be open to suggestions

### After Merge

1. **Delete your branch**:
   ```bash
   git branch -d feature/your-feature-name
   ```

2. **Update your fork**:
   ```bash
   git checkout main
   git pull upstream main
   git push origin main
   ```

## Areas for Contribution

### High Priority

- [x] Add support for more databases (PubMed, arXiv, etc.)
- [x] Improve test coverage
- [ ] Add CLI tool enhancements
- [ ] Performance optimizations

### Medium Priority

- [ ] Add more export formats (RIS, EndNote)
- [ ] Implement caching mechanism
- [ ] Add progress bars for long operations
- [ ] Improve error messages

### Low Priority

- [ ] Add visualization tools
- [ ] Create web interface
- [ ] Add more examples
- [ ] Improve documentation

## Questions?

- Open an [issue](https://github.com/TorSalve/paperseek/issues)
- Check existing [discussions](https://github.com/TorSalve/paperseek/discussions)
- Email: torsalve@di.ku.dk

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Thank you for contributing to PaperSeek! Your contributions help make academic research more accessible to everyone.

---

**Last Updated:** 2025-11-05
