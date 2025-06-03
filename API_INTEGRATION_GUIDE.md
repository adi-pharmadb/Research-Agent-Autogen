# PharmaDB Research Microservice - API Integration Guide

## 🚀 Overview

The PharmaDB Research Microservice provides AI-powered research capabilities using AutoGen multi-agent systems. It can process natural language questions, analyze CSV data, read PDF documents, and perform web searches to deliver comprehensive research answers.

**Base URL**: `https://pharmadb-research-agent-v1.onrender.com` (or your deployed URL)

## 📋 Quick Integration Checklist

- [ ] Get the deployed microservice URL
- [ ] Test the `/health` endpoint
- [ ] Implement the research endpoint call
- [ ] Add error handling for timeouts and failures
- [ ] Handle file uploads (if using file analysis)
- [ ] Add loading states for long-running requests

## 🔗 API Endpoints

### 1. Health Check
**`GET /health`**

Check if the microservice is operational and properly configured.

```bash
curl -X GET "https://pharmadb-research-agent-v1.onrender.com/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "services": {
    "supabase": "connected",
    "openai": "configured", 
    "tavily": "configured"
  }
}
```

### 2. Research Endpoint
**`POST /api/v1/research`**

Submit a research question and get comprehensive AI-powered analysis.

**Request Body:**
```json
{
  "question": "What are the latest advancements in AI for drug discovery?",
  "file_ids": ["optional-file-1.pdf", "data.csv"]  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "final_answer": "### Latest Advancements in AI for Drug Discovery\n\nRecent developments include...",
  "agent_steps": [
    {
      "step_number": 1,
      "agent_name": "Analyst",
      "action_type": "analysis",
      "content": "I will analyze your question about AI in drug discovery...",
      "timestamp": "2025-01-01T12:00:00.000Z",
      "tool_used": null,
      "tool_parameters": null,
      "tool_result": null
    }
  ],
  "sources_used": ["web_search"],
  "processing_time_seconds": 15.34,
  "total_agent_turns": 3,
  "llm_calls_made": 5,
  "errors_encountered": [],
  "warnings": []
}
```

## 💻 Integration Code Examples

### Python (FastAPI/Django)

```python
import httpx
import asyncio
from typing import List, Optional, Dict, Any

class PharmaResearchClient:
    def __init__(self, base_url: str, timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the research service is healthy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def research(self, question: str, file_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Submit a research question and get AI-powered analysis"""
        payload = {"question": question}
        if file_ids:
            payload["file_ids"] = file_ids
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/research",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()

# Usage in your main app
async def handle_user_research_request(user_question: str, uploaded_files: List[str] = None):
    client = PharmaResearchClient("https://pharmadb-research-agent-v1.onrender.com")
    
    try:
        # Optional: Check service health first
        health = await client.health_check()
        if health["status"] != "healthy":
            return {"error": "Research service is not available"}
        
        # Submit research request
        result = await client.research(user_question, uploaded_files)
        
        if result["success"]:
            return {
                "answer": result["final_answer"],
                "metadata": {
                    "processing_time": result["processing_time_seconds"],
                    "sources": result["sources_used"],
                    "agent_steps": result["agent_steps"]
                }
            }
        else:
            return {"error": "Research failed"}
            
    except httpx.TimeoutException:
        return {"error": "Research request timed out. Please try again."}
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
```

### JavaScript/TypeScript (React/Node.js)

```typescript
interface ResearchRequest {
  question: string;
  file_ids?: string[];
}

interface ResearchResponse {
  success: boolean;
  final_answer: string;
  agent_steps: AgentStep[];
  sources_used: string[];
  processing_time_seconds: number;
  total_agent_turns: number;
  llm_calls_made: number;
  errors_encountered: string[];
  warnings: string[];
}

interface AgentStep {
  step_number: number;
  agent_name: string;
  action_type: string;
  content: string;
  timestamp: string;
  tool_used?: string;
  tool_parameters?: Record<string, any>;
  tool_result?: string;
}

class PharmaResearchClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string, timeout: number = 300000) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeout = timeout;
  }

  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  }

  async research(question: string, fileIds?: string[]): Promise<ResearchResponse> {
    const payload: ResearchRequest = { question };
    if (fileIds) {
      payload.file_ids = fileIds;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/research`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timed out');
      }
      throw error;
    }
  }
}

// React Hook Example
import { useState, useCallback } from 'react';

export const useResearch = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const client = new PharmaResearchClient(process.env.REACT_APP_RESEARCH_API_URL);

  const submitResearch = useCallback(async (question: string, fileIds?: string[]) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await client.research(question, fileIds);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, result, error, submitResearch };
};
```

### cURL Examples

```bash
# Health Check
curl -X GET "https://pharmadb-research-agent-v1.onrender.com/health"

# Simple Research Question
curl -X POST "https://pharmadb-research-agent-v1.onrender.com/api/v1/research" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the side effects of metformin?"
  }'

# Research with File Analysis
curl -X POST "https://pharmadb-research-agent-v1.onrender.com/api/v1/research" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Analyze the drug data for diabetes medications",
    "file_ids": ["diabetes_drugs.csv", "clinical_trial.pdf"]
  }'
