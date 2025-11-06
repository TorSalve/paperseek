"""Shared normalization utilities for paper data across different databases.

This module provides common utilities to reduce code duplication across database clients.
Each client has unique data formats, but many operations (parsing dates, cleaning text,
extracting DOIs, etc.) are similar and can be shared.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ..core.models import Author


class TextNormalizer:
    """Utilities for cleaning and normalizing text fields."""

    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        """
        Clean and sanitize text fields.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text or None
        """
        if not text:
            return None

        # Strip whitespace
        cleaned = text.strip()

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned if cleaned else None

    @staticmethod
    def truncate_text(text: Optional[str], max_length: int = 1000) -> Optional[str]:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text or None
        """
        if not text:
            return None

        cleaned = TextNormalizer.clean_text(text)
        if not cleaned:
            return None

        if len(cleaned) > max_length:
            return cleaned[:max_length] + "..."

        return cleaned


class DateNormalizer:
    """Utilities for parsing and normalizing dates."""

    @staticmethod
    def extract_year(date_input: Any) -> Optional[int]:
        """
        Extract year from various date formats.

        Handles:
        - Integer year (2023)
        - String year ("2023")
        - ISO date string ("2023-05-15")
        - Datetime object
        - Date parts list [[2023, 5, 15]]
        - Date dict {"year": 2023}

        Args:
            date_input: Date in various formats

        Returns:
            Year as integer or None
        """
        if not date_input:
            return None

        # Already an integer
        if isinstance(date_input, int):
            if 1900 <= date_input <= 2100:
                return date_input
            return None

        # String that might be a year or date
        if isinstance(date_input, str):
            # Try to extract year from ISO date
            try:
                date_obj = datetime.fromisoformat(date_input.replace("Z", "+00:00"))
                return date_obj.year
            except (ValueError, AttributeError):
                pass

            # Try to extract just the year
            match = re.search(r"\b(19|20)\d{2}\b", date_input)
            if match:
                return int(match.group(0))

            return None

        # Datetime object
        if isinstance(date_input, datetime):
            return date_input.year

        # Date parts list (CrossRef style: [[2023, 5, 15]])
        if isinstance(date_input, list) and date_input:
            first_part = date_input[0]
            if isinstance(first_part, list) and first_part:
                year = first_part[0]
                if isinstance(year, int) and 1900 <= year <= 2100:
                    return year
            elif isinstance(first_part, int) and 1900 <= first_part <= 2100:
                return first_part

        # Dict with year field or date-parts (CrossRef style)
        if isinstance(date_input, dict):
            # Check for direct year field
            year = date_input.get("year")
            if year:
                return DateNormalizer.extract_year(year)
            
            # Check for date-parts (CrossRef style: {"date-parts": [[2023, 5, 15]]})
            date_parts = date_input.get("date-parts")
            if date_parts and isinstance(date_parts, list) and date_parts:
                first_part = date_parts[0]
                if isinstance(first_part, list) and first_part:
                    year_value = first_part[0]
                    if isinstance(year_value, int) and 1900 <= year_value <= 2100:
                        return year_value

        return None

    @staticmethod
    def parse_date_parts(date_parts: Any) -> Optional[str]:
        """
        Parse date parts to ISO date string.

        Args:
            date_parts: Date parts in various formats

        Returns:
            ISO date string (YYYY-MM-DD) or None
        """
        if not date_parts:
            return None

        # Handle CrossRef style: {"date-parts": [[2023, 5, 15]]}
        if isinstance(date_parts, dict) and "date-parts" in date_parts:
            date_parts = date_parts["date-parts"]

        # Handle nested list: [[2023, 5, 15]]
        if isinstance(date_parts, list) and date_parts:
            parts = date_parts[0] if isinstance(date_parts[0], list) else date_parts

            if len(parts) >= 1:
                year = parts[0]
                month = parts[1] if len(parts) >= 2 else 1
                day = parts[2] if len(parts) >= 3 else 1

                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except (ValueError, TypeError):
                    pass

        return None


