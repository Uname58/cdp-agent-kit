#!/usr/bin/env python3
from pathlib import Path
from setuptools import setup, find_namespace_packages

ROOT = Path(__file__).parent
README = ROOT / "cli_anything/browser_cdp/README.md"

def read_readme():
    try:
        return README.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

setup(
    name="cli-anything-browser-cdp",
    version="0.1.0",

    author="Uname58",
    description="CLI harness for browser automation via Chrome DevTools Protocol — connects to YOUR existing Chrome, no extensions needed",
    long_description=read_readme(),
    long_description_content_type="text/markdown",

    url="https://github.com/Uname58/cdp-agent-kit",
    project_urls={
        "Homepage": "https://github.com/Uname58/cdp-agent-kit",
        "Issues": "https://github.com/Uname58/cdp-agent-kit/issues",
    },

    license="MIT",

    packages=find_namespace_packages(include=["cli_anything.*"]),
    python_requires=">=3.10",

    install_requires=[
        "click>=8.1,<9.0",
        "websocket-client>=1.0",
    ],

    extras_require={
        "dev": [
            "pytest>=7",
            "pytest-cov>=4",
        ],
    },

    entry_points={
        "console_scripts": [
            "cli-anything-browser-cdp=cli_anything.browser_cdp.browser_cdp_cli:main",
        ],
    },

    include_package_data=True,
    zip_safe=False,

    keywords="cli browser automation cdp chrome-devtools-protocol ai-agent",

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
