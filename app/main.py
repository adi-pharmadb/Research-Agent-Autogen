from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
from datetime import datetime

from app.config import settings
from app.orchestration.research_flow import run_research_flow_with_tracking, get_default_llm_config

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PharmaDB Deep-Research Micro-Service using AutoGen multi-agent system",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class ResearchRequest(BaseModel):
    question: str = Field(..., description="Natural language research question", min_length=1)
    file_ids: Optional[List[str]] = Field(default=None, description="Optional list of file IDs from Supabase storage")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the latest advancements in AI for drug discovery?",
                "file_ids": ["research_paper.pdf", "drug_data.csv"]
            }
        }

# Response Models
class AgentStep(BaseModel):
    step_number: int
    agent_name: str
    action_type: str  # "analysis", "tool_execution", "synthesis", "conversation"
    content: str
    timestamp: datetime
    tool_used: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None

class ResearchResponse(BaseModel):
    success: bool
    final_answer: str = Field(..., description="Final Markdown-formatted research answer")
    
    # Agent reasoning and process details
    agent_steps: List[AgentStep] = Field(..., description="Detailed step-by-step agent reasoning process")
    sources_used: List[str] = Field(..., description="List of tools/sources used (web_search, query_csv, read_pdf)")
    
    # Metadata
    processing_time_seconds: float
    total_agent_turns: int
    llm_calls_made: int
    
    # Error information (if any)
    errors_encountered: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "final_answer": "### Latest Advancements in AI for Drug Discovery\n\nRecent developments include...",
                "agent_steps": [
                    {
                        "step_number": 1,
                        "agent_name": "PharmaDB_Analyst",
                        "action_type": "analysis",
                        "content": "I will search for latest AI advancements...",
                        "timestamp": "2025-01-01T12:00:00Z"
                    }
                ],
                "sources_used": ["web_search"],
                "processing_time_seconds": 15.34,
                "total_agent_turns": 3,
                "llm_calls_made": 5,
                "errors_encountered": [],
                "warnings": []
            }
        }

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "operational",
        "endpoints": {
            "research": "/api/v1/research",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "services": {
            "supabase": "connected" if settings.SUPABASE_URL and settings.SUPABASE_KEY else "not configured",
            "openai": "configured" if settings.OPENAI_API_KEY else "not configured",
            "tavily": "configured" if settings.TAVILY_API_KEY else "not configured"
        }
    }

@app.post("/api/v1/research", response_model=ResearchResponse, 
         summary="Research Question Processor",
         description="Submit a natural language research question with optional file IDs. The system uses multi-agent AI to analyze the question, process data from files or web sources, and return a comprehensive Markdown answer with detailed reasoning steps.")
async def research_endpoint(request: ResearchRequest):
    """
    Process a research question using the multi-agent system.
    
    This endpoint:
    1. Analyzes the research question using an AI Analyst agent
    2. Executes appropriate tools (web search, CSV queries, PDF reading) based on the question and files
    3. Synthesizes the findings into a comprehensive Markdown answer
    4. Returns detailed step-by-step reasoning and metadata
    
    **Example Questions:**
    - "What are the latest advancements in AI for drug discovery?"
    - "Find all drugs for hypertension in the uploaded dataset"
    - "Summarize the key findings from this research paper"
    """
    
    try:
        # Validate request
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Check if required services are configured
        missing_services = []
        if not settings.OPENAI_API_KEY:
            missing_services.append("OpenAI API key")
        if request.file_ids and not (settings.SUPABASE_URL and settings.SUPABASE_KEY):
            missing_services.append("Supabase configuration")
            
        if missing_services:
            raise HTTPException(
                status_code=503, 
                detail=f"Service unavailable: Missing configuration for {', '.join(missing_services)}"
            )
        
        # Get LLM configuration
        llm_config = get_default_llm_config()
        if not llm_config:
            raise HTTPException(
                status_code=503,
                detail="LLM service not properly configured"
            )
        
        # Log the request (optional)
        print(f"\n=== API Research Request ===")
        print(f"Question: {request.question}")
        print(f"File IDs: {request.file_ids}")
        print(f"Timestamp: {datetime.now()}")
        
        # Execute the research flow with detailed tracking
        research_result = await run_research_flow_with_tracking(
            user_question=request.question,
            file_ids=request.file_ids,
            llm_config=llm_config
        )
        
        # Build the response
        response = ResearchResponse(
            success=research_result["success"],
            final_answer=research_result["final_answer"],
            agent_steps=[AgentStep(**step) for step in research_result["agent_steps"]],
            sources_used=research_result["sources_used"],
            processing_time_seconds=research_result["processing_time_seconds"],
            total_agent_turns=research_result["total_agent_turns"],
            llm_calls_made=research_result["llm_calls_made"],
            errors_encountered=research_result["errors_encountered"],
            warnings=research_result["warnings"]
        )
        
        # Log the completion
        print(f"=== API Research Completed ===")
        print(f"Success: {response.success}")
        print(f"Processing time: {response.processing_time_seconds:.2f}s")
        print(f"Sources used: {response.sources_used}")
        if response.errors_encountered:
            print(f"Errors: {response.errors_encountered}")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        error_msg = f"Unexpected error in research endpoint: {str(e)}"
        print(f"ERROR: {error_msg}")
        
        # Return error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error during research processing",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        ) 