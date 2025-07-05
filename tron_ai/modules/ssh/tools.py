from .manager import SSHManager
from .models import SSHConnectionConfig, SSHCommandResult
from typing import Optional

def connect_and_run_command(
    config: SSHConnectionConfig, command: str
) -> Optional[SSHCommandResult]:
    """
    Connects to an SSH server and runs a command. Returns SSHCommandResult or None on failure.
    """
    manager = SSHManager()
    connected = manager.connect(
        hostname=config.hostname,
        username=config.username,
        password=config.password,
        key_filename=config.key_filename,
        port=config.port,
        timeout=config.timeout,
    )
    if not connected:
        return None
    result = manager.execute_command(config.hostname, command, timeout=config.timeout)
    manager.close(config.hostname)

    if result['exit_code'] != 0:
        return SSHCommandResult(output="", error=result["error"], exit_code=-1)
    return SSHCommandResult(
        output=result["output"],
        error=result["error"],
        exit_code=result["exit_code"],
    ) 