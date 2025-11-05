"""BibTeX exporter for search results."""

from pathlib import Path
from typing import Optional
import re

from ..core.models import SearchResult, Paper, Author
from ..core.exceptions import ExportError
from ..utils.logging import get_logger


class BibTeXExporter:
    """Export search results to BibTeX format."""

    def __init__(self):
        """Initialize BibTeX exporter."""
        self.logger = get_logger(self.__class__.__name__)

    def export(self, results: SearchResult, filename: str) -> None:
        """
        Export search results to BibTeX file.

        Args:
            results: SearchResult object
            filename: Output BibTeX file path

        Raises:
            ExportError: If export fails
        """
        try:
            self.logger.info(f"Exporting {len(results)} results to {filename}")

            # Create output directory if needed
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

            with open(filename, "w", encoding="utf-8") as f:
                for i, paper in enumerate(results.papers, 1):
                    entry = self._paper_to_bibtex(paper, entry_number=i)
                    f.write(entry)
                    f.write("\n\n")

            self.logger.info(f"Successfully exported to {filename}")

        except Exception as e:
            raise ExportError(f"Failed to export to BibTeX: {e}") from e

    def _paper_to_bibtex(self, paper: Paper, entry_number: int = 1) -> str:
        """
        Convert Paper object to BibTeX entry.

        Args:
            paper: Paper object
            entry_number: Entry number for citation key

        Returns:
            BibTeX entry as string
        """
        # Determine entry type
        entry_type = self._determine_entry_type(paper)

        # Generate citation key
        cite_key = self._generate_cite_key(paper, entry_number)

        # Build entry
        lines = [f"@{entry_type}{{{cite_key},"]

        # Add required and optional fields
        if paper.title:
            lines.append(f"  title = {{{self._escape_bibtex(paper.title)}}},")

        if paper.authors:
            author_str = " and ".join(
                self._format_author_bibtex(author) for author in paper.authors
            )
            lines.append(f"  author = {{{author_str}}},")

        if paper.year:
            lines.append(f"  year = {{{paper.year}}},")

        if paper.journal:
            lines.append(f"  journal = {{{self._escape_bibtex(paper.journal)}}},")

        if paper.conference:
            lines.append(f"  booktitle = {{{self._escape_bibtex(paper.conference)}}},")

        if paper.volume:
            lines.append(f"  volume = {{{paper.volume}}},")

        if paper.issue:
            lines.append(f"  number = {{{paper.issue}}},")

        if paper.pages:
            lines.append(f"  pages = {{{paper.pages}}},")

        if paper.publisher:
            lines.append(f"  publisher = {{{self._escape_bibtex(paper.publisher)}}},")

        if paper.doi:
            lines.append(f"  doi = {{{paper.doi}}},")

        if paper.url:
            lines.append(f"  url = {{{paper.url}}},")

        if paper.abstract:
            lines.append(f"  abstract = {{{self._escape_bibtex(paper.abstract)}}},")

        if paper.keywords:
            keywords_str = ", ".join(paper.keywords)
            lines.append(f"  keywords = {{{keywords_str}}},")

        # Remove trailing comma from last field
        if lines[-1].endswith(","):
            lines[-1] = lines[-1][:-1]

        lines.append("}")

        return "\n".join(lines)

    def _determine_entry_type(self, paper: Paper) -> str:
        """Determine BibTeX entry type based on paper metadata."""
        if paper.conference:
            return "inproceedings"
        elif paper.journal:
            return "article"
        else:
            return "misc"

    def _generate_cite_key(self, paper: Paper, entry_number: int) -> str:
        """
        Generate citation key for BibTeX entry.

        Format: firstauthor_year_keyword or paper_N if insufficient data

        Args:
            paper: Paper object
            entry_number: Fallback entry number

        Returns:
            Citation key string
        """
        # Try to construct meaningful key
        parts = []

        # Add first author's last name
        if paper.authors:
            first_author = paper.authors[0].name
            # Extract last name (assume last word)
            last_name = first_author.split()[-1]
            # Remove non-alphanumeric characters
            last_name = re.sub(r"[^a-zA-Z0-9]", "", last_name)
            parts.append(last_name.lower())

        # Add year
        if paper.year:
            parts.append(str(paper.year))

        # Add first significant word from title
        if paper.title:
            title_words = paper.title.lower().split()
            # Skip common words
            stop_words = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or"}
            for word in title_words:
                word_clean = re.sub(r"[^a-zA-Z0-9]", "", word)
                if word_clean and word_clean not in stop_words:
                    parts.append(word_clean[:10])  # Limit length
                    break

        if len(parts) >= 2:
            return "_".join(parts)
        else:
            # Fallback to generic key
            return f"paper_{entry_number}"

    def _format_author_bibtex(self, author: Author) -> str:
        """Format author name for BibTeX."""
        # BibTeX prefers "Last, First" or "First Last" format
        name_parts = author.name.split()
        if len(name_parts) >= 2:
            return author.name
        else:
            return author.name

    def _escape_bibtex(self, text: str) -> str:
        """
        Escape special characters for BibTeX.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ""

        # BibTeX special characters
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
            "\\": r"\textbackslash{}",
        }

        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        return result


class StreamingBibTeXExporter:
    """Streaming BibTeX exporter for large result sets."""

    def __init__(self, filename: str):
        """
        Initialize streaming exporter.

        Args:
            filename: Output BibTeX file path
        """
        self.filename = filename
        self.logger = get_logger(self.__class__.__name__)

        # Create output directory
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # Open file
        self.file = open(filename, "w", encoding="utf-8")
        self.count = 0
        self.exporter = BibTeXExporter()

    def write_paper(self, paper: Paper) -> None:
        """
        Write a single paper to the BibTeX file.

        Args:
            paper: Paper object to write
        """
        entry = self.exporter._paper_to_bibtex(paper, entry_number=self.count + 1)
        self.file.write(entry)
        self.file.write("\n\n")
        self.count += 1

    def write_papers(self, papers: list) -> None:
        """Write multiple papers."""
        for paper in papers:
            self.write_paper(paper)

    def close(self) -> None:
        """Close the BibTeX file."""
        if self.file:
            self.file.close()
            self.logger.info(f"Wrote {self.count} papers to {self.filename}")

    def __enter__(self) -> "StreamingBibTeXExporter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
