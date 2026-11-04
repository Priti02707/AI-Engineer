import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
my_api_key = os.getenv("GROQ_API_KEY")

if not my_api_key:
    raise ValueError("GROQ_API_KEY environment variable is not set.")

client = Groq(api_key=my_api_key)

model = os.getenv("GROQ_MODEL", "").strip() or "openai/gpt-oss-20b"
role = "user"

# structure it
from pydantic import BaseModel
class Ticket(BaseModel):
    name:str
    email:str
    issue:str

schema= Ticket.model_json_schema()

response_format={
    "type": "json_object"
}
system_prompt=f"""
Extract the personal information from the ticket based on this schema and give a json output.
{schema}
"""

message_system={
    "role":"system",
    "content": system_prompt
}

text = "My name is Casey Morgan. My keyboard disconnects after sleep. Email me at casey@example.com."
prompt=f"""
This is a customer ticket. Please extract the personal information from this.
{text}
"""
# message me role and content
message = {
    "role": role,
    "content": prompt
}

messages = [message_system,message]
response = client.chat.completions.create(model=model, messages=messages, response_format=response_format)


answer=(response.choices[0].message.content)
print(answer)


# isko padhate kaise hai
import json
raw_json=answer
data_file=json.loads(raw_json)
ticket=Ticket(**data_file)

print(ticket.name)
print(ticket.email)
print(ticket.issue)






