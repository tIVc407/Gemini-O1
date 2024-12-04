import json
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import cv2
import pytesseract
import threading
import os
from loguru import logger

from thinking import ProblemSolver, WorkflowStage, APICallError

import requests
import re
import base64
import pyautogui  # Added import
from collections import deque  # Add import

# Consolidate API key
API_KEY = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8"  # Replace with your actual API key

class RateLimiter:
    """Rate limiter using a token bucket algorithm."""
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()

    def wait(self):
        """Wait if necessary to enforce rate limiting."""
        current = time.time()
        time_passed = current - self.last_check
        self.last_check = current
        self.allowance += time_passed * (self.rate / self.per)
        if self.allowance > self.rate:
            self.allowance = self.rate
        if self.allowance < 1.0:
            sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
            time.sleep(sleep_time)
            self.allowance = 0.0
        else:
            self.allowance -= 1.0

class GeminiAPIClient:
    """Handles API interactions with the Gemini service."""
    def __init__(self, api_key: str):
        self.endpoint = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate=30, per=60)

    def encode_image_base64(self, image_path):
        """Encode an image to base64."""
        with open(image_path, 'rb') as f:
            image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')

    def call_gemini(self, text_prompt: str, image_path: str) -> str:
        """Make an API call to Gemini service with text and image."""
        self.rate_limiter.wait()
        base64_encoded_image = self.encode_image_base64(image_path)
        request_body = {
            "contents": [
                {
                    "parts": [
                        {"text": text_prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64_encoded_image
                            }
                        }
                    ]
                }
            ]
        }
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers=headers,
                json=request_body
            )
            if response.status_code == 429:
                logger.warning("Received 429 Too Many Requests. Sleeping for 60 seconds.")
                time.sleep(60)
                return self.call_gemini(text_prompt, image_path)  # Retry after sleep
            response.raise_for_status()
            gemini_response = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info(f"Gemini response: '{gemini_response}'")
            return gemini_response
        except Exception as e:
            logger.error(f"API call error: {str(e)}")
            raise APICallError(f"API call failed: {str(e)}") from e

# Initialize GeminiAPIClient once
api_client = GeminiAPIClient(api_key=API_KEY)

def get_ai_decision(screenshot_path, decision_type, screen_dimensions):
    # Load the screenshot
    image = cv2.imread(screenshot_path)

    if decision_type == 'move':
        prompt = f"""
        Based on the provided screenshot and the screen dimensions {screen_dimensions}, determine the pixel coordinates (x, y) where the AI should move or click.
        Please provide the coordinates in the format 'x, y'.
        """
        response = api_client.call_gemini(prompt)
        if response:
            match = re.search(r'(\d+)\s*,\s*(\d+)', response)
            if match:
                return int(match.group(1)), int(match.group(2))
        return (0, 0)
    elif decision_type == 'input':
        text = pytesseract.image_to_string(image)
        prompt = f"""
        Based on the extracted text from the screenshot and the screen dimensions {screen_dimensions}, determine what input should be entered.
        Extracted Text: {text.strip()}
        """
        response = api_client.call_gemini(prompt)
        return response.strip() if response else 'Hello World'
    return None

from selenium.webdriver.firefox.options import Options  # Updated import

import threading

# Initialize a deque to store the last 10 mouse movements
mouse_movements = deque(maxlen=10)

def record_mouse_movement(x, y):
    """Record mouse movement coordinates."""
    mouse_movements.append((x, y))

def mouse_movement(coordinates):
    """Use pyautogui to move the mouse and click."""
    x, y = coordinates
    pyautogui.moveTo(x, y)
    pyautogui.click()
    record_mouse_movement(x, y)  # Record movement

