"""
Integration tests for the research flow
"""
import pytest
from unittest.mock import patch, AsyncMock
from app.orchestration.research_flow import run_research_flow_with_tracking


class TestResearchFlowIntegration:
    """Integration tests for the complete research flow"""
    
    @pytest.mark.asyncio
    @patch('app.orchestration.research_flow.get_default_llm_config')
    @patch('app.tools.data_processing_tools.web_search')
    async def test_web_search_flow(self, mock_web_search, mock_llm_config):
        """Test complete flow with web search"""
        # Mock LLM config
        mock_llm_config.return_value = {"model": "gpt-4"}
        
        # Mock web search
        mock_web_search.return_value = "AI drug discovery has advanced significantly..."
        
        # Mock the AutoGen conversation
        with patch('app.orchestration.research_flow.UserProxyAgent') as mock_user_proxy, \
             patch('app.orchestration.research_flow.AnalystAgent') as mock_analyst:
            
            # Mock agent responses
            mock_user_proxy_instance = AsyncMock()
            mock_analyst_instance = AsyncMock()
            
            mock_user_proxy.return_value = mock_user_proxy_instance
            mock_analyst.return_value = mock_analyst_instance
            
            # Mock conversation result
            mock_user_proxy_instance.initiate_chat = AsyncMock(return_value=None)
            
            result = await run_research_flow_with_tracking(
                user_question="What are the latest AI advancements?",
                file_ids=None,
                llm_config={"model": "gpt-4"}
            )
            
            assert result["success"] is True
            assert "sources_used" in result
            assert "processing_time_seconds" in result
    
    @pytest.mark.asyncio
    @patch('app.orchestration.research_flow.get_default_llm_config')
    @patch('app.tools.data_processing_tools.query_csv')
    async def test_csv_analysis_flow(self, mock_query_csv, mock_llm_config):
        """Test complete flow with CSV analysis"""
        # Mock LLM config
        mock_llm_config.return_value = {"model": "gpt-4"}
        
        # Mock CSV query
        mock_query_csv.return_value = "Found 5 companies with ALFATRADIOL registration"
        
        # Mock the AutoGen conversation
        with patch('app.orchestration.research_flow.UserProxyAgent') as mock_user_proxy, \
             patch('app.orchestration.research_flow.AnalystAgent') as mock_analyst:
            
            mock_user_proxy_instance = AsyncMock()
            mock_analyst_instance = AsyncMock()
            
            mock_user_proxy.return_value = mock_user_proxy_instance
            mock_analyst.return_value = mock_analyst_instance
            
            mock_user_proxy_instance.initiate_chat = AsyncMock(return_value=None)
            
            result = await run_research_flow_with_tracking(
                user_question="How many companies registered ALFATRADIOL?",
                file_ids=["Mexico_Product_Registry.csv"],
                llm_config={"model": "gpt-4"}
            )
            
            assert result["success"] is True
            assert "sources_used" in result
    
    @pytest.mark.asyncio
    @patch('app.orchestration.research_flow.get_default_llm_config')
    async def test_missing_llm_config(self, mock_llm_config):
        """Test flow when LLM config is missing"""
        mock_llm_config.return_value = None
        
        result = await run_research_flow_with_tracking(
            user_question="Test question",
            file_ids=None,
            llm_config=None
        )
        
        assert result["success"] is False
        assert "LLM configuration" in result["final_answer"] 