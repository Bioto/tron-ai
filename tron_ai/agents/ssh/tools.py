from tron_ai.modules.ssh.tools import connect_and_run_command
from tron_ai.modules.ssh.models import SSHConnectionConfig, SSHCommandResult

class SSHAgentTools:
    @staticmethod
    def run_ssh_command(
        hostname: str,
        username: str,
        password: str = None,
        key_filename: str = None,
        port: int = 22,
        timeout: int = 10,
        command: str = "",
        session_id: str = None
    ) -> dict:
        """
        Connect to a remote server via SSH and execute a command.
        Returns a dict with output, error, and exit_code.
        """
        if False:  # Replace with actual sub-agent call check if added
            if not session_id:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("[SESSION] run_ssh_command called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "run_ssh_command called without session_id. Session tracking will break."
        config = SSHConnectionConfig(
            hostname=hostname,
            username=username,
            password=password,
            key_filename=key_filename,
            port=port,
            timeout=timeout,
        )
        result: SSHCommandResult = connect_and_run_command(config, command)

        if result is None:
            return {"error": "SSH connection or command failed."}
        return {
            "output": result.output,
            "error": result.error,
            "exit_code": result.exit_code,
        } 