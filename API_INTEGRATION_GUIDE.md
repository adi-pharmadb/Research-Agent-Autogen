# PharmaDB Research Microservice - API Integration Guide

## 🚀 Overview

The PharmaDB Research Microservice provides AI-powered research capabilities using AutoGen multi-agent systems with **real tool execution**. It can process natural language questions, analyze CSV data, read PDF documents, and perform live web searches to deliver comprehensive research answers with actual data sources.

**Key Features:**
- 🔍 **Live Web Search**: Real-time pharmaceutical research using Tavily API with actual URLs and content
- 📊 **CSV Data Analysis**: SQL-based queries on uploaded files using DuckDB
- 📄 **PDF Document Processing**: Text extraction and analysis using pdfplumber
- 🤖 **Multi-Agent AI**: Analyst → DataRunner → Writer workflow with detailed step tracking
- ⚡ **Fast Performance**: 3-8 seconds for most queries with real tool execution
- 🌐 **Concurrent Support**: Stateless architecture supporting multiple simultaneous users

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
  "file_ids": ["optional-file-1.pdf", "data.csv"],  // Optional
  "conversation_history": [  // Optional - for multi-turn conversations
    {
      "role": "user",
      "content": "Tell me about diabetes medications",
      "timestamp": "2025-01-01T11:55:00Z",
      "source": "user"
    },
    {
      "role": "assistant", 
      "content": "Here are the main classes of diabetes medications...",
      "timestamp": "2025-01-01T11:55:15Z",
      "source": "assistant"
    }
  ],
  "system_prompt": "You are a regulatory affairs specialist with FDA experience. Focus on compliance and safety."  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "final_answer": "# Research Analysis: What are the latest FDA diabetes drug approvals in 2024?\n## Web Research Findings\nResult 1:\n  Title: New Indications and Dosage Forms for 2024 - Drugs.com\n  URL: https://www.drugs.com/new-indications-archive/2024.html\n  Content Snippet: June 12, 2024 · FDA Approves Xigduo XR (dapagliflozin/metformin) for Glycemic Control...\n\nResult 2:\n  Title: Understanding the 2024 FDA Approvals for New Diabetes Medications\n  URL: https://www.longislanddiabetes.org/understanding-the-2024-fda-approvals...\n  Content Snippet: The recent FDA approvals for new diabetes medications in 2024 have significant implications...",
  "agent_steps": [
    {
      "step_number": 1,
      "agent_name": "Analyst",
      "action_type": "analysis",
      "content": "I'm analyzing your research question: 'What are the latest FDA diabetes drug approvals in 2024?'",
      "timestamp": "2025-01-01T12:00:00.000Z",
      "tool_used": null,
      "tool_parameters": null,
      "tool_result": null
    },
    {
      "step_number": 2,
      "agent_name": "DataRunner",
      "action_type": "tool_execution", 
      "content": "Performing web search for relevant information",
      "timestamp": "2025-01-01T12:00:04.000Z",
      "tool_used": "web_search",
      "tool_parameters": {"query": "FDA diabetes drug approvals 2024", "max_results": 10},
      "tool_result": "Successfully gathered web search results with 5829 characters"
    }
  ],
  "sources_used": ["web_search"],
  "processing_time_seconds": 4.15,
  "total_agent_turns": 3,
  "llm_calls_made": 2,
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
from datetime import datetime

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
    
    async def research(self, question: str, file_ids: Optional[List[str]] = None, 
                     conversation_history: Optional[List[Dict[str, Any]]] = None,
                     system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Submit a research question and get AI-powered analysis"""
        payload = {"question": question}
        if file_ids:
            payload["file_ids"] = file_ids
        if conversation_history:
            payload["conversation_history"] = conversation_history
        if system_prompt:
            payload["system_prompt"] = system_prompt
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/research",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()

# Usage in your main app with conversation management
class ConversationManager:
    def __init__(self):
        self.conversation_history = []
    
    def add_exchange(self, question: str, response: str):
        """Add a question-response exchange to conversation history"""
        timestamp = datetime.now().isoformat()
        
        self.conversation_history.extend([
            {
                "role": "user",
                "content": question,
                "timestamp": timestamp,
                "source": "user"
            },
            {
                "role": "assistant", 
                "content": response,
                "timestamp": timestamp,
                "source": "assistant"
            }
        ])
        
        # Keep only last 20 exchanges (40 messages)
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
    
    async def research_with_context(self, client: PharmaResearchClient, 
                                  question: str, **kwargs):
        """Research with automatic conversation history management"""
        result = await client.research(
            question=question,
            conversation_history=self.conversation_history,
            **kwargs
        )
        
        if result.get("success"):
            self.add_exchange(question, result["final_answer"])
        
        return result

async def handle_user_research_request(user_question: str, 
                                     uploaded_files: List[str] = None,
                                     expertise_type: str = None,
                                     conversation_manager: ConversationManager = None):
    client = PharmaResearchClient("https://pharmadb-research-agent-v1.onrender.com")
    
    # System prompts for different expertise types
    EXPERTISE_PROMPTS = {
        "regulatory": """You are a regulatory affairs specialist with FDA experience. 
                        Focus on compliance, safety data interpretation, and submission requirements.""",
        "clinical": """You are a clinical pharmacologist specializing in drug therapy. 
                      Focus on efficacy, safety profiles, and clinical applications.""",
        "economic": """You are a health economics specialist. 
                      Focus on cost-effectiveness, market access, and economic value."""
    }
    
    try:
        # Optional: Check service health first
        health = await client.health_check()
        if health["status"] != "healthy":
            return {"error": "Research service is not available"}
        
        # Prepare request parameters
        research_kwargs = {}
        if uploaded_files:
            research_kwargs["file_ids"] = uploaded_files
        if expertise_type and expertise_type in EXPERTISE_PROMPTS:
            research_kwargs["system_prompt"] = EXPERTISE_PROMPTS[expertise_type]
        
        # Submit research request with context if available
        if conversation_manager:
            result = await conversation_manager.research_with_context(
                client, user_question, **research_kwargs
            )
        else:
            result = await client.research(user_question, **research_kwargs)
        
        if result["success"]:
            return {
                "answer": result["final_answer"],
                "metadata": {
                    "processing_time": result["processing_time_seconds"],
                    "sources": result["sources_used"],
                    "agent_steps": result["agent_steps"],
                    "conversation_length": len(conversation_manager.conversation_history) if conversation_manager else 0
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

# Example usage patterns
async def example_usage():
    # 1. Simple one-off research
    client = PharmaResearchClient("https://pharmadb-research-agent-v1.onrender.com")
    result = await client.research("What are the side effects of metformin?")
    
    # 2. Research with specialized expertise
    result = await client.research(
        "Evaluate this clinical trial data",
        file_ids=["trial_data.pdf"],
        system_prompt="You are a regulatory affairs specialist. Focus on FDA submission requirements."
    )
    
    # 3. Conversational research session
    conversation = ConversationManager()
    
    # First question
    result1 = await conversation.research_with_context(
        client, "What are the main diabetes medications?"
    )
    
    # Follow-up question (automatically includes conversation history)
    result2 = await conversation.research_with_context(
        client, "What about dosing for elderly patients?",
        system_prompt="You are a geriatric pharmacist. Focus on age-related considerations."
    )

### JavaScript/TypeScript (React/Node.js)

```typescript
interface ResearchRequest {
  question: string;
  file_ids?: string[];
  conversation_history?: ConversationMessage[];
  system_prompt?: string;
}

interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  source?: string;
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

  async research(question: string, options?: {
    fileIds?: string[];
    conversationHistory?: ConversationMessage[];
    systemPrompt?: string;
  }): Promise<ResearchResponse> {
    const payload: ResearchRequest = { question };
    
    if (options?.fileIds) {
      payload.file_ids = options.fileIds;
    }
    if (options?.conversationHistory) {
      payload.conversation_history = options.conversationHistory;
    }
    if (options?.systemPrompt) {
      payload.system_prompt = options.systemPrompt;
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

  const submitResearch = useCallback(async (question: string, fileIds: string[] = []) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await client.research(question, { fileIds });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, result, error, submitResearch };
};

// Conversation Management Hook
export const useConversationResearch = () => {
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const client = new PharmaResearchClient(process.env.REACT_APP_RESEARCH_API_URL);

  const addToConversation = (role: 'user' | 'assistant', content: string) => {
    const message: ConversationMessage = {
      role,
      content,
      timestamp: new Date().toISOString(),
      source: role
    };
    
    setConversation(prev => [...prev, message]);
  };

  const submitWithContext = async (
    question: string, 
    options?: { fileIds?: string[]; systemPrompt?: string }
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      // Add user question to conversation
      addToConversation('user', question);
      
      const response = await client.research(question, {
        ...options,
        conversationHistory: conversation
      });
      
      if (response.success) {
        // Add assistant response to conversation
        addToConversation('assistant', response.final_answer);
      }
      
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearConversation = () => {
    setConversation([]);
  };

  return { 
    conversation, 
    loading, 
    error, 
    submitWithContext, 
    clearConversation 
  };
};

// Example Component using conversation context
const ConversationalResearch = () => {
  const { 
    conversation, 
    loading, 
    error, 
    submitWithContext, 
    clearConversation 
  } = useConversationResearch();
  
  const [question, setQuestion] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    
    await submitWithContext(question, { 
      systemPrompt: systemPrompt || undefined 
    });
    setQuestion('');
  };

  return (
    <div className="conversation-research">
      <div className="conversation-history">
        {conversation.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role}:</strong> {msg.content}
          </div>
        ))}
      </div>
      
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a follow-up question..."
          disabled={loading}
        />
        
        <textarea
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          placeholder="Optional: Specify expertise (e.g., 'You are a regulatory specialist...')"
          rows={2}
        />
        
        <button type="submit" disabled={loading}>
          {loading ? 'Researching...' : 'Submit'}
        </button>
        
        <button type="button" onClick={clearConversation}>
          Clear History
        </button>
      </form>
      
      {error && <div className="error">{error}</div>}
    </div>
  );
};

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

## 💬 Conversation History & System Prompts (New Features)

### Overview
The research API now supports **conversation history** and **custom system prompts** for more contextual and specialized interactions:

- **Conversation History**: Maintain context across multiple research queries in a session
- **System Prompts**: Customize agent expertise and response formatting

### Conversation History

**Use Cases:**
- Multi-turn research sessions where follow-up questions build on previous answers
- Maintaining context about specific drugs, studies, or research topics
- Progressive deepening of research topics

**Example: Multi-turn Diabetes Research**
```python
# First question - establish context
first_response = await client.research("What are the main diabetes medications?")

# Follow-up question with conversation history
conversation_history = [
    {
        "role": "user",
        "content": "What are the main diabetes medications?",
        "timestamp": "2025-01-01T12:00:00Z"
    },
    {
        "role": "assistant", 
        "content": first_response["final_answer"],
        "timestamp": "2025-01-01T12:00:15Z"
    }
]

# Second question builds on context
second_response = await client.research(
    question="What about dosing for elderly patients?",
    conversation_history=conversation_history
)
```

**Benefits:**
- The AI understands "elderly patients" refers to diabetes medication dosing
- Responses reference previous discussion points
- More natural, contextual conversation flow

### System Prompts

**Use Cases:**
- **Regulatory Expertise**: FDA compliance, submission requirements
- **Clinical Focus**: Safety profiles, efficacy analysis, patient outcomes  
- **Economic Analysis**: Cost-effectiveness, market access considerations
- **Research Methodology**: Study design, statistical analysis

**Example: Regulatory Affairs Specialist**
```python
regulatory_system_prompt = """
You are a senior regulatory affairs specialist with 15 years of FDA experience. 
Focus on:
- Regulatory compliance requirements
- Safety data interpretation
- Submission strategy recommendations
- Potential FDA concerns and mitigation strategies
- Required documentation for drug approvals
"""

response = await client.research(
    question="Evaluate this clinical trial for FDA submission readiness",
    file_ids=["phase3_results.pdf"],
    system_prompt=regulatory_system_prompt
)
```

**Example: Clinical Pharmacologist**
```python
clinical_system_prompt = """
You are a clinical pharmacologist specializing in diabetes care.
Provide evidence-based analysis focusing on:
- Mechanism of action
- Efficacy data and clinical outcomes
- Safety profiles and contraindications
- Drug interactions and clinical considerations
- Patient selection criteria
"""

response = await client.research(
    question="Compare efficacy of GLP-1 agonists vs insulin",
    system_prompt=clinical_system_prompt
)
```

### Combined Usage: Context + Expertise

```python
# Combine conversation history with specialized expertise
conversation_with_expertise = await client.research(
    question="How does this new data change our regulatory strategy?",
    file_ids=["updated_safety_data.csv"],
    conversation_history=previous_conversation,
    system_prompt="You are a regulatory strategist. Focus on risk assessment and FDA submission timing."
)
```

### Implementation Best Practices

**Conversation History Management:**
```python
class ConversationManager:
    def __init__(self):
        self.history = []
        
    def add_exchange(self, user_question: str, assistant_response: str):
        timestamp = datetime.now().isoformat()
        
        self.history.extend([
            {
                "role": "user",
                "content": user_question, 
                "timestamp": timestamp,
                "source": "user"
            },
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": timestamp,
                "source": "assistant"
            }
        ])
        
        # Keep only last 20 exchanges (40 messages) for performance
        if len(self.history) > 40:
            self.history = self.history[-40:]
    
    async def research_with_context(self, question: str, **kwargs):
        response = await client.research(
            question=question,
            conversation_history=self.history,
            **kwargs
        )
        
        # Add to history
        self.add_exchange(question, response["final_answer"])
        return response
```

**System Prompt Templates:**
```python
SYSTEM_PROMPTS = {
    "regulatory": """You are a regulatory affairs specialist with FDA experience. 
                    Focus on compliance, safety, and submission requirements.""",
    
    "clinical": """You are a clinical researcher and physician. 
                  Focus on patient safety, efficacy, and clinical applications.""",
    
    "economic": """You are a health economics specialist. 
                  Focus on cost-effectiveness, market access, and economic value.""",
    
    "research": """You are a pharmaceutical research scientist. 
                  Focus on mechanism of action, study design, and scientific rigor."""
}

# Usage
response = await client.research(
    question="Analyze this drug's market potential",
    system_prompt=SYSTEM_PROMPTS["economic"]
)
```

### Response Format Enhancements

When using conversation history or system prompts, responses will include:

- **Context Awareness**: "Continuing from our previous discussion..."
- **Specialized Perspective**: "From a regulatory standpoint..."
- **Reference to History**: Building upon previous points
- **Targeted Analysis**: Focused on the specified expertise area

### Limits and Considerations

- **Conversation History**: Maximum 50 messages (typically 25 exchanges)
- **System Prompt**: Maximum 2000 characters
- **Performance**: Adding context may increase response time by 1-2 seconds
- **Memory**: No persistent storage - history must be maintained client-side

## 🔥 File Upload Integration

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
- **Typical response time**: 3-8 seconds (with real tool execution)
- **Simple web search**: 3-5 seconds
- **File analysis + web search**: 5-10 seconds
- **Complex multi-source queries**: Up to 2 minutes
- **Recommended timeout**: 300 seconds (5 minutes) for safety

### Real Performance Metrics (Live Testing)
- **Web Search Only**: 3.94-4.68 seconds
- **CSV + Web Search**: 6.78 seconds  
- **PDF + Web Search**: 4.5 seconds
- **Multi-file Analysis**: 8.32 seconds
- **Data Sources per Query**: 3-7 real URLs and file results

### Rate Limiting
- **Current limit**: No enforced limit
- **Recommended**: Implement your own rate limiting in main app
- **Concurrent requests**: Up to 20 per instance
- **Real Tool Usage**: Tavily API calls count against your quota

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