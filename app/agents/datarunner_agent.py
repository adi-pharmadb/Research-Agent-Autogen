from autogen import UserProxyAgent
from app.tools import data_processing_tools # Import the module

class DataRunnerAgent(UserProxyAgent):
    def __init__(self, name="PharmaDB_DataRunner", llm_config=None, **kwargs):
        system_message = (
            "You are a DataRunner agent. Your role is to execute specific data processing functions based on instructions. "
            "You have access to tools for querying CSVs, reading PDFs, and searching the web. "
            "You will receive function call requests (or messages that can be mapped to function calls) and you should execute them. "
            "Ensure you have the exact function name: query_csv, read_pdf, or web_search. "
            "Return the direct output of the function call, whether it's data or an error message."
        )
        
        # Prepare the function map
        # The keys in this map are what the AnalystAgent might call (or what its messages can be parsed into)
        # The values are the actual functions to execute.
        current_function_map = {
            data_processing_tools.query_csv.__name__: data_processing_tools.query_csv,
            data_processing_tools.read_pdf.__name__: data_processing_tools.read_pdf,
            data_processing_tools.web_search.__name__: data_processing_tools.web_search,
        }

        super().__init__(
            name=name,
            system_message=system_message,
            human_input_mode="NEVER",
            llm_config=llm_config, # Can be False
            function_map=current_function_map, # Register the functions
            code_execution_config=False,
            **kwargs
        )

# Example usage (for testing, will be part of orchestration later):
if __name__ == '__main__':
    try:
        data_runner = DataRunnerAgent(llm_config=False) 
        print(f"DataRunner Agent {data_runner.name} initialized.")
        print(f"Registered functions: {list(data_runner.function_map.keys())}")

        # Test calling a registered function (how AutoGen might do it internally based on a message)
        # This is a direct call for testing, not how it works in a chat
        if "query_csv" in data_runner.function_map:
            print("\nSimulating call to query_csv via function_map:")
            result = data_runner.function_map["query_csv"](file_id="test.csv", sql_query="SELECT * FROM DUMMY")
            print(f"Result: {result}")
        
        if "web_search" in data_runner.function_map:
            print("\nSimulating call to web_search via function_map:")
            # Ensure .env has TAVILY_API_KEY for this to not return an error string
            result = data_runner.function_map["web_search"](query="AI in pharma")
            print(f"Result: {result}")

    except Exception as e:
        print(f"Error in DataRunnerAgent example: {e}") 