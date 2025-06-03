import os
from typing import Union
from dotenv import load_dotenv, find_dotenv

# Attempt to load .env.local first, then .env as a fallback
# find_dotenv will search for the file. If not found, it returns an empty string,
# and load_dotenv effectively does nothing for that specific call.

# Determine the path to .env.local
dotenv_local_path = find_dotenv('.env.local', usecwd=True, raise_error_if_not_found=False)
if dotenv_local_path:
    print(f"Loading environment variables from: {dotenv_local_path}")
    load_dotenv(dotenv_path=dotenv_local_path, override=True) # Override system env vars if .env.local is present
elif find_dotenv('.env', usecwd=True, raise_error_if_not_found=False):
    dotenv_path = find_dotenv('.env', usecwd=True, raise_error_if_not_found=False)
    print(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path) # Load .env if .env.local not found
else:
    print("No .env or .env.local file found. Environment variables should be set in the system.")

# Example: Accessing an environment variable
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Add other configurations as needed

class Settings:
    PROJECT_NAME: str = "PharmaDB Deep-Research Micro-Service"
    API_V1_STR: str = "/api/v1"

    # Supabase (will be loaded from .env)
    SUPABASE_URL: Union[str, None] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Union[str, None] = os.getenv("SUPABASE_KEY")

    # Tavily API Key (will be loaded from .env)
    TAVILY_API_KEY: Union[str, None] = os.getenv("TAVILY_API_KEY")

    # OpenAI API Key (will be loaded from .env for AutoGen agents)
    OPENAI_API_KEY: Union[str, None] = os.getenv("OPENAI_API_KEY")

    # Supabase Bucket Name (will be loaded from .env)
    SUPABASE_BUCKET_NAME: Union[str, None] = os.getenv("SUPABASE_BUCKET_NAME", "pharma_research_files") # Default if not set

    # Redis (optional, will be loaded from .env if used)
    REDIS_HOST: Union[str, None] = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: Union[int, None] = int(os.getenv("REDIS_PORT", 6379)) 

settings = Settings()

# You can add functions here to validate settings or provide defaults if needed.
# def get_settings() -> Settings:
#     return Settings()

if __name__ == "__main__":
    print(f"Supabase URL: {settings.SUPABASE_URL}")
    print(f"Supabase Key: {settings.SUPABASE_KEY}")
    print(f"Tavily API Key: {settings.TAVILY_API_KEY}")
    print(f"OpenAI API Key: {settings.OPENAI_API_KEY}")
    print(f"Supabase Bucket Name: {settings.SUPABASE_BUCKET_NAME}") 