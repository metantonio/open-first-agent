from flask import Flask, request, jsonify, render_template
import os
import sys
import logging
import asyncio
from queue import Queue
from dotenv import load_dotenv
from universal_orchestrator import orchestrator
from terminal_manager import terminal_manager
from pathlib import Path
import nest_asyncio
import threading

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Verify and export critical environment variables
if not os.getenv('OPENAI_API_KEY'):
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

# Ensure OPENAI_API_KEY is explicitly set in the environment
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Command and output queues
command_queue = Queue()
output_queue = Queue()

async def process_message(message, mode):
    try:
        logger.info(f"Processing message: {message} in mode: {mode}")
        if mode == "terminal":
            # Remove the '!' prefix if it exists
            if message.startswith('!'):
                message = message[1:]  # Remove the '!' prefix

            if message.lower() == "exit":
                return "exit_terminal"
            elif message.lower() == "clear":
                return "clear_screen"
            else:
                # Execute the command without the '!' prefix
                result = await terminal_manager.execute_command(message)
                return result or "Command executed successfully"
        else:
            logger.info("Calling orchestrator.process_request")
            response = await orchestrator.process_request(message)
            logger.info(f"Orchestrator response: {response}")
            return response
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return f"Error: {str(e)}"

async def process_commands():
    while True:
        #logger.info("Checking command queue...")
        if not command_queue.empty():
            command, mode = command_queue.get()
            #logger.info(f"Command dequeued: {command}, mode: {mode}")
            result = await process_message(command, mode)
            #logger.info(f"Processed command: {command}, result: {result}")
            output_queue.put(result)
            #logger.info(f"Result added to output queue: {result}")
        await asyncio.sleep(2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
async def send():
    data = request.get_json()
    command = data.get('command')
    mode = data.get('mode')
    logger.info(f"Received command: {command}, mode: {mode}")
    command_queue.put((command, mode))
    logger.info(f"Command added to queue: {command}, mode: {mode}")
    return jsonify({"status": "Command received"})

@app.route('/output', methods=['GET'])
async def output():
    #logger.info("Output endpoint called")
    if not output_queue.empty():
        output = output_queue.get()
        logger.info(f"Sending output: {output}")
        return jsonify({"output": output})
    return jsonify({"output": None})

@app.route('/stop', methods=['POST'])
async def stop():
    logger.info("Stopping command processing...")
    # Here you might want to implement a way to stop the processing loop
    logger.info("Command processing stopped.")
    return jsonify({"status": "Processing stopped"})

async def handle_request(request):
    try:
        result = await orchestrator.process_request(request)  # Ensure this is awaited
        return result
    except Exception as e:
        logger.error(f"Error in explanation workflow: {str(e)}")
        return f"Error: {str(e)}"

def start_processing_loop():
    asyncio.run(process_commands())

if __name__ == "__main__":
    # Start the command processing loop in a separate thread
    processing_thread = threading.Thread(target=start_processing_loop)
    processing_thread.start()
    
    try:
        app.run(port=3000, debug=True)
    except KeyboardInterrupt:
        logger.info("Shutting down the server...")
        logger.info("Server shut down gracefully.") 