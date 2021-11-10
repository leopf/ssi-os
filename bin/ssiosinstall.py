import argparse
import pathlib
import json

from ssiosinstaller.context import InstallConfig, LocalExecContext, SSHExecContext
from ssiosinstaller.installer import install
import inquirer

parser = argparse.ArgumentParser(description='ssiOS -')
parser.add_argument('--ssh', action=argparse.BooleanOptionalAction)
parser.add_argument('--config', type=pathlib.Path, default="config.json")

args = parser.parse_args()

config_dict: InstallConfig = None
with open(args.config, mode="r") as config_file:
    config_dict = json.load(config_file)

if args.ssh:
    questions = [
        inquirer.Text('hostname', message="hostname"),
        inquirer.Text('port', message="port"),
        inquirer.Text('username', message="username"),
        inquirer.Text('password', message="password"),
    ]
    answers = inquirer.prompt(questions)
    with SSHExecContext(config_dict, answers["hostname"], int(answers["port"]), answers["username"], answers["password"]) as context:
        install(context)
else:
    with LocalExecContext(config_dict) as context:
        install(context)
