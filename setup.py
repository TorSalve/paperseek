"""Setup script for paperseek package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="paperseek",
    version="0.1.0",
    author="Tor-Salve Dalsgaard",
    author_email="torsalve@di.ku.dk",
    description="A unified interface for searching multiple academic databases",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TorSalve/paperseek",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "pandas>=1.5.0",
        "pyyaml>=6.0",
        "pyrate-limiter>=3.0.0",
        "python-dotenv>=1.0.0",
        "bibtexparser>=1.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
            "ruff>=0.0.290",
        ],
    },
    entry_points={
        "console_scripts": [
            # Add CLI entry points if needed
        ],
    },
)