class AuthorNormalizer:
    """Utilities for normalizing author data."""

    @staticmethod
    def normalize_author_name(
        given: Optional[str] = None,
        family: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> str:
        """
        Normalize author name from various formats.

        Args:
            given: Given name (first name)
            family: Family name (last name)
            full_name: Full name if not split

        Returns:
            Normalized full name
        """
        if full_name:
            return TextNormalizer.clean_text(full_name) or "Unknown"

        name_parts = []
        if given:
            name_parts.append(TextNormalizer.clean_text(given))
        if family:
            name_parts.append(TextNormalizer.clean_text(family))

        if name_parts:
            return " ".join(p for p in name_parts if p)

        return "Unknown"

    @staticmethod
    def create_author(
        name: Optional[str] = None,
        given: Optional[str] = None,
        family: Optional[str] = None,
        affiliation: Optional[str] = None,
        orcid: Optional[str] = None,
    ) -> Author:
        """
        Create Author object with normalized data.

        Args:
            name: Full name
            given: Given name
            family: Family name
            affiliation: Affiliation
            orcid: ORCID identifier

        Returns:
            Author object
        """
        normalized_name = AuthorNormalizer.normalize_author_name(
            given=given, family=family, full_name=name
        )

        return Author(
            name=normalized_name,
            affiliation=TextNormalizer.clean_text(affiliation),
            orcid=TextNormalizer.clean_text(orcid),
        )


class IdentifierNormalizer:
    """Utilities for normalizing identifiers (DOI, PMID, etc.)."""

    @staticmethod
    def clean_doi(doi: Optional[str]) -> Optional[str]:
        """
        Clean and normalize DOI.

        Removes common prefixes like "doi:", "DOI:", "https://doi.org/", etc.

        Args:
            doi: Raw DOI string

        Returns:
            Cleaned DOI or None
        """
        if not doi:
            return None

        doi = doi.strip()

        # Remove common prefixes
        prefixes = [
            "doi:",
            "DOI:",
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
        ]

        for prefix in prefixes:
            if doi.lower().startswith(prefix.lower()):
                doi = doi[len(prefix) :]
                break

        return doi.strip() if doi else None

    @staticmethod
    def extract_arxiv_id(text: Optional[str]) -> Optional[str]:
        """
        Extract arXiv ID from text or URL.

        Args:
            text: Text containing arXiv ID

        Returns:
            Cleaned arXiv ID or None
        """
        if not text:
            return None

        # Remove arXiv: prefix
        text = text.replace("arXiv:", "").replace("arxiv:", "")

        # Extract from URL
        if "arxiv.org" in text:
            match = re.search(r"(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", text)
            if match:
                return match.group(1)

        # Direct ID pattern
        match = re.search(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b", text)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def extract_pmid(text: Optional[str]) -> Optional[str]:
        """
        Extract PubMed ID from text or URL.

        Args:
            text: Text containing PMID

        Returns:
            Cleaned PMID or None
        """
        if not text:
            return None

        # Extract from URL
        if "pubmed" in text.lower():
            match = re.search(r"/(\d+)/?", text)
            if match:
                return match.group(1)

        # Direct ID pattern (numeric only)
        match = re.search(r"\b(\d{7,8})\b", text)
        if match:
            return match.group(1)

        return None


class URLNormalizer:
    """Utilities for normalizing URLs."""

    @staticmethod
    def clean_url(url: Optional[str]) -> Optional[str]:
        """
        Clean and validate URL.

        Args:
            url: Raw URL string

        Returns:
            Cleaned URL or None
        """
        if not url:
            return None

        url = url.strip()

        # Basic validation
        try:
            result = urlparse(url)
            if result.scheme in ("http", "https") and result.netloc:
                return url
        except Exception:
            pass

        return None

    @staticmethod
    def extract_pdf_url(links: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract PDF URL from list of link objects.

        Args:
            links: List of link dictionaries

        Returns:
            PDF URL or None
        """
        if not links:
            return None

        for link in links:
            if not isinstance(link, dict):
                continue

            # Check content type
            content_type = link.get("content-type", "").lower()
            if "pdf" in content_type:
                url = link.get("URL") or link.get("url") or link.get("href")
                if url:
                    return URLNormalizer.clean_url(url)

            # Check title or rel
            title = (link.get("title") or "").lower()
            rel = (link.get("rel") or "").lower()
            if "pdf" in title or "pdf" in rel:
                url = link.get("URL") or link.get("url") or link.get("href")
                if url:
                    return URLNormalizer.clean_url(url)

        return None


class VenueNormalizer:
    """Utilities for normalizing venue/journal/conference data."""

    @staticmethod
    def classify_venue_type(
        venue: Optional[str],
        publication_type: Optional[str] = None,
        venue_hints: Optional[Dict[str, Any]] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Classify venue as journal or conference.

        Args:
            venue: Venue name
            publication_type: Type from API (e.g., "journal-article", "proceedings-article")
            venue_hints: Additional hints from API

        Returns:
            Tuple of (journal, conference) - one will be None
        """
        if not venue:
            return None, None

        # Check publication type first
        if publication_type:
            pub_type_lower = publication_type.lower()
            if any(
                word in pub_type_lower
                for word in ["proceedings", "conference", "symposium", "workshop"]
            ):
                return None, venue
            if any(word in pub_type_lower for word in ["journal", "article"]):
                return venue, None

        # Check venue name for keywords
        venue_lower = venue.lower()
        conference_keywords = [
            "conference",
            "symposium",
            "workshop",
            "proceedings",
            "congress",
            "summit",
        ]
        journal_keywords = ["journal", "transactions", "letters", "review", "magazine"]

        if any(keyword in venue_lower for keyword in conference_keywords):
            return None, venue
        if any(keyword in venue_lower for keyword in journal_keywords):
            return venue, None

        # Default to journal if unclear
        return venue, None

    @staticmethod
    def extract_venue_from_list(
        venue_list: Optional[List[str]], default: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract venue from list (handle APIs that return lists).

        Args:
            venue_list: List of venue strings
            default: Default value if list is empty

        Returns:
            First non-empty venue or default
        """
        if not venue_list:
            return default

        if isinstance(venue_list, list):
            for venue in venue_list:
                if venue and isinstance(venue, str):
                    cleaned = TextNormalizer.clean_text(venue)
                    if cleaned:
                        return cleaned

        return default
