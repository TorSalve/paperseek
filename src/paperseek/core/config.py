"""Configuration management for academic search."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Configuration for a specific database."""

    api_key: Optional[str] = None
    rate_limit_per_second: float = Field(default=1.0, gt=0)
    rate_limit_per_minute: Optional[float] = None
    timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, gt=0)
    enabled: bool = True

    model_config = SettingsConfigDict(frozen=False)


class AcademicSearchConfig(BaseSettings):
    """Main configuration for the academic search package."""

    # General settings
    email: Optional[str] = Field(default=None, description="Email for polite API requests")
    user_agent: str = Field(
        default="AcademicSearchUnified/0.1.0", description="User agent string for API requests"
    )

    # Logging
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = None

    # Database-specific configs
    crossref: DatabaseConfig = Field(default_factory=DatabaseConfig)
    openalex: DatabaseConfig = Field(default_factory=DatabaseConfig)
    semantic_scholar: DatabaseConfig = Field(default_factory=DatabaseConfig)
    doi: DatabaseConfig = Field(default_factory=DatabaseConfig)
    pubmed: DatabaseConfig = Field(default_factory=DatabaseConfig)
    arxiv: DatabaseConfig = Field(default_factory=DatabaseConfig)
    core: DatabaseConfig = Field(default_factory=DatabaseConfig)
    unpaywall: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dblp: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # Search defaults
    default_max_results: int = Field(default=100, ge=1)
    default_timeout: int = Field(default=30, gt=0)

    # Fallback behavior
    fallback_mode: str = Field(
        default="sequential",
        description="How to handle multiple databases: 'sequential', 'parallel', or 'first'",
    )
    fail_fast: bool = Field(
        default=False, description="If True, stop on first error; otherwise try all databases"
    )

    model_config = SettingsConfigDict(
        env_prefix="ACADEMIC_SEARCH_", env_nested_delimiter="__", frozen=False
    )

    @field_validator("fallback_mode")
    @classmethod
    def validate_fallback_mode(cls, v: str) -> str:
        """Validate fallback mode."""
        allowed = ["sequential", "parallel", "first"]
        if v not in allowed:
            raise ValueError(f"fallback_mode must be one of {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v_upper

    def get_database_config(self, database: str) -> DatabaseConfig:
        """Get configuration for a specific database."""
        db_map = {
            "crossref": self.crossref,
            "openalex": self.openalex,
            "semantic_scholar": self.semantic_scholar,
            "doi": self.doi,
            "pubmed": self.pubmed,
            "arxiv": self.arxiv,
            "core": self.core,
            "unpaywall": self.unpaywall,
            "dblp": self.dblp,
        }

        db_lower = database.lower()
        if db_lower not in db_map:
            raise ValueError(f"Unknown database: {database}")

        return db_map[db_lower]

    @classmethod
    def from_yaml(cls, config_path: str) -> "AcademicSearchConfig":
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            AcademicSearchConfig instance
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AcademicSearchConfig":
        """
        Load configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            AcademicSearchConfig instance
        """
        return cls(**config_dict)

    @classmethod
    def from_env(cls) -> "AcademicSearchConfig":
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with ACADEMIC_SEARCH_
        and use double underscores for nested values.

        Examples:
            ACADEMIC_SEARCH_EMAIL=user@example.com
            ACADEMIC_SEARCH_CROSSREF__API_KEY=your_key
            ACADEMIC_SEARCH_OPENALEX__RATE_LIMIT_PER_SECOND=2.0

        Returns:
            AcademicSearchConfig instance
        """
        return cls()

    def to_yaml(self, output_path: str) -> None:
        """
        Save configuration to a YAML file.

        Args:
            output_path: Path to output YAML file
        """
        data = self.model_dump()

        with open(output_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_user_agent(self) -> str:
        """Get the complete user agent string with email if available."""
        if self.email:
            return f"{self.user_agent} (mailto:{self.email})"
        return self.user_agent


def load_config(
    config_file: Optional[str] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    use_env: bool = True,
) -> AcademicSearchConfig:
    """
    Load configuration from multiple sources with priority.

    Priority order (highest to lowest):
    1. config_dict (direct parameters)
    2. config_file (YAML file)
    3. Environment variables (if use_env=True)

    Args:
        config_file: Path to YAML configuration file
        config_dict: Configuration dictionary
        use_env: Whether to load from environment variables

    Returns:
        AcademicSearchConfig instance
    """
    # Start with environment variables if enabled
    if use_env:
        config = AcademicSearchConfig.from_env()
    else:
        config = AcademicSearchConfig()

    # Override with file config
    if config_file:
        file_config = AcademicSearchConfig.from_yaml(config_file)
        # Merge configurations
        for field_name in file_config.model_fields:
            setattr(config, field_name, getattr(file_config, field_name))

    # Override with dict config
    if config_dict:
        dict_config = AcademicSearchConfig.from_dict(config_dict)
        for field_name in dict_config.model_fields:
            value = getattr(dict_config, field_name)
            # Only override if value is not default
            if value != config.model_fields[field_name].default:
                setattr(config, field_name, value)

    return config
