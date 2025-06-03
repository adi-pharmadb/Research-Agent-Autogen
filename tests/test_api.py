"""
Tests for the main API endpoints
"""
import pytest
from unittest.mock import patch


class TestResearchEndpoint:
    """Tests for the /api/v1/research endpoint"""
    
    def test_health_endpoint(self, client):
        """Test the health endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "operational"
    
    def test_research_endpoint_validation_empty_question(self, client):
        """Test research endpoint with empty question"""
        request_data = {"question": "", "file_ids": None}
        response = client.post("/api/v1/research", json=request_data)
        assert response.status_code == 400
    
    def test_research_endpoint_validation_missing_question(self, client):
        """Test research endpoint with missing question"""
        request_data = {"file_ids": None}
        response = client.post("/api/v1/research", json=request_data)
        assert response.status_code == 422  # Pydantic validation error
    
    @patch('app.orchestration.research_flow.run_research_flow_with_tracking')
    def test_research_endpoint_success(self, mock_research_flow, client, sample_research_request):
        """Test successful research endpoint call"""
        # Mock the research flow response
        mock_research_flow.return_value = {
            "success": True,
            "final_answer": "Mock research answer",
            "agent_steps": [],
            "sources_used": ["web_search"],
            "processing_time_seconds": 1.5,
            "total_agent_turns": 2,
            "llm_calls_made": 3,
            "errors_encountered": [],
            "warnings": []
        }
        
        response = client.post("/api/v1/research", json=sample_research_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "final_answer" in data
        assert "agent_steps" in data
        assert "sources_used" in data
    
    def test_research_endpoint_missing_openai_key(self, client, sample_research_request):
        """Test research endpoint when OpenAI key is missing"""
        with patch('app.config.settings.OPENAI_API_KEY', None):
            response = client.post("/api/v1/research", json=sample_research_request)
            assert response.status_code == 503  # Service unavailable
    
    def test_research_endpoint_missing_supabase_config(self, client, sample_csv_request):
        """Test research endpoint when Supabase config is missing for file requests"""
        with patch('app.config.settings.SUPABASE_URL', None):
            response = client.post("/api/v1/research", json=sample_csv_request)
            assert response.status_code == 503  # Service unavailable


class TestRequestValidation:
    """Tests for request validation"""
    
    def test_research_request_model_valid(self):
        """Test valid research request model"""
        from app.main import ResearchRequest
        
        request = ResearchRequest(
            question="Test question",
            file_ids=["test.csv"]
        )
        assert request.question == "Test question"
        assert request.file_ids == ["test.csv"]
    
    def test_research_request_model_no_files(self):
        """Test research request model without files"""
        from app.main import ResearchRequest
        
        request = ResearchRequest(question="Test question")
        assert request.question == "Test question"
        assert request.file_ids is None 