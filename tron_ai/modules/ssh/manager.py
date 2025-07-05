import paramiko
from typing import Optional, Dict, Any

class SSHManager:
    """
    Manages SSH connections and command execution using Paramiko.
    Maintains a pool of active connections for reuse.
    """
    def __init__(self) -> None:
        self.connections: Dict[str, paramiko.SSHClient] = {}

    def connect(
        self,
        hostname: str,
        username: str,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
        timeout: int = 10,
    ) -> bool:
        """
        Establish an SSH connection and add it to the pool.
        Returns True if successful, False otherwise.
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if key_filename:
                client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    key_filename=key_filename,
                    timeout=timeout,
                )
            else:
                client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout,
                )
            self.connections[hostname] = client
            return True
        except Exception as e:
            print(f"[SSHManager] Connection failed to {hostname}: {e}")
            return False

    def execute_command(self, hostname: str, command: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Execute a command on the specified host.
        Returns a dict with output, error, and exit_code.
        """
        if hostname not in self.connections:
            return {"error": f"Not connected to host: {hostname}"}
        try:
            stdin, stdout, stderr = self.connections[hostname].exec_command(command, timeout=timeout)
            output = stdout.read().decode()
            error = stderr.read().decode()
            exit_code = stdout.channel.recv_exit_status()
            return {
                "output": output,
                "error": error,
                "exit_code": exit_code,
            }
        except Exception as e:
            return {"error": str(e)}

    def close(self, hostname: str) -> None:
        """
        Close the SSH connection to the specified host.
        """
        client = self.connections.pop(hostname, None)
        if client:
            client.close()

    def close_all(self) -> None:
        """
        Close all SSH connections.
        """
        for client in self.connections.values():
            client.close()
        self.connections.clear() 