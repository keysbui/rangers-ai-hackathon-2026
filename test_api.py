import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("ARK_API_KEY"),
    base_url=os.getenv("ARK_BASE_URL")
)

model_id = os.getenv("MODEL_ID")

print(f"Testing with Model ID: {model_id}")

try:
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": "Hello, are you working?"}
        ]
    )
    print("Success!")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
