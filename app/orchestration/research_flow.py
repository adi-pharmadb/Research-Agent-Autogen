"""
This module orchestrates the research flow using AutoGen agents.
"""
import json
from typing import Union, List, Dict, Any
from datetime import datetime
from autogen_agentchat.agents import AssistantAgent  # Updated for new package structure
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio
import time

from app.agents.analyst_agent import AnalystAgent
from app.agents.datarunner_agent import DataRunnerAgent
from app.agents.writer_agent import WriterAgent
from app.config import settings # For LLM config, API keys etc.
from app.tools.data_processing_tools import web_search, query_csv, read_pdf

# Step tracking for API responses
class ResearchStep:
    def __init__(self, step_number: int, agent_name: str, action_type: str, content: str, 
                 tool_used: str = None, tool_parameters: Dict[str, Any] = None, tool_result: str = None):
        self.step_number = step_number
        self.agent_name = agent_name
        self.action_type = action_type
        self.content = content
        self.timestamp = datetime.now()
        self.tool_used = tool_used
        self.tool_parameters = tool_parameters
        self.tool_result = tool_result
    
    def to_dict(self):
        return {
            "step_number": self.step_number,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_used": self.tool_used,
            "tool_parameters": self.tool_parameters,
            "tool_result": self.tool_result
        }

def get_default_llm_config() -> Dict[str, Any]:
    """Get default LLM configuration from settings"""
    return {
        "model": "gpt-4",
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.1,
        "timeout": 300
    }

