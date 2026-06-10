"""Root conftest: add src to sys.path."""
import sys
import os
import pytest

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture
def skip_no_spacy():
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        pytest.skip("spaCy en_core_web_sm not installed")
