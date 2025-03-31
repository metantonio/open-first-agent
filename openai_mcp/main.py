import asyncio
import os
import shutil
import logging
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from dotenv import load_dotenv
from .config import get_model_config
import traceback

load_dotenv()

logger = logging.getLogger(__name__)

# Ensure output directory exists for logs
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
model = get_model_config()  # Ensure model is fetched here

async def run(mcp_server: MCPServer, request: str = ""):
    agent = Agent(
        name="File Assistant",
        instructions=f"Use the tools to read the filesystem and answer questions based on those files.",
        model=model,
        mcp_servers=[mcp_server],
    )

    result = await Runner.run(starting_agent=agent, input=request)
    #print(result.final_output)
    return result.final_output
    # Test:
    """  message = "Read the files and list them."
    print(f"Running: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # Ask about books
    message = "What is my #1 favorite book?"
    print(f"\n\nRunning: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # Ask a question that reads then reasons.
    message = "Look at my favorite songs. Suggest one new song that I might like."
    print(f"\n\nRunning: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output) """


async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "./sample_files")
    logger.info(f"sample directory: {samples_dir}")
    print(f"sample directory: {samples_dir}")
    async with MCPServerStdio(
        name="Filesystem Server, via npx",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir, OUTPUT_DIR],
        },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="MCP Filesystem Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/{trace_id}\n")
            await run(server)

async def run_workflow(request: str) -> str:
    logger.info(f"request to the MCP file system: {request}")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "../output")

    async with MCPServerStdio(
        name="Filesystem Server, via npx",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir, OUTPUT_DIR],
        },
    ) as server:
        """ trace_id = gen_trace_id()
        with trace(workflow_name="MCP Filesystem Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/{trace_id}\n")
            response = await run(server, request)  # Capturar la respuesta aquí
            print(response)
            logger.info(f"MCP response: {response}")
            return response """
            #return response.final_output  # Retornar el output final
        response = await run(server, request)  # Capturar la respuesta aquí
        print(response)
        logger.info(f"MCP response: {response}")
        return response

if __name__ == "__main__":
    # Let's make sure the user has npx installed
    if not shutil.which("npx"):
        raise RuntimeError("npx is not installed. Please install it with `npm install -g npx`.")

    asyncio.run(main())