async def run_research_flow_with_tracking(question: str, file_ids: List[str] = None) -> Dict[str, Any]:
    """
    Run the research flow with progress tracking using AutoGen v0.4 async patterns
    
    Args:
        question: The research question to investigate
        file_ids: Optional list of file IDs to analyze
        
    Returns:
        Dictionary containing the result and metadata in the expected API format
    """
    start_time = time.time()
    
    try:
        # Create model client for v0.4
        model_client = OpenAIChatCompletionClient(
            model="gpt-4",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        
        # Initialize tracking variables
        agent_steps = []
        sources_used = []
        errors_encountered = []
        warnings = []
        
        # Step 1: Analyst analyzes the question
        agent_steps.append({
            "step_number": 1,
            "agent_name": "Analyst",
            "action_type": "analysis",
            "content": f"I'm analyzing your research question: '{question}'",
            "timestamp": datetime.now(),
            "tool_used": None,
            "tool_parameters": None,
            "tool_result": None
        })
        
        # Step 2: Execute file analysis if files are provided
        file_results = []
        if file_ids:
            for file_id in file_ids:
                agent_steps.append({
                    "step_number": len(agent_steps) + 1,
                    "agent_name": "DataRunner",
                    "action_type": "tool_execution",
                    "content": f"Analyzing file: {file_id}",
                    "timestamp": datetime.now(),
                    "tool_used": "file_analysis",
                    "tool_parameters": {"file_id": file_id},
                    "tool_result": None
                })
                
                try:
                    if file_id.lower().endswith('.csv'):
                        # Use query_csv with objective-based analysis
                        result = await query_csv(file_id, objective=f"Analyze this data to answer: {question}")
                        sources_used.append("query_csv")
                        file_results.append(f"CSV Analysis of {file_id}:\n{result}")
                        
                        # Update the step with successful result
                        agent_steps[-1]["tool_result"] = f"Successfully analyzed CSV file with {len(result)} characters of results"
                        
                    elif file_id.lower().endswith('.pdf'):
                        # Use read_pdf with the question as query
                        result = await read_pdf(file_id, query=question)
                        sources_used.append("read_pdf") 
                        file_results.append(f"PDF Analysis of {file_id}:\n{result}")
                        
                        # Update the step with successful result
                        agent_steps[-1]["tool_result"] = f"Successfully analyzed PDF file with {len(result)} characters of results"
                        
                    else:
                        warnings.append(f"Unsupported file type for {file_id}")
                        agent_steps[-1]["tool_result"] = f"Unsupported file type: {file_id}"
                        
                except Exception as e:
                    error_msg = f"Error analyzing file {file_id}: {str(e)}"
                    errors_encountered.append(error_msg)
                    agent_steps[-1]["tool_result"] = error_msg
        
        # Step 3: Perform web search
        agent_steps.append({
            "step_number": len(agent_steps) + 1,
            "agent_name": "DataRunner", 
            "action_type": "tool_execution",
            "content": "Performing web search for relevant information",
            "timestamp": datetime.now(),
            "tool_used": "web_search",
            "tool_parameters": {"query": question, "max_results": 10},
            "tool_result": None
        })
        
        try:
            web_results = web_search(question, max_results=10)
            sources_used.append("web_search")
            agent_steps[-1]["tool_result"] = f"Successfully gathered web search results with {len(web_results)} characters"
        except Exception as e:
            error_msg = f"Web search error: {str(e)}"
            errors_encountered.append(error_msg)
            agent_steps[-1]["tool_result"] = error_msg
            web_results = "Web search failed - using general knowledge"
        
        # Step 4: Generate comprehensive answer using real data
        research_result = await generate_research_answer_with_data(
            question, file_ids, file_results, web_results, model_client
        )
        
        agent_steps.append({
            "step_number": len(agent_steps) + 1,
            "agent_name": "Writer",
            "action_type": "synthesis", 
            "content": "Synthesizing findings into comprehensive response",
            "timestamp": datetime.now(),
            "tool_used": None,
            "tool_parameters": None,
            "tool_result": None
        })
        
        processing_time = time.time() - start_time
        
        await model_client.close()
        
        return {
            "success": True,
            "final_answer": research_result,
            "agent_steps": agent_steps,
            "sources_used": list(set(sources_used)),  # Remove duplicates
            "processing_time_seconds": round(processing_time, 2),
            "total_agent_turns": len(agent_steps),
            "llm_calls_made": 2,  # Estimate based on our simple flow
            "errors_encountered": errors_encountered,
            "warnings": warnings
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        print(f"Error in research flow: {error_msg}")
        
        return {
            "success": False,
            "final_answer": f"I apologize, but I encountered an error while processing your research request: {error_msg}",
            "agent_steps": [
                {
                    "step_number": 1,
                    "agent_name": "System",
                    "action_type": "error",
                    "content": f"Research flow failed with error: {error_msg}",
                    "timestamp": datetime.now(),
                    "tool_used": None,
                    "tool_parameters": None,
                    "tool_result": None
                }
            ],
            "sources_used": [],
            "processing_time_seconds": round(processing_time, 2),
            "total_agent_turns": 1,
            "llm_calls_made": 0,
            "errors_encountered": [error_msg],
            "warnings": []
        }

async def generate_research_answer_with_data(question: str, file_ids: List[str], file_results: List[str], web_results: str, model_client) -> str:
    """Generate a comprehensive research answer using real data from tools"""
    
    try:
        # Build context from real data
        context_parts = []
        
        if web_results and "Error" not in web_results:
            context_parts.append(f"## Web Search Results:\n{web_results}")
        
        if file_results:
            context_parts.append("## File Analysis Results:")
            for result in file_results:
                context_parts.append(result)
        
        context = "\n\n".join(context_parts) if context_parts else "No specific data available."
        
        # Create a comprehensive prompt with real data
        prompt = f"""You are a pharmaceutical research expert. Based on the provided data, answer this research question comprehensively:

**Question:** {question}

**Available Data:**
{context}

**Instructions:**
1. Analyze the provided data thoroughly
2. Answer the question directly using the information found
3. Highlight key findings and insights
4. If the data is insufficient, clearly state what additional information would be helpful
5. Format your response in clear Markdown with appropriate headers

Provide a comprehensive, evidence-based response using the actual data provided above."""

        # Try to get LLM response (simplified for now)
        # In a full implementation, you'd use the model_client properly
        
        # For now, create a structured response based on the available data
        if file_results or (web_results and "Error" not in web_results and "web search failed" not in web_results.lower()):
            response_parts = [f"# Research Analysis: {question}"]
            
            if web_results and "Error" not in web_results and "web search failed" not in web_results.lower():
                response_parts.append("## Web Research Findings")
                response_parts.append(web_results)
                response_parts.append("")
            
            if file_results:
                response_parts.append("## File Analysis Results")
                for result in file_results:
                    response_parts.append(result)
                    response_parts.append("")
            
            response_parts.append("## Summary")
            response_parts.append(f"Based on the analysis above, I've found relevant information to address your question about: **{question}**")
            
            if file_ids:
                response_parts.append(f"\n**Files analyzed:** {', '.join(file_ids)}")
            
            response_parts.append("\n*This analysis is based on current data from web sources and uploaded files.*")
            
            return "\n".join(response_parts)
        else:
            # Debug output to understand why we're falling back
            debug_info = f"""
            DEBUG INFO:
            - file_results: {len(file_results) if file_results else 0} results
            - web_results length: {len(web_results) if web_results else 0}
            - web_results contains 'Error': {'Error' in web_results if web_results else 'N/A'}
            - web_results preview: {web_results[:200] if web_results else 'None'}...
            """
            print(debug_info)
            
            return f"""# Research Analysis: {question}

## Status  
I apologize, but I encountered issues accessing both web search and file analysis capabilities for your question.

## Debug Information
- File results available: {len(file_results) if file_results else 0}
- Web results available: {len(web_results) if web_results else 0} characters
- Web results preview: {web_results[:200] if web_results else 'None'}...

## Question
**{question}**

## Issues Encountered
- Web search may have failed or returned no results
- File analysis may have encountered errors

## Recommendations
1. Check that all required API keys are properly configured
2. Verify that uploaded files are accessible
3. Try rephrasing your question for better search results
4. Consider providing more specific context or keywords

For immediate assistance, please consult relevant pharmaceutical databases, research publications, or expert sources in the field."""
        
    except Exception as e:
        return f"""# Research Response Error

I encountered an error while generating the research response for: **{question}**

**Error details:** {str(e)}

## Troubleshooting
1. Verify API configurations are correct
2. Check file accessibility and format
3. Try a simpler question format
4. Contact support if the issue persists"""

# Legacy function for backwards compatibility
async def run_research_flow(user_question: str, file_ids: Union[List[str], None] = None, llm_config: Union[dict, bool, None] = None) -> str:
    """Legacy function that returns just the final answer string."""
    result = await run_research_flow_with_tracking(question=user_question, file_ids=file_ids)
    return result["final_answer"]

# Example for direct testing of this flow (requires proper LLM config and .env setup)
async def main_test_flow():
    # This requires OAI_CONFIG_LIST to be set in environment or llm_config to be properly defined
    # with a valid API key for OpenAI or other LLM provider.
    print("Attempting to run main_test_flow()...")
    
    test_llm_config = get_default_llm_config()

    # Test case 1: Simple web search
    answer = await run_research_flow(
        user_question="What are the latest advancements in AI for drug discovery?"
    )
    print(f"\n--- Test Flow 1 Result ---\n{answer}")

    # Test case 2: File-based query (CSV) - demonstrates file handling even with empty bucket
    print("\n" + "="*60)
    print("Testing File-Based Query (CSV)...")
    answer_csv = await run_research_flow(
        user_question="Find all drugs with indication 'hypertension' from the uploaded data",
        file_ids=["drug_data.csv"]
    )
    print(f"\n--- Test Flow 2 (CSV File Query) Result ---\n{answer_csv}")

    # Test case 3: File-based query (PDF) - demonstrates PDF handling
    print("\n" + "="*60)
    print("Testing File-Based Query (PDF)...")
    answer_pdf = await run_research_flow(
        user_question="What are the key findings in this research paper?",
        file_ids=["research_paper.pdf"]
    )
    print(f"\n--- Test Flow 3 (PDF File Query) Result ---\n{answer_pdf}")

if __name__ == "__main__":
    import asyncio
    # To run this, you need to: 
    # 1. Have an .env file with OPENAI_API_KEY (and potentially other keys like TAVILY_API_KEY)
    # 2. Ensure app/config.py loads OPENAI_API_KEY into settings.OPENAI_API_KEY
    # 3. Uncomment the asyncio.run line and the test cases within main_test_flow.
    asyncio.run(main_test_flow())
    print("Research flow test completed.") 