def handle_user_input(browser, screenshot_path, screen_dimensions):
    download_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
    screenshot_path = os.path.join(download_folder, 'screenshot.png')
    while True:
        try:
            task = input("Please enter a task for the AI to perform (type 'exit' to quit): ")
            if task.lower() == 'exit':
                break

            # Ensure screenshot is taken and exists
            browser.save_screenshot(screenshot_path)
            logger.info(f"Saved screenshot: {screenshot_path}")

            # Prepare the text prompt
            prompt = f"""
            Analyze the screenshot to identify relevant visual elements like buttons, text fields, and menus.
            The user requests to "{task}".
            Calculate the precise pixel coordinates for the target location on the screen.
            Provide actions in the following formats:
            - To click at coordinates: "Click at (x, y)"
            - To input text: "Type 'text' into the input field at (x, y)"
            """

            # Call Gemini API with text and image
            try:
                response = api_client.call_gemini(prompt, screenshot_path)
            except Exception as e:
                logger.error(f"Failed to get response from Gemini API: {e}")
                continue

            if response:
                if response.strip().lower() == 'done':
                    print("Gemini indicates task is done.")
                    break  # Exit the loop
                else:
                    # Process AI response to extract actions
                    match_click = re.search(r'Click at\s*\((\d+),\s*(\d+)\)', response)
                    match_type = re.search(r"Type\s*'(.*?)'\s*into the input field at\s*\((\d+),\s*(\d+)\)", response)
                    if match_click:
                        x, y = int(match_click.group(1)), int(match_click.group(2))
                        pyautogui.moveTo(x, y)
                        pyautogui.click()
                        record_mouse_movement(x, y)
                        print(f"Clicked at coordinates ({x}, {y}).")
                    elif match_type:
                        text_to_type = match_type.group(1)
                        x, y = int(match_type.group(2)), int(match_type.group(3))
                        pyautogui.moveTo(x, y)
                        pyautogui.click()
                        pyautogui.write(text_to_type)
                        record_mouse_movement(x, y)
                        print(f"Typed '{text_to_type}' into input field at ({x}, {y}).")
                    else:
                        print("Could not parse actions from the AI response.")
            else:
                print("Failed to get a response from the AI.")

            # Take a screenshot after task
            new_screenshot_path = os.path.join(download_folder, 'screenshot_after_task.png')
            try:
                browser.save_screenshot(new_screenshot_path)
                logger.info("Screenshot taken after task execution.")
            except Exception as e:
                logger.error(f"Failed to save screenshot after task: {e}")

            time.sleep(5)  # Wait 5 seconds before next iteration
        except Exception as e:
            logger.error(f"Error in user input thread: {str(e)}")
            break
        
def main():
    logger.info("Starting Gemini-O1-Control")
    firefox_options = Options()
    firefox_options.accept_insecure_certs = True  # Accept insecure certificates
    browser = webdriver.Firefox(options=firefox_options)  # Changed to Firefox
    browser.get('http://www.google.com')
    time.sleep(2)
    screen_dimensions = (browser.execute_script("return window.innerWidth"), 
                         browser.execute_script("return window.innerHeight"))
    download_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
    screenshot_path = os.path.join(download_folder, 'screenshot.png')
    browser.save_screenshot(screenshot_path)

    user_input_thread = threading.Thread(target=handle_user_input, args=(browser, screenshot_path, screen_dimensions))
    user_input_thread.start()
    user_input_thread.join()

    interaction_plan = []  # Initialize interaction plan
    execute_interactions(interaction_plan)  # Start the recursive interaction loop

    logger.info("Terminating Gemini-O1-Control")
    browser.quit()

# New Functions for Recursive Task Execution Loop and Gemini API Integration

def execute_interactions(interaction_plan):
    """Continuously prompt Gemini to open YouTube, including last 10 mouse movements."""
    while True:
        # Prepare the prompt with the last 10 mouse movements
        movements_str = ', '.join([f"({x}, {y})" for x, y in mouse_movements])
        prompt = f"""
        Please open YouTube. Here are the last 10 mouse movements: {movements_str}.
        """

        # Take a screenshot
        screenshot_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'screenshot.png')
        browser.save_screenshot(screenshot_path)

        # Call Gemini API with the prompt and screenshot
        try:
            gemini_response = api_client.call_gemini(prompt, screenshot_path)
        except Exception as e:
            logger.error(f"Failed to get response from Gemini API: {e}")
            continue

        if gemini_response.strip().lower() == 'done':
            confirm_task_completion()
            break  # Exit the loop

        # Process the AI response to get actions
        processed_actions = process_ai_response(gemini_response)

        # Execute the actions
        for action in processed_actions:
            if action['type'] == 'mouse_move':
                mouse_movement(action['coordinates'])
            elif action['type'] == 'keyboard':
                keyboard_navigation(action['text'])

        time.sleep(5)  # Wait 5 seconds before next iteration

