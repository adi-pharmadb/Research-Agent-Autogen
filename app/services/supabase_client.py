from typing import Union
from supabase import create_client, Client
from app.config import settings # Assuming your config.py has 'settings' instance
import io

# Initialize Supabase client
supabase_client: Union[Client, None] = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        print("Supabase client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        supabase_client = None
else:
    print("Supabase URL or Key not found in settings. Supabase client not initialized.")

def get_supabase_client() -> Union[Client, None]:
    """Returns the initialized Supabase client instance."""
    return supabase_client

async def download_file_from_supabase(bucket_name: str, file_path_in_bucket: str) -> Union[bytes, None]:
    """
    Downloads a file from the specified Supabase storage bucket.

    Args:
        bucket_name: The name of the Supabase storage bucket.
        file_path_in_bucket: The path to the file within the bucket (this could be the file_id if files are stored directly by ID).

    Returns:
        The file content as bytes if successful, None otherwise.
    """
    if not supabase_client:
        print("Supabase client not initialized. Cannot download file.")
        return None

    try:
        # Note: The Supabase Python client's download method is synchronous.
        # If you need true async for this specific I/O operation with Supabase storage,
        # you might need to run it in a thread pool executor with FastAPI (e.g., using `fastapi.concurrency.run_in_threadpool`)
        # or check if the Supabase client offers an async version for storage operations (common for HTTP-based clients).
        # For simplicity, we use the direct sync call here.
        response = supabase_client.storage.from_(bucket_name).download(file_path_in_bucket)
        if response:
            # The response from download is the file content in bytes
            print(f"Successfully downloaded file '{file_path_in_bucket}' from bucket '{bucket_name}'.")
            return response
        else:
            print(f"Failed to download file '{file_path_in_bucket}' from bucket '{bucket_name}'. Response was empty.")
            return None
    except Exception as e:
        print(f"Error downloading file '{file_path_in_bucket}' from Supabase bucket '{bucket_name}': {e}")
        return None

# Example usage (for testing this module directly)
async def main_test():
    if supabase_client:
        print("Testing Supabase file download...")
        # Replace with your actual bucket name and a test file path
        # For example, if your files are in a bucket named 'research_files'
        # and identified by a file_id like 'example_csv_001.csv'
        # BUCKET = "research_files"
        # FILE_ID = "test.txt" # Replace with a real file_id/path in your bucket for testing

        # For this example, let's assume you have a bucket 'test_bucket'
        # and a file 'hello.txt' with content "Hello Supabase" in it.
        # You would need to create this manually in your Supabase storage for the test to pass.

        # Create a dummy file for upload (if you want to test upload)
        # try:
        #     content = b"Hello Supabase from Python client!"
        #     file_options = {"content-type": "text/plain"}
        #     upload_response = supabase_client.storage.from_("test-bucket-pharmadb").upload("test_upload.txt", io.BytesIO(content), file_options=file_options)
        #     print(f"Upload response: {upload_response}")
        # except Exception as e:
        #     print(f"Error uploading test file: {e}")


        # file_content = await download_file_from_supabase(bucket_name="test-bucket-pharmadb", file_path_in_bucket="test_upload.txt")
        # if file_content:
        #     print(f"File content: {file_content.decode()}")
        # else:
        #     print("Could not retrieve file for test.")
        pass # Keep it passive for now, actual test requires .env and bucket setup
    else:
        print("Supabase client not available for testing.")

if __name__ == "__main__":
    import asyncio
    # To run this test, you'll need to have your .env file set up with Supabase credentials
    # and ensure the test bucket/file exists.
    # Create a .env file in the root with your SUPABASE_URL and SUPABASE_KEY
    # Example .env:
    # SUPABASE_URL="https://your-project-ref.supabase.co"
    # SUPABASE_KEY="your-anon-key"

    # Note: Running asyncio like this is mainly for standalone script testing.
    # In FastAPI, it handles the event loop.
    # asyncio.run(main_test())
    print("Supabase client module loaded. Run with asyncio.run(main_test()) for a manual test if desired (requires .env and bucket/file setup).") 