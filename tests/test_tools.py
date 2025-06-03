"""
Tests for data processing tools
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.tools.data_processing_tools import query_csv, read_pdf, web_search


class TestQueryCSV:
    """Tests for CSV query functionality"""
    
    @patch('app.tools.data_processing_tools.download_file_from_supabase')
    @patch('app.tools.data_processing_tools.duckdb')
    def test_query_csv_with_sql(self, mock_duckdb, mock_download):
        """Test CSV query with direct SQL"""
        # Mock file download
        mock_download.return_value = b"col1,col2\nval1,val2\n"
        
        # Mock DuckDB
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [("result1", "result2")]
        mock_conn.execute.return_value.description = [("col1",), ("col2",)]
        
        result = query_csv("test.csv", sql_query="SELECT * FROM current_csv_table")
        
        assert "result1" in result
        assert "result2" in result
        mock_download.assert_called_once()
        mock_duckdb.connect.assert_called_once()
    
    @patch('app.tools.data_processing_tools.download_file_from_supabase')
    def test_query_csv_with_objective(self, mock_download):
        """Test CSV query with intelligent objective"""
        # Mock file download
        mock_download.return_value = b"Company,Product\nAcme Corp,Drug A\n"
        
        with patch('app.tools.data_processing_tools.analyze_csv_schema') as mock_analyze, \
             patch('app.tools.data_processing_tools.create_query_plan') as mock_plan, \
             patch('app.tools.data_processing_tools.execute_query_plan') as mock_execute:
            
            # Mock schema analysis
            mock_schema = MagicMock()
            mock_analyze.return_value = mock_schema
            
            # Mock query plan
            mock_query_plan = MagicMock()
            mock_plan.return_value = mock_query_plan
            
            # Mock execution
            mock_execute.return_value = "Enhanced analysis result"
            
            result = query_csv("test.csv", objective="Count companies")
            
            assert "Enhanced analysis result" in result
            mock_analyze.assert_called_once()
            mock_plan.assert_called_once()
            mock_execute.assert_called_once()


class TestReadPDF:
    """Tests for PDF reading functionality"""
    
    @patch('app.tools.data_processing_tools.download_file_from_supabase')
    @patch('app.tools.data_processing_tools.pdfplumber')
    def test_read_pdf_success(self, mock_pdfplumber, mock_download):
        """Test successful PDF reading"""
        # Mock file download
        mock_download.return_value = b"fake pdf content"
        
        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample PDF text content"
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = read_pdf("test.pdf")
        
        assert "Sample PDF text content" in result
        mock_download.assert_called_once()
        mock_pdfplumber.open.assert_called_once()
    
    @patch('app.tools.data_processing_tools.download_file_from_supabase')
    def test_read_pdf_download_failure(self, mock_download):
        """Test PDF reading when download fails"""
        mock_download.return_value = None
        
        result = read_pdf("nonexistent.pdf")
        
        assert "Error" in result
        assert "Could not download" in result


class TestWebSearch:
    """Tests for web search functionality"""
    
    @patch('app.tools.data_processing_tools.TavilySearchResults')
    def test_web_search_success(self, mock_tavily):
        """Test successful web search"""
        # Mock Tavily client
        mock_client = MagicMock()
        mock_client.run.return_value = "Search results for query"
        mock_tavily.return_value = mock_client
        
        result = web_search("test query")
        
        assert "Search results for query" in result
        mock_tavily.assert_called_once()
        mock_client.run.assert_called_once_with("test query")
    
    @patch('app.tools.data_processing_tools.TavilySearchResults')
    def test_web_search_failure(self, mock_tavily):
        """Test web search when Tavily fails"""
        # Mock Tavily client to raise exception
        mock_client = MagicMock()
        mock_client.run.side_effect = Exception("API Error")
        mock_tavily.return_value = mock_client
        
        result = web_search("test query")
        
        assert "Error" in result
        assert "API Error" in result 