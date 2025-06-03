"""
This module orchestrates the research flow using AutoGen agents.
"""
import json
from typing import Union, List, Dict, Any
from datetime import datetime
from autogen_agentchat import UserProxyAgent, ConversableAgent # Updated for new package structure
import asyncio

from app.agents.analyst_agent import AnalystAgent
from app.agents.datarunner_agent import DataRunnerAgent
from app.agents.writer_agent import WriterAgent
from app.config import settings # For LLM config, API keys etc.

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

# Setup for LLM configuration
def get_default_llm_config():
    if settings.OPENAI_API_KEY:
        return {
            "config_list": [
                {
                    "model": "gpt-3.5-turbo", # Or "gpt-4o", "gpt-4-turbo", etc.
                    "api_key": settings.OPENAI_API_KEY,
                }
            ],
            "temperature": 0.1, # Lower temperature for more deterministic tool usage
            "timeout": 120, # Timeout for API calls
            # "cache_seed": 42, # for reproducibility, can be None
        }
    else:
        print("Warning: OPENAI_API_KEY not found in settings. LLM-dependent agents will use DEFAULT_LLM_CONFIG (False).")
        return False

DEFAULT_LLM_CONFIG = get_default_llm_config()

async def run_research_flow_with_tracking(user_question: str, file_ids: Union[List[str], None] = None, llm_config: Union[dict, bool, None] = None) -> Dict[str, Any]:
    """
    Enhanced research flow that captures detailed step-by-step agent reasoning.
    
    Returns:
        Dict containing final_answer, agent_steps, sources_used, errors, etc.
    """
    start_time = datetime.now()
    step_counter = 0
    agent_steps = []
    sources_used = set()
    errors_encountered = []
    warnings = []
    llm_calls_made = 0
    
    def add_step(agent_name: str, action_type: str, content: str, tool_used: str = None, 
                 tool_parameters: Dict[str, Any] = None, tool_result: str = None):
        nonlocal step_counter
        step_counter += 1
        step = ResearchStep(step_counter, agent_name, action_type, content, tool_used, tool_parameters, tool_result)
        agent_steps.append(step)
        return step
    
    print(f"--- Enhanced Research Flow for: '{user_question}' with files: {file_ids} ---")
    
    add_step("System", "initialization", f"Starting research flow for question: '{user_question}' with files: {file_ids}")

    if not llm_config:
        error_msg = "LLM configuration is not set. Agents requiring LLM will not function correctly."
        print(f"Warning: {error_msg}")
        warnings.append(error_msg)

    try:
        # 1. Initialize Agents
        add_step("System", "agent_initialization", "Initializing Analyst, DataRunner, and Writer agents")
        analyst = AnalystAgent(llm_config=llm_config)
        data_runner = DataRunnerAgent(llm_config=False) # DataRunner might not need LLM if Analyst provides perfect calls
        writer = WriterAgent(llm_config=llm_config)

        # 2. Create a UserProxyAgent to manage the conversation
        user_proxy = UserProxyAgent(
            name="UserProxy_Manager",
            human_input_mode="NEVER",
            llm_config=False, # Doesn't need to make LLM calls itself for this flow
            code_execution_config=False, # No code execution for the manager itself
        )

        # Construct the initial message for the Analyst
        initial_task = f"Research Question: {user_question}"
        if file_ids:
            initial_task += f"\nRelevant File IDs: {json.dumps(file_ids)}"
        initial_task += "\nPlease analyze the question and determine the first data processing step."

        add_step("UserProxy_Manager", "task_initiation", f"Sending initial task to Analyst: {initial_task}")

        # Conversation loop settings
        max_conversation_turns = 7 # Max rounds between user_proxy and analyst to prevent infinite loops
        current_turn = 0
        final_answer_from_writer = "Error: Could not generate an answer through the research flow."

        # Start the conversation with the Analyst
        print(f"\n[UserProxy_Manager to Analyst]: {initial_task}")
        current_conversant: ConversableAgent = analyst # Type hint for clarity
        message_to_send = initial_task

        while current_turn < max_conversation_turns:
            current_turn += 1
            print(f"\n--- Turn {current_turn} ---")
            
            add_step("System", "conversation_turn", f"Starting conversation turn {current_turn} with {current_conversant.name}")

            # Send message from user_proxy to the current conversant (Analyst or Writer)
            llm_calls_made += 1
            await user_proxy.a_initiate_chat(
                recipient=current_conversant,
                message=message_to_send,
                max_turns=1, # We want one response at a time to control the flow
                silent=False # For debugging, set to True later
            )
            
            analyst_response_msg = user_proxy.last_message(current_conversant)
            if not analyst_response_msg or not analyst_response_msg.get("content"):
                error_msg = f"{current_conversant.name} did not provide a response."
                final_answer_from_writer = f"Error: {error_msg}"
                errors_encountered.append(error_msg)
                add_step(current_conversant.name, "error", error_msg)
                break
            
            analyst_response_content = analyst_response_msg["content"].strip()
            print(f"[{current_conversant.name} to UserProxy_Manager]: {analyst_response_content}")
            
            add_step(current_conversant.name, "response", analyst_response_content)

            # Try to parse the analyst's response as JSON (as per Analyst system prompt)
            try:
                action_json = json.loads(analyst_response_content)
                tool_name = action_json.get("tool_name")
                parameters = action_json.get("parameters", {})

                if tool_name in ["query_csv", "read_pdf", "web_search"]:
                    print(f"[UserProxy_Manager]: Analyst requested tool: {tool_name} with params: {parameters}")
                    sources_used.add(tool_name)
                    
                    add_step("UserProxy_Manager", "tool_request", f"Analyst requested tool: {tool_name}", 
                            tool_used=tool_name, tool_parameters=parameters)
                    
                    if tool_name not in data_runner.function_map:
                        error_msg = f"DataRunner does not have tool '{tool_name}'. Available: {list(data_runner.function_map.keys())}"
                        tool_result = f"Error: {error_msg}"
                        errors_encountered.append(error_msg)
                    else:
                        # Execute the tool using DataRunner's function_map
                        tool_function = data_runner.function_map[tool_name]
                        try:
                            # Add query context for read_pdf to enable intelligent processing
                            if tool_name == "read_pdf" and "query" not in parameters:
                                parameters["query"] = user_question
                            
                            # Properly await async tool functions
                            if asyncio.iscoroutinefunction(tool_function):
                                tool_result = await tool_function(**parameters)
                            else:
                                tool_result = tool_function(**parameters)
                        except TypeError as te:
                            error_msg = f"Incorrect parameters for tool '{tool_name}'. Details: {te}"
                            tool_result = f"Error: {error_msg}"
                            errors_encountered.append(error_msg)
                        except Exception as e:
                            error_msg = f"Error executing tool '{tool_name}': {e}"
                            tool_result = f"Error: {error_msg}"
                            errors_encountered.append(error_msg)
                    
                    print(f"[DataRunner result for {tool_name}]: {tool_result}")
                    add_step("DataRunner", "tool_execution", f"Executed {tool_name}", 
                            tool_used=tool_name, tool_parameters=parameters, tool_result=str(tool_result)[:500] + "..." if len(str(tool_result)) > 500 else str(tool_result))
                    
                    message_to_send = f"The tool '{tool_name}' was executed with parameters {json.dumps(parameters)}. Result: \n{tool_result}\nWhat is the next step?"
                    current_conversant = analyst # Continue conversation with Analyst
                
                elif tool_name == "final_answer":
                    summary_for_writer = parameters.get("summary", "No summary provided by Analyst.")
                    print(f"[UserProxy_Manager]: Analyst provided final summary for Writer: {summary_for_writer}")
                    
                    add_step("UserProxy_Manager", "final_summary", f"Analyst provided final summary: {summary_for_writer}")
                    
                    # Send to Writer Agent
                    llm_calls_made += 1
                    await user_proxy.a_initiate_chat(
                        recipient=writer,
                        message=f"Please synthesize the following information into a final Markdown answer for the user's original question ('{user_question}'):\n\n{summary_for_writer}",
                        max_turns=1,
                        silent=False
                    )
                    writer_response_msg = user_proxy.last_message(writer)
                    if writer_response_msg and writer_response_msg.get("content"):
                        final_answer_from_writer = writer_response_msg["content"].strip()
                        add_step("Writer", "synthesis", f"Generated final answer: {final_answer_from_writer[:200]}...")
                    else:
                        error_msg = "Writer did not provide a final answer."
                        final_answer_from_writer = f"Error: {error_msg}"
                        errors_encountered.append(error_msg)
                        add_step("Writer", "error", error_msg)
                    print(f"[Writer to UserProxy_Manager]: {final_answer_from_writer}")
                    break # End of flow
                
                else:
                    # If JSON is valid but tool_name is unknown or not a tool call
                    warning_msg = f"Analyst provided an unknown action or a conversational response: {analyst_response_content}"
                    print(f"[UserProxy_Manager]: {warning_msg}")
                    warnings.append(warning_msg)
                    add_step("UserProxy_Manager", "clarification_needed", warning_msg)
                    message_to_send = f"Your previous response was: '{analyst_response_content}'. Please respond with a valid JSON action (query_csv, read_pdf, web_search, final_answer) or ask for clarification if needed."
                    current_conversant = analyst

            except json.JSONDecodeError:
                # If response is not JSON, treat it as a conversational turn with the Analyst
                warning_msg = f"Analyst response was not valid JSON. Treating as conversational: {analyst_response_content}"
                print(f"[UserProxy_Manager]: {warning_msg}")
                warnings.append(warning_msg)
                add_step("UserProxy_Manager", "json_parsing_error", warning_msg)
                message_to_send = f"Your previous response was: '{analyst_response_content}'. Please respond with a valid JSON action (query_csv, read_pdf, web_search, final_answer) or ask for clarification if needed."
                current_conversant = analyst
            
            if current_turn >= max_conversation_turns:
                error_msg = "Max conversation turns reached and could not finalize answer."
                print(f"Reached max conversation turns.")
                if final_answer_from_writer.startswith("Error:"):
                     final_answer_from_writer = f"Error: {error_msg}"
                errors_encountered.append(error_msg)
                add_step("System", "timeout", error_msg)
                break

    except Exception as e:
        error_msg = f"Critical error in research flow: {str(e)}"
        print(f"Critical error: {error_msg}")
        errors_encountered.append(error_msg)
        add_step("System", "critical_error", error_msg)
        final_answer_from_writer = f"Error: {error_msg}"

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    print(f"--- Research Flow Ended. Final Answer: ---\n{final_answer_from_writer}")
    add_step("System", "completion", f"Research flow completed in {processing_time:.2f} seconds")
    
    return {
        "final_answer": final_answer_from_writer,
        "agent_steps": [step.to_dict() for step in agent_steps],
        "sources_used": list(sources_used),
        "processing_time_seconds": processing_time,
        "total_agent_turns": current_turn,
        "llm_calls_made": llm_calls_made,
        "errors_encountered": errors_encountered,
        "warnings": warnings,
        "success": len(errors_encountered) == 0 and not final_answer_from_writer.startswith("Error:")
    }

