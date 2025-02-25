import google.generativeai as genai
from enum import Enum

class WorkflowStage(Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"

class APICallError(Exception):
    """Exception raised for API call errors"""
    pass

class ProblemSolver:
    def __init__(self, api_key, model_type="normal"):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        # Initialize generative models based on type
        if model_type == "thinking":
            self.model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
        else:  # default to normal mode
            self.model = genai.GenerativeModel('gemini-1.5-flash')

    def solve_problem(self, message_history):
        try:
            # Get the last user message
            last_msg = message_history[-1]["content"] if message_history else ""

            # Pass message to the text model
            response = self.model.generate_content(
                contents=last_msg,
                tools={
                    "google_search_retrieval": {
                        "dynamic_retrieval_config": {}
                    }
                },
                generation_config={
                    'temperature': 0.7
                }
            )

            # Extract grounding metadata if available
            grounding_info = ""
            if hasattr(response, 'groundingMetadata') and response.groundingMetadata:
                sources = response.groundingMetadata.get('sources', [])
                if sources:
                    grounding_info = "\n\nSources:\n" + "\n".join(
                        [f"- {source['url']}" for source in sources]
                    )

            return {
                "solution": response.text + grounding_info,
                "grounding": response.groundingMetadata if hasattr(response, 'groundingMetadata') else None
            }

        except Exception as e:
            return {"error": str(e)}
