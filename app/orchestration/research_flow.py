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

async def run_research_flow_with_tracking(question: str, file_ids: List[str] = None, 
                                        conversation_history: List[Dict[str, Any]] = None,
                                        system_prompt: str = None) -> Dict[str, Any]:
    """
    Run the research flow with progress tracking using AutoGen v0.4 async patterns
    
    Args:
        question: The research question to investigate
        file_ids: Optional list of file IDs to analyze
        conversation_history: Optional previous conversation for context
        system_prompt: Optional custom system prompt to override default behavior
        
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
        
        # Process conversation history for context
        conversation_context = ""
        if conversation_history:
            context_messages = []
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                source = msg.get("source", role)
                context_messages.append(f"{source}: {content}")
            
            conversation_context = "\n".join(context_messages[-10:])  # Keep last 10 messages for context
            
            agent_steps.append({
                "step_number": 1,
                "agent_name": "Analyst",
                "action_type": "analysis",
                "content": f"Processing conversation history with {len(conversation_history)} previous messages for context",
                "timestamp": datetime.now(),
                "tool_used": None,
                "tool_parameters": {"history_length": len(conversation_history)},
                "tool_result": f"Loaded {len(conversation_history)} messages for context"
            })
        
        # Step: Analyst analyzes the question with context
        step_number = len(agent_steps) + 1
        analysis_content = f"I'm analyzing your research question: '{question}'"
        if conversation_context:
            analysis_content += f" in the context of our previous conversation"
        if system_prompt:
            analysis_content += f" using specialized expertise: {system_prompt[:100]}..."
            
        agent_steps.append({
            "step_number": step_number,
            "agent_name": "Analyst",
            "action_type": "analysis", 
            "content": analysis_content,
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
            question, file_ids, file_results, web_results, model_client,
            conversation_context=conversation_context, system_prompt=system_prompt
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

async def generate_research_answer_with_data(question: str, file_ids: List[str], file_results: List[str], web_results: str, model_client,
                                           conversation_context: str = "", system_prompt: str = None) -> str:
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
        base_system_prompt = "You are a pharmaceutical research expert. Provide detailed, evidence-based analysis of the data. Synthesize information from multiple sources to answer the question comprehensively. Focus on extracting key insights and presenting them in a clear, structured format."
        
        if system_prompt:
            # Use custom system prompt if provided
            base_system_prompt = system_prompt
        
        # Create system message with the system prompt
        system_message = {
            "role": "system",
            "content": base_system_prompt
        }
        
        # Create user message with the question and context
        user_message_parts = []
        
        if conversation_context:
            user_message_parts.append(f"## Previous Conversation Context:\n{conversation_context}\n")
        
        user_message_parts.append(f"## Research Question:\n{question}\n")
        user_message_parts.append(f"## Available Data:\n{context}\n")
        
        user_message_parts.append("## Instructions:")
        user_message_parts.append("1. Analyze the provided data thoroughly and extract key insights")
        user_message_parts.append("2. Answer the research question directly and comprehensively")
        user_message_parts.append("3. Synthesize information from all sources to form a coherent analysis")
        user_message_parts.append("4. Provide specific numbers, statistics, and facts when available")
        user_message_parts.append("5. If the data is insufficient, clearly state what information is missing")
        user_message_parts.append("6. Format your response in clear Markdown with appropriate headers")
        user_message_parts.append("7. Focus on providing actionable insights and conclusions")
        
        user_message = {
            "role": "user",
            "content": "\n".join(user_message_parts)
        }
        
        # Create the messages array for the API call
        messages = [system_message, user_message]
        
        try:
            # Actually use the model_client to get a response
            response = await model_client.create(messages=messages)
            
            # Extract the content from the response
            if response and response.choices and len(response.choices) > 0:
                analysis = response.choices[0].message.content
                return analysis
            else:
                # Fallback if the response format is unexpected
                return f"""# Research Analysis: {question}

## Analysis
I was unable to generate a comprehensive analysis due to an issue with the AI model response format.

## Question
**{question}**

## Available Data Summary
- Web search results available: {'Yes' if web_results and "Error" not in web_results else 'No'}
- File analysis results available: {'Yes' if file_results else 'No'}

Please try again or contact support if this issue persists."""
                
        except Exception as api_error:
            print(f"Error calling LLM API: {str(api_error)}")
            
            # Fallback to a simplified analysis if the API call fails
            simplified_analysis_parts = []
            
            # Add title
            simplified_analysis_parts.append(f"# Research Analysis: {question}")
            simplified_analysis_parts.append("")
            
            # Add system prompt context if specialized
            if system_prompt:
                simplified_analysis_parts.append(f"*Analysis from specialized perspective based on provided expertise*")
                simplified_analysis_parts.append("")
            
            # Add data sections
            if web_results and "Error" not in web_results:
                simplified_analysis_parts.append("## Key Information from Web Research")
                simplified_analysis_parts.append("Based on the web search results, here are the key points relevant to your question:")
                simplified_analysis_parts.append("")
                simplified_analysis_parts.append("- The search results contain information about your query but require expert analysis")
                simplified_analysis_parts.append("- I'm unable to provide that analysis due to a technical issue with our AI processing")
                simplified_analysis_parts.append("")
            
            if file_results:
                simplified_analysis_parts.append("## File Analysis")
                simplified_analysis_parts.append("Your uploaded files contain relevant data that would help answer this question.")
                simplified_analysis_parts.append("")
            
            # Add conclusion
            simplified_analysis_parts.append("## Conclusion")
            simplified_analysis_parts.append(f"I apologize, but I encountered an issue while analyzing the data for your question about **{question}**. The system was able to gather relevant information, but the AI analysis component experienced a technical problem.")
            simplified_analysis_parts.append("")
            simplified_analysis_parts.append("Please try again or contact support if this issue persists.")
            
            return "\n".join(simplified_analysis_parts)
        
    except Exception as e:
        print(f"Error in generate_research_answer_with_data: {str(e)}")
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