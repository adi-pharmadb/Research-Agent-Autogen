from autogen_agentchat import AssistantAgent

class WriterAgent(AssistantAgent):
    def __init__(self, name="PharmaDB_Writer", llm_config=None, **kwargs):
        system_message = (
            "You are an expert report writer for PharmaDB. "
            "Your role is to take processed data, findings, and summaries provided to you, "
            "and synthesize them into a clear, concise, and well-formatted Markdown answer "
            "that directly addresses the user's original research question. "
            "Ensure your output is in Markdown format."
        )
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            **kwargs
        )

# Example usage (for testing, will be part of orchestration later):
if __name__ == '__main__':
    try:
        # mock_llm_config = {
        #     "model": "gpt-4", 
        #     "api_key": "YOUR_OPENAI_API_KEY" # Should be loaded from env
        # }
        # writer = WriterAgent(llm_config=mock_llm_config)
        # print(f"Writer Agent {writer.name} initialized with system message:")
        # print(writer.system_message)
        print("WriterAgent class defined. Requires LLM config for actual use.")
    except Exception as e:
        print(f"Error in WriterAgent example: {e}") 