```

## 🔥 File Upload Integration

If your main app needs to upload files for analysis, here's the recommended flow:

### 1. Upload Files to Supabase (from main app)
```python
# In your main app - upload files to Supabase
from supabase import create_client, Client

supabase: Client = create_client(supabase_url, supabase_key)

async def upload_file_for_research(file_content: bytes, filename: str) -> str:
    """Upload file and return file_id for research API"""
    
    # Upload to Supabase storage
    response = supabase.storage.from_("pharma_research_files").upload(
        path=filename,
        file=file_content,
        file_options={"content-type": "application/octet-stream"}
    )
    
    if response.error:
        raise Exception(f"Upload failed: {response.error}")
    
    return filename  # This becomes the file_id for research API
```

### 2. Research with Uploaded Files
```python
# After upload, call research API with file_ids
file_id = await upload_file_for_research(pdf_content, "research_paper.pdf")
research_result = await client.research(
    question="Summarize the key findings from this paper",
    file_ids=[file_id]
)
```

## ⚡ Error Handling Best Practices

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid question, empty input)
- **503**: Service Unavailable (missing API keys, service down)
- **500**: Internal Server Error
- **Timeout**: Request exceeded 5 minutes

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Recommended Error Handling
```python
async def handle_research_with_retry(question: str, max_retries: int = 3):
    """Research with automatic retry logic"""
    
    for attempt in range(max_retries):
        try:
            return await client.research(question)
        
        except httpx.TimeoutException:
            if attempt == max_retries - 1:
                return {"error": "Research timed out after multiple attempts"}
            await asyncio.sleep(5)  # Wait before retry
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                # Service unavailable - might be temporary
                if attempt == max_retries - 1:
                    return {"error": "Research service temporarily unavailable"}
                await asyncio.sleep(10)
            else:
                # Other HTTP errors - don't retry
                return {"error": f"API error: {e.response.status_code}"}
```

## 🎯 Performance Considerations

### Request Timeouts
- **Typical response time**: 10-30 seconds
- **Complex queries**: Up to 5 minutes
- **Recommended timeout**: 300 seconds (5 minutes)

### Rate Limiting
- **Current limit**: No enforced limit
- **Recommended**: Implement your own rate limiting in main app
- **Concurrent requests**: Up to 20 per instance

### Caching Strategy (Optional)
```python
# Simple cache for repeated questions
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
async def cached_research(question_hash: str, question: str):
    """Cache research results for identical questions"""
    return await client.research(question)

async def research_with_cache(question: str):
    question_hash = hashlib.md5(question.encode()).hexdigest()
    return await cached_research(question_hash, question)
```

## 🔒 Security Considerations

### API Key Management
```python
# Environment variables for main app
PHARMA_RESEARCH_API_URL=https://your-api-url.com
PHARMA_RESEARCH_API_KEY=optional-if-you-add-auth  # Future enhancement
```

### Input Validation
```python
def validate_research_request(question: str, file_ids: List[str] = None):
    """Validate request before sending to API"""
    
    if not question or len(question.strip()) < 3:
        raise ValueError("Question must be at least 3 characters")
    
    if len(question) > 5000:
        raise ValueError("Question too long (max 5000 characters)")
    
    if file_ids and len(file_ids) > 10:
        raise ValueError("Maximum 10 files per request")
```

## 📱 UI/UX Integration Guidelines

### Loading States
```javascript
// Show progressive loading states
const loadingStates = [
  "Analyzing your question...",
  "Searching for relevant information...", 
  "Processing data and documents...",
  "Generating comprehensive answer..."
];
```

### Response Display
```javascript
// Render markdown response
import ReactMarkdown from 'react-markdown';

<ReactMarkdown>{result.final_answer}</ReactMarkdown>

// Show metadata
<div className="metadata">
  <span>Processing time: {result.processing_time_seconds}s</span>
  <span>Sources: {result.sources_used.join(', ')}</span>
</div>
```

## 🧪 Testing

### Test Cases to Implement
```python
# Test cases for your main app integration
async def test_research_integration():
    # 1. Simple question
    result = await client.research("What is aspirin used for?")
    assert result["success"] is True
    
    # 2. File analysis  
    result = await client.research(
        "Analyze this data", 
        file_ids=["test.csv"]
    )
    assert "csv" in result["sources_used"]
    
    # 3. Error handling
    try:
        await client.research("")  # Empty question
        assert False, "Should have raised an error"
    except Exception:
        pass  # Expected
```

## 🚀 Deployment URL

Replace `https://your-api-url.com` with your actual deployed URL:

```bash
# Your Render deployment URL:
https://pharmadb-research-agent-v1.onrender.com
```

## 📞 Support

For integration questions or issues:
1. Check the `/health` endpoint first
2. Verify your request format matches the examples
3. Check network connectivity and timeouts
4. Review error messages in the response

---

**Ready to integrate!** This microservice is production-ready and will handle multiple concurrent users seamlessly. 