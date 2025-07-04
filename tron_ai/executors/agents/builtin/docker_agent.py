# Third-party imports
from adalflow.core.func_tool import FunctionTool
from adalflow.core.tool_manager import ToolManager
import subprocess

# Local imports
from tron_ai.executors.agents.models.agent import Agent
from tron_ai.prompts.models import Prompt
from tron_ai.utils import json as json


# Docker Management Tools
def list_containers(all: bool = True) -> dict:
    """
    Lists Docker containers with minimal information.

    Args:
        all (bool): Whether to include stopped containers

    Returns:
        dict: Container list with details
    """
    try:
        # Optimized: Use a Go template to fetch only essential fields
        # This significantly reduces the amount of data transferred
        json_format = '{"id":"{{.ID}}", "name":"{{.Names}}", "image":"{{.Image}}", "status":"{{.Status}}"}'
        cmd = ["docker", "ps"]
        if all:
            cmd.append("-a")
        cmd.extend(["--format", json_format])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": f"Failed to list containers: {result.stderr}"}

        # Optimized: Use list comprehension instead of loop with append
        containers = [
            json.loads(line) for line in result.stdout.splitlines() if line.strip()
        ]

        return {"containers": containers}
    except Exception as e:
        return {"error": f"Failed to list containers: {str(e)}"}


def create_container(
    image: str,
    name: str = None,
    ports: list = None,
    env: list = None,
    volumes: list = None,
) -> dict:
    """
    Creates a new Docker container.

    Args:
        image (str): Docker image name
        name (str): Container name
        ports (list): Port mappings (e.g. ["8080:80"])
        env (list): Environment variables (e.g. ["KEY=VALUE"])
        volumes (list): Volume mappings (e.g. ["/host:/container"])

    Returns:
        dict: Operation result
    """
    try:
        cmd = ["docker", "run", "-d"]

        if name:
            cmd.extend(["--name", name])

        # Optimized: Use list comprehension instead of loops
        # Build all optional arguments efficiently
        port_args = [arg for port in (ports or []) for arg in ["-p", port]]
        env_args = [arg for var in (env or []) for arg in ["-e", var]]
        volume_args = [arg for vol in (volumes or []) for arg in ["-v", vol]]

        # Extend command with all arguments at once
        cmd.extend(port_args + env_args + volume_args)
        cmd.append(image)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": f"Failed to create container: {result.stderr}"}

        return {"container_id": result.stdout.strip()}
    except Exception as e:
        return {"error": f"Failed to create container: {str(e)}"}


def start_container(container: str) -> dict:
    """
    Starts a Docker container.

    Args:
        container (str): Container ID or name

    Returns:
        dict: Operation result
    """
    try:
        result = subprocess.run(
            ["docker", "start", container], capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"error": f"Failed to start container: {result.stderr}"}

        return {"success": True, "message": f"Container started: {container}"}
    except Exception as e:
        return {"error": f"Failed to start container: {str(e)}"}


def stop_container(container: str) -> dict:
    """
    Stops a Docker container.

    Args:
        container (str): Container ID or name

    Returns:
        dict: Operation result
    """
    try:
        result = subprocess.run(
            ["docker", "stop", container], capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"error": f"Failed to stop container: {result.stderr}"}

        return {"success": True, "message": f"Container stopped: {container}"}
    except Exception as e:
        return {"error": f"Failed to stop container: {str(e)}"}


def remove_container(container: str, force: bool = False) -> dict:
    """
    Removes a Docker container.

    Args:
        container (str): Container ID or name
        force (bool): Force removal of running container

    Returns:
        dict: Operation result
    """
    try:
        cmd = ["docker", "rm"]
        if force:
            cmd.append("-f")
        cmd.append(container)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": f"Failed to remove container: {result.stderr}"}

        return {"success": True, "message": f"Container removed: {container}"}
    except Exception as e:
        return {"error": f"Failed to remove container: {str(e)}"}


def get_container_logs(container: str, tail: int = None) -> dict:
    """
    Gets logs from a Docker container.

    Args:
        container (str): Container ID or name
        tail (int): Number of lines to show from the end

    Returns:
        dict: Container logs
    """
    try:
        cmd = ["docker", "logs"]
        if tail:
            cmd.extend(["--tail", str(tail)])
        cmd.append(container)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": f"Failed to get container logs: {result.stderr}"}

        return {"logs": result.stdout}
    except Exception as e:
        return {"error": f"Failed to get container logs: {str(e)}"}


def inspect_container(container: str) -> dict:
    """
    Gets detailed information about a Docker container.

    Args:
        container (str): Container ID or name

    Returns:
        dict: Container details
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", container], capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"error": f"Failed to inspect container: {result.stderr}"}

        return {"info": json.loads(result.stdout)}
    except Exception as e:
        return {"error": f"Failed to inspect container: {str(e)}"}


def run_docker_command(command: str) -> dict:
    """
    Executes an arbitrary Docker command.

    Args:
        command (str): Docker command to execute (must start with 'docker')

    Returns:
        dict: Command execution result
    """
    try:
        # Validate command starts with docker
        if not command.strip().startswith("docker"):
            return {"error": 'Command must start with "docker"'}

        # Split command into args and run
        cmd_args = command.strip().split()
        result = subprocess.run(cmd_args, capture_output=True, text=True)

        if result.returncode != 0:
            return {"error": f"Command failed: {result.stderr}"}

        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}

    except Exception as e:
        return {"error": f"Failed to execute command: {str(e)}"}


# Create tool manager with Docker management tools
docker_tools = ToolManager(
    tools=[
        FunctionTool(fn=list_containers),
        FunctionTool(fn=create_container),
        FunctionTool(fn=start_container),
        FunctionTool(fn=stop_container),
        FunctionTool(fn=remove_container),
        FunctionTool(fn=get_container_logs),
        FunctionTool(fn=inspect_container),
        FunctionTool(fn=run_docker_command),
    ]
)


class DockerAgent(Agent):
    """Docker container management agent."""

    def __init__(self):
        super().__init__(
            name="Docker Manager",
            description="Manages Docker containers and container lifecycle",
            prompt=Prompt(
                text="""You are a Docker operations expert.

Your responsibilities include:
1. Container Lifecycle Management
   - Create and run containers
   - Start and stop containers
   - Remove containers when needed
   - Monitor container status

2. Container Configuration
   - Set up port mappings
   - Configure environment variables
   - Manage volume mounts
   - Handle container naming

3. Container Monitoring
   - Check container status
   - View container logs
   - Inspect container details
   - Monitor resource usage

4. Security Best Practices
   - Validate container configurations
   - Check for exposed ports
   - Verify volume permissions
   - Monitor container health

5. Error Handling
   - Handle container failures
   - Manage startup issues
   - Debug container problems
   - Provide error reporting

6. Resource Management
   - Monitor container resources
   - Handle container cleanup
   - Manage container lifecycle
   - Optimize container performance
   - Prioritize fetching minimal data to reduce overhead

Always follow these security practices:
- Validate container configurations
- Check port exposures
- Verify volume mounts
- Use secure defaults
- Implement proper error handling
- Log all critical operations
- Handle cleanup properly"""
            ),
            tool_manager=docker_tools,
        )
