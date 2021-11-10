from abc import abstractclassmethod
import subprocess
from typing import List, TypedDict
from paramiko import SSHClient, AutoAddPolicy

def escape_subcommand(command: str):
    return command.replace("\\", "\\\\").replace("'", "\\'")

class CommandResult(TypedDict):
    stderr: str
    stdout: str

class InstallConfig(TypedDict):
    computer_name: str
    root_password: str
    
    username: str
    user_password: str
    key_layout: str
    timezone: str
    lang: str

    custom_pacman_mirrors: List[str]
    additional_packages: List[str]
    kernels: List[str]

class ExecContext:
    config: InstallConfig
    primary_disk: str
    memory_size_mb: int

    def __init__(self, config: InstallConfig) -> None:
        self.config = config
        self.primary_disk = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    def exec_chroot_as_user(self, command: str, no_error: bool=True) -> CommandResult:
        final_command = "su {0} -c $\'{1}\'".format(self.config["username"], escape_subcommand(command))
        return self.exec_chroot(final_command, no_error)

    def exec_chroot(self, command: str, no_error: bool=True) -> CommandResult:
        final_command = "arch-chroot /mnt bash -c $\'{}\'".format(escape_subcommand(command))

        if no_error:
            return self.exec_no_err(final_command)
        else:
            return self.exec(final_command)

    def exec_no_err(self, command: str) -> CommandResult:
        res = self.exec(command)
        if res["stderr"]:
            print("there was an error in the execution!")
            print(res)
            # raise "there was an error"
        return res

    @abstractclassmethod
    def exec(self, command: str) -> CommandResult:
        pass

class LocalExecContext(ExecContext):
    def exec(self, cmd: str) -> CommandResult:
        print("--executing: ", cmd)
        input("Press Enter to continue...")
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        data = p.communicate()

        res = {
            "stdout": data[0].decode(),
            "stderr": data[1].rstrip(b'\n').decode()
        }

        print(res)

        return res


class SSHExecContext(ExecContext):
    ssh_client: SSHClient
    hostname: str
    port: int
    username: str
    password: str

    def __init__(self, config: InstallConfig, hostname: str, port: int, username: str, password: str) -> None:
        super().__init__(config)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ssh_client = None

    def __enter__(self):
        if self.ssh_client:
            raise "Dont use this context twice, mate!"

        self.ssh_client = SSHClient()
        self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        self.ssh_client.connect(self.hostname, self.port, self.username, self.password)

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.ssh_client:
            self.ssh_client.close()

    def exec(self, cmd: str) -> CommandResult:
        if not self.ssh_client:
            raise "you need to use this with 'with'"

        # could use stdin, maybe, but pls dont
        _, stdout, stderr = self.ssh_client.exec_command(cmd)
        return {
            "stderr": stderr.read().decode("utf8"),
            "stdout": stdout.read().decode("utf8")
        }