# Legacy function for backwards compatibility
async def run_research_flow(user_question: str, file_ids: Union[List[str], None] = None, llm_config: Union[dict, bool, None] = None) -> str:
    """Legacy function that returns just the final answer string."""
    result = await run_research_flow_with_tracking(user_question, file_ids, llm_config)
    return result["final_answer"]

# Example for direct testing of this flow (requires proper LLM config and .env setup)
async def main_test_flow():
    # This requires OAI_CONFIG_LIST to be set in environment or llm_config to be properly defined
    # with a valid API key for OpenAI or other LLM provider.
    print("Attempting to run main_test_flow()...")
    
    test_llm_config = False
    if settings.OPENAI_API_KEY: # Assuming you add OPENAI_API_KEY to your Settings class
         test_llm_config = get_default_llm_config() # Use the same logic for consistency
    else:
        print("OPENAI_API_KEY not found in settings. LLM-dependent agents might not work.")
        print("Please ensure OPENAI_API_KEY is in your .env file and app/config.py loads it.")
        return

    # Test case 1: Simple web search
    answer = await run_research_flow(
        user_question="What are the latest advancements in AI for drug discovery?",
        llm_config=test_llm_config
    )
    print(f"\n--- Test Flow 1 Result ---\n{answer}")

    # Test case 2: File-based query (CSV) - demonstrates file handling even with empty bucket
    print("\n" + "="*60)
    print("Testing File-Based Query (CSV)...")
    answer_csv = await run_research_flow(
        user_question="Find all drugs with indication 'hypertension' from the uploaded data",
        file_ids=["drug_data.csv"],
        llm_config=test_llm_config
    )
    print(f"\n--- Test Flow 2 (CSV File Query) Result ---\n{answer_csv}")

    # Test case 3: File-based query (PDF) - demonstrates PDF handling
    print("\n" + "="*60)
    print("Testing File-Based Query (PDF)...")
    answer_pdf = await run_research_flow(
        user_question="What are the key findings in this research paper?",
        file_ids=["research_paper.pdf"],
        llm_config=test_llm_config
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