"""
Pytest configuration for PharmaDB Deep-Research Micro-Service tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)

@pytest.fixture
def sample_research_request():
    """Sample research request for testing"""
    return {
        'question': 'What are the latest advancements in AI for drug discovery?',
        'file_ids': None
    }

@pytest.fixture
def sample_csv_request():
    """Sample CSV research request for testing"""
    return {
        'question': 'How many companies have registered ALFATRADIOL?',
        'file_ids': ['Mexico_Product_Registry.csv']
    }

@pytest.fixture
def sample_pdf_request():
    """Sample PDF research request for testing"""
    return {
        'question': 'What are the Ethics Committee requirements for clinical trials?',
        'file_ids': ['23NEW DRUGS AND CLINICAL TRIALS RULES, 2019.pdf']
    } 