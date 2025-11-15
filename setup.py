"""Setup configuration for the news agent package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="hackathon-news-agent",
    version="0.1.0",
    description="Integration layer, state management, and testing framework for news agent",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Person 3",
    author_email="person3@example.com",
    url="https://github.com/yourusername/hackathon-news-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.1.0",
        "langchain-openai>=0.0.2",
        "openai>=1.0.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "httpx>=0.25.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
        ],
        "async": [
            "aiohttp>=3.9.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "news-agent-demo=example_usage:main",
        ],
    },
)
