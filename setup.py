#!/usr/bin/env python3
"""
Setup configuration for OpenTelemetry Validator CLI
"""

from setuptools import setup, find_packages

setup(
    name="otel-validator",
    version="0.1.0",
    description="AI-powered OpenTelemetry instrumentation validator using RAG",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "langchain>=0.1.0",
        "langchain-openai>=0.1.0",
        "langchain-community>=0.0.10",
        "chromadb>=0.4.0",
        "python-dotenv>=1.0.0",
        "click>=8.0.0",
        "rich>=12.0.0",
        "pyyaml>=6.0",
        "gitpython>=3.1.0",
        "numpy>=1.21.0",
        "tiktoken>=0.5.0",
        "pydantic>=1.10.0"
    ],
    entry_points={
        "console_scripts": [
            "otel-validator=cli.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)