from google.auth import default
from google.auth.transport.requests import Request
import requests

class LLMClient:
    def __init__(self, model_endpoint):
        self.model_endpoint = model_endpoint
        self.credentials, _ = default()
        self.session = requests.Session()

    def generate_response(self, prompt):
        headers = {
            'Authorization': f'Bearer {self.credentials.token}',
            'Content-Type': 'application/json'
        }
        data = {
            'prompt': prompt,
            'max_tokens': 150
        }
        response = self.session.post(self.model_endpoint, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('choices')[0].get('text')

    def close(self):
        self.session.close()