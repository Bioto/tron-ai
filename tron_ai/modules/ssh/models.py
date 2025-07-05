from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SSHConnectionConfig:
    """
    Configuration for an SSH connection.
    """
    hostname: str
    username: str
    password: Optional[str] = None
    key_filename: Optional[str] = None
    port: int = 22
    timeout: int = 10

@dataclass(frozen=True)
class SSHCommandResult:
    """
    Result of an SSH command execution.
    """
    output: str
    error: str
    exit_code: int 