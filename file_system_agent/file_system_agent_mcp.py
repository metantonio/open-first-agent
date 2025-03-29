import asyncio
import os
import shutil
import logging
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from .config import get_model_config

model = get_model_config()
logger = logging.getLogger(__name__)

# Ensure output directory exists for logs
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
model = get_model_config()  # Ensure model is fetched here

async def run(mcp_server: MCPServer):
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to read the filesystem and answer questions based on those files.",
        model=model,
        mcp_servers=[mcp_server],
    )
    
    # Aquí se ejecuta el agente y se obtiene la respuesta
    #response = await Runner.run_sync(agent, "Process this file system request.")
    #return response  # Retornar la respuesta

async def run_workflow():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "output")

    async with MCPServerStdio(
        name="Filesystem Server, via npx",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
        },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="MCP Filesystem Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/{trace_id}\n")
            response = await run(server)  # Capturar la respuesta aquí
            return response.final_output  # Retornar el output final

if __name__ == "__main__":
    # Let's make sure the user has npx installed
    if not shutil.which("npx"):
        raise RuntimeError("npx is not installed. Please install it with `npm install -g npx`.")

    result = asyncio.run(run_workflow())  # Capturar el resultado de main
    print(result)  # Imprimir el resultado