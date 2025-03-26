from flask import Flask, request, jsonify
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    data = request.get_json()
    logger.info(f"Received MCP data: {data}")
    
    # Process the MCP data here
    response_data = {"status": "success", "message": "Data received"}
    
    return jsonify(response_data)

if __name__ == "__main__":
    app.run(port=4000, debug=True) 