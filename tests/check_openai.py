import os
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_ORIG")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables.") 
print(f"Environment OpenAI API Key: {OPENAI_API_KEY}")

# Hard-coded API key
hardcoded_api_key = ""  # insert api key here

#client = OpenAI(api_key=hardcoded_api_key)
client = OpenAI(api_key=OPENAI_API_KEY)

def test_openai_chat(model="gpt-4o-mini"):
    try:
        messages = [{"role": "user", "content": "Tell me a knock knock joke about science."}]
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        if response:
            print("API chat response:", response.choices[0].message.content)
            print("API connection successful!")
        else:
            print("Failed to get a valid response from the API")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("API connection failed.")

# Run the test
if __name__ == "__main__":
    test_openai_chat()