def prepare_gemini_api_request(interaction_plan):
    return {"actions": interaction_plan}

def send_multimodal_input(gemini_request):
    try:
        return api_client.call_gemini(json.dumps(gemini_request))
    except APICallError as e:
        logger.error(f"Failed to send multi-modal input: {e}")
        return None

def receive_ai_response(gemini_response):
    return gemini_response if gemini_response else logger.error("No response received from Gemini API.")

def process_ai_response(ai_response):
    try:
        return json.loads(ai_response).get("actions", [])
    except json.JSONDecodeError:
        logger.error("Failed to decode AI response.")
        return []

def analyze_completion_status():
    return "Retry" if not check_action_logs() else "Yes"

def retry_or_escalate():
    logger.info("Attempting to retry the task.")
    logger.error("Task failed after retries. Escalating the issue.")
    provide_detailed_error_report()

def check_action_logs():
    return True  # Placeholder

def provide_user_guidance():
    logger.info("Providing user guidance for complex or impossible task.")
    print("The requested task is too complex or impossible to perform. Please provide a different request or seek further assistance.")

def confirm_task_completion():
    logger.info("Task completed successfully.")
    print("Task completed successfully.")

def provide_detailed_error_report():
    logger.info("Providing detailed error report.")
    print("Task failed after multiple attempts. Please refer to the log file for details or contact support.")

def mouse_movement(coordinates):
    """Use pyautogui to move the mouse and click."""
    x, y = coordinates
    pyautogui.moveTo(x, y)
    pyautogui.click()

def keyboard_navigation(text_to_type):
    """Use pyautogui to type text."""
    pyautogui.write(text_to_type)

def screen_element_detection(screenshot_path):
    text = pytesseract.image_to_string(cv2.imread(screenshot_path))
    logger.debug(f"Detected screen elements: {text}")
    return text.splitlines()

def identify_clickable_elements(screen_elements):
    clickable = [elem for elem in screen_elements if "button" in elem.lower()]
    logger.debug(f"Identified clickable elements: {clickable}")
    return clickable

def analyze_screen_layout(screen_elements):
    logger.debug("Analyzed layout based on detected elements.")
    return "Analyzed layout based on detected elements."

def determine_interaction_points(screen_layout):
    interaction_points = [(100, 200), (150, 250)]  # Example coordinates
    logger.debug(f"Determined interaction points: {interaction_points}")
    return interaction_points

def natural_language_processing(text_input):
    response = api_client.call_gemini(f"Process the following text for understanding: {text_input}")
    logger.debug(f"NLP processed text: {response}")
    return response

def understand_user_intent(processed_text):
    response = api_client.call_gemini(f"Determine the user's intent based on the following processed text: {processed_text}")
    logger.debug(f"User intent: {response}")
    return response

def task_decomposition(intent):
    response = api_client.call_gemini(f"Decompose the following intent into actionable tasks: {intent}")
    tasks = [task.strip() for task in response.split('\n') if task.strip()]
    logger.debug(f"Decomposed tasks: {tasks}")
    return tasks

def generate_task_sequence(tasks):
    response = api_client.call_gemini(f"Generate a sequential task plan based on the following tasks:\n{chr(10).join(tasks)}")
    task_sequence = [task.strip() for task in response.split('\n') if task.strip()]
    logger.debug(f"Generated task sequence: {task_sequence}")
    return task_sequence

def validate_task_feasibility(task_sequence):
    response = api_client.call_gemini(f"Validate the feasibility of the following task sequence:\n{chr(10).join(task_sequence)}\nIs this task sequence feasible? (yes/no)")
    feasibility = response.strip().lower() in ['yes', 'y', 'true']
    logger.debug(f"Task feasibility: {'Task Possible' if feasibility else 'Task Complex/Impossible'}")
    return "Task Possible" if feasibility else "Task Complex/Impossible"

def prepare_interaction_plan(task_sequence):
    response = api_client.call_gemini(f"Prepare an interaction plan based on the following task sequence:\n{chr(10).join(task_sequence)}")
    try:
        return json.loads(response).get("actions", [])
    except json.JSONDecodeError:
        logger.error("Failed to decode interaction plan from AI response.")
        return []

def verify_action_completion():
    logger.debug("Verifying action completion.")
    return True  # Placeholder

if __name__ == "__main__":
    main()
