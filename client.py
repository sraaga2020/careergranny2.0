from openrouter import OpenRouter
import os
from dotenv import load_dotenv
import requests


# Load .env
load_dotenv()

HACKCLUB_KEY = os.getenv("GEMINI_API_KEY")
if not HACKCLUB_KEY:
    raise ValueError("Hack Club API key not found in environment!")

client = OpenRouter(
    api_key=HACKCLUB_KEY,
    server_url="https://ai.hackclub.com/proxy/v1",
)

def gem3(prompt: str) -> str:
    try:
        response = client.chat.send(
            # Using the latest Gemini 3 model available on the proxy
            model="google/gemini-3-flash-preview",
            messages=[
                {"role": "system", "content": "You are a helpful career and college advisor for high schoolers. Always return markdown unless specifically requested for JSON or another format."},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
        # Fix: access via choices[0]
        return response.choices[0].message.content
    except Exception as e:
        return f"API Error: {str(e)}"

