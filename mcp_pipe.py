"""
Simple MCP stdio <-> WebSocket pipe for Xiaozhi Robot.
Usage:
    python mcp_pipe.py server.py
"""

import asyncio
import websockets
import subprocess
import logging
import os
import sys
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_pipe.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MCP_PIPE')

# Reconnection settings
INITIAL_BACKOFF = 1
MAX_BACKOFF = 60

def update_status(status_str):
    try:
        import json
        import time
        with open("mcp_status.json", "w", encoding="utf-8") as f:
            json.dump({"status": status_str, "timestamp": time.time()}, f)
    except Exception:
        pass

async def status_heartbeat_loop(status_str):
    try:
        while True:
            update_status(status_str)
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        pass

async def pipe_websocket_to_process(websocket, process, target):
    """Read data from WebSocket and write to process stdin"""
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            logger.debug(f"[{target}] WS -> Stdin: {message.strip()}")
            process.stdin.write(message + '\n')
            process.stdin.flush()
    except Exception as e:
        logger.error(f"[{target}] Error in WebSocket to process pipe: {e}")
        raise
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()

async def pipe_process_to_websocket(process, websocket, target):
    """Read data from process stdout and send to WebSocket"""
    try:
        while True:
            # Read line asynchronously
            line = await asyncio.to_thread(process.stdout.readline)
            if not line:
                logger.info(f"[{target}] Process stdout EOF")
                break
            logger.debug(f"[{target}] Stdout -> WS: {line.strip()}")
            await websocket.send(line)
    except Exception as e:
        logger.error(f"[{target}] Error in process to WebSocket pipe: {e}")
        raise

async def pipe_process_stderr_to_terminal(process, target):
    """Read data from process stderr and print to terminal"""
    try:
        while True:
            line = await asyncio.to_thread(process.stderr.readline)
            if not line:
                break
            sys.stderr.write(f"[{target} - STDERR] {line}")
            sys.stderr.flush()
    except Exception as e:
        logger.error(f"[{target}] Error reading stderr: {e}")

async def connect_to_server(uri, target_script):
    """Connect to WebSocket server and pipe stdio to the local process"""
    logger.info(f"Connecting to WebSocket server at {uri}...")
    async with websockets.connect(uri) as websocket:
        logger.info("Successfully connected to WebSocket server")
        
        # Start server process (e.g. python server.py)
        cmd = [sys.executable, target_script]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            errors='replace',
            text=True,
            bufsize=1
        )
        logger.info(f"Started server process: {' '.join(cmd)}")
        
        heartbeat_task = asyncio.create_task(status_heartbeat_loop("connected"))
        try:
            await asyncio.gather(
                pipe_websocket_to_process(websocket, process, target_script),
                pipe_process_to_websocket(process, websocket, target_script),
                pipe_process_stderr_to_terminal(process, target_script)
            )
        finally:
            heartbeat_task.cancel()
            update_status("disconnected")
            # Cleanup process
            if process.poll() is None:
                logger.info(f"Terminating subprocess {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python mcp_pipe.py <mcp_server_script.py>")
        sys.exit(1)
        
    target_script = sys.argv[1]
    uri = os.getenv("MCP_ENDPOINT")
    if not uri:
        logger.error("MCP_ENDPOINT environment variable not set in .env")
        sys.exit(1)
        
    reconnect_attempt = 0
    backoff = INITIAL_BACKOFF
    
    while True:
        try:
            update_status("connecting")
            if reconnect_attempt > 0:
                wait_time = backoff * (1 + random.random() * 0.1)
                logger.info(f"Waiting {wait_time:.2f} seconds before reconnection attempt {reconnect_attempt}...")
                await asyncio.sleep(wait_time)
                
            await connect_to_server(uri, target_script)
            # Reset backoff on successful connection closure without error
            reconnect_attempt = 0
            backoff = INITIAL_BACKOFF
        except Exception as e:
            update_status("disconnected")
            reconnect_attempt += 1
            logger.warning(f"Connection closed/failed: {e}")
            backoff = min(backoff * 2, MAX_BACKOFF)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        update_status("stopped")
        logger.info("MCP Pipe stopped by user")
