import os
import google.generativeai as genai
from typing import List, Dict, Optional
import asyncio
import time
from dataclasses import dataclass
import logging
from collections import deque
import uuid  # Import uuid for generating instance IDs
from asyncio import Queue  # Add this import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@dataclass
class ThoughtStep:
    step_number: int
    description: str
    reasoning: str
    conclusion: str
    next_question: str

class RateLimiter:
    def __init__(self, max_calls: int = 3, period: float = 60):
        self.max_calls = max_calls
        self.period = period
        self.call_times = deque()

    async def wait(self):
        current_time = time.time()
        while self.call_times and current_time - self.call_times[0] >= self.period:
            self.call_times.popleft()

        if len(self.call_times) >= self.max_calls:
            wait_time = self.period - (current_time - self.call_times[0])
            logger.info(f"Rate limit reached. Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time + 1)

        self.call_times.append(current_time)


class CoTNode:
    def __init__(
        self,
        api_key: str,
        name: str,
        role: str,  # Add this parameter
        instance_id: Optional[str] = None,
        node_type: str = 'cot',
        rate_limiter: Optional[RateLimiter] = None  # Add this parameter
    ):
        if not api_key:
            raise ValueError("API key not found")
        self.name = name
        self.role = role  # Add this line
        self.api_key = api_key
        self.instance_id = instance_id if instance_id else str(uuid.uuid4())[:8]
        self.node_type = node_type
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.rate_limiter = rate_limiter if rate_limiter else RateLimiter()
        self.thought_steps: List[ThoughtStep] = []
        self.max_steps = 4
        self.chat = None
        self.message_queue = Queue()  # Add this line
        self.history = []  # Add this line

    async def start_chat(self):
        self.chat = self.model.start_chat()

    def _format_initial_prompt(self, query: str) -> str:
        return f"""
Analyze this query using recursive Chain of Thought reasoning. Focus on ONE key aspect at a time, letting each conclusion naturally lead to a new question.

Query: {query}

Format your response EXACTLY as follows:

Step 1:
Description: [Focus on ONE key aspect of the problem]
Reasoning: [Why this aspect is important and how we're analyzing it]
Conclusion: [What we've learned from this specific analysis]
Next Question: [What specific aspect should we explore next, based on this conclusion]

Keep your response focused on a single aspect. The next question should naturally arise from your conclusion.
"""

    def _format_followup_prompt(self, previous_steps: List[ThoughtStep], next_question: str) -> str:
        last_step = previous_steps[-1]

        return f"""
Based on the previous step's conclusion:
"{last_step.conclusion}"

Now analyze this follow-up question:
{next_question}

Format your response EXACTLY as follows:

Step {len(previous_steps) + 1}:
Description: [Focus on ONE key aspect raised by the question]
Reasoning: [Why this aspect is important and how it connects to previous conclusions]
Conclusion: [What we've learned from this specific analysis]
Next Question: [What specific aspect should we explore next, based on this conclusion]

If this seems like a natural endpoint, write "FINAL STEP" in the Next Question field.
"""

    def _parse_step(self, response: str, step_number: int) -> Optional[ThoughtStep]:
        try:
            lines = response.split('\n')
            current_field = None
            fields = {
                'description': [],
                'reasoning': [],
                'conclusion': [],
                'next_question': []
            }

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                lower_line = line.lower()
                if 'description:' in lower_line:
                    current_field = 'description'
                    line = line.split(':', 1)[1].strip()
                elif 'reasoning:' in lower_line:
                    current_field = 'reasoning'
                    line = line.split(':', 1)[1].strip()
                elif 'conclusion:' in lower_line:
                    current_field = 'conclusion'
                    line = line.split(':', 1)[1].strip()
                elif 'next question:' in lower_line:
                    current_field = 'next_question'
                    line = line.split(':', 1)[1].strip()

                if current_field and line:
                    fields[current_field].append(line)

            return ThoughtStep(
                step_number=step_number,
                description=' '.join(fields['description']),
                reasoning=' '.join(fields['reasoning']),
                conclusion=' '.join(fields['conclusion']),
                next_question=' '.join(fields['next_question'])
            )
        except Exception as e:
            logger.error(f"Error parsing step: {str(e)}")
            return None

    async def process_query(self, query: str) -> Dict:
        try:
            await self.start_chat()
            self.thought_steps = []
            # Initial step
            await self.rate_limiter.wait()
            initial_prompt = self._format_initial_prompt(query)
            response = await self.chat.send_message_async(initial_prompt)
            step = self._parse_step(response.text, 1)
            if step is None:
                return {'error': "Failed to parse initial response", 'steps': [], 'final_synthesis': ''}
            self.thought_steps.append(step)

            # Continue with follow-up steps
            while (len(self.thought_steps) < self.max_steps and
                   'FINAL STEP' not in step.next_question.upper()):
                followup_prompt = self._format_followup_prompt(
                    self.thought_steps,
                    step.next_question
                )
                response = await self.chat.send_message_async(followup_prompt)
                step = self._parse_step(response.text, len(self.thought_steps) + 1)
                if step is None:
                    break
                self.thought_steps.append(step)

            # Generate final answer
            synthesis_prompt = self._generate_synthesis_prompt(query)
            response = await self.chat.send_message_async(synthesis_prompt)
            
            # Store the raw response
            final_response = response.text
            self.history.append({
                "role": self.role,
                "text": final_response
            })
            return {
                'steps': self.thought_steps,
                'final_synthesis': final_response
            }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'error': str(e),
                'steps': self.thought_steps,
                'final_synthesis': 'An error occurred while processing the query.'
            }

    def _generate_synthesis_prompt(self, query: str) -> str:
        steps_summary = "\n".join([
            f"Step {step.step_number} Conclusion: {step.conclusion}"
            for step in self.thought_steps
        ])
        return f"""
Given the following chain of thought analysis:
{steps_summary}

Now answer this query directly: "{query}"

Respond naturally as if you are having a conversation. Do not summarize the previous steps - 
just provide your complete answer incorporating all the insights gained.
"""

    def display_step(self, step: ThoughtStep):
        print(f"\n{'='*20} Step {step.step_number} {'='*20}")
        print(f"Description: {step.description}")
        print(f"Reasoning: {step.reasoning}")
        print(f"Conclusion: {step.conclusion}")
        if 'FINAL STEP' not in step.next_question.upper():
            print(f"Next Question: {step.next_question}")
        print("="*50)

    async def receive_messages(self) -> List[Dict[str, str]]:
        """Retrieve all pending messages."""
        messages = []
        while not self.message_queue.empty():
            messages.append(await self.message_queue.get())
        return messages
