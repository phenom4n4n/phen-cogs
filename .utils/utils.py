# taken from https://github.com/TrustyJAID/Trusty-cogs/blob/master/.utils/utils.py
import glob
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Mapping, Optional

import click
import tabulate
from babel.lists import format_list as babel_list

DEFAULT_INFO = {
    "author": [],
    "install_msg": "",
    "name": "",
    "disabled": False,
    "short": "",
    "description": "",
    "tags": [],
    "requirements": [],
    "hidden": False,
}

logging.basicConfig(filename="scripts.log", level=logging.INFO)
log = logging.getLogger(__file__)

path = Path(__file__).resolve()
ROOT = path.parents[1]

VER_REG = re.compile(r"\_\_version\_\_ = \"(\d+\.\d+\.\d+)", flags=re.I)

DEFAULT_AUTHOR = ["PhenoM4n4n"]


HEADER = """<h1 align="center">
  <a href="https://github.com/phenom4n4n/phen-cogs"><img src="https://i.imgur.com/dIOX12K.png" alt="Phen-Cogs"></a>
</h1>

<p align="center">
  <a href="https://discord.gg/cGJ8JmX">
    <img src="https://discordapp.com/api/guilds/631306089366945821/widget.png?style=shield" alt="Discord Server">
  </a>
  <a href="https://www.python.org/downloads/">
    <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/Red-Discordbot">
  </a>
  <a href="https://github.com/Rapptz/discord.py/">
     <img src="https://img.shields.io/badge/discord-py-blue.svg" alt="discord.py">
  </a>
  <a href="https://github.com/ambv/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black">
  </a>
  <a href='https://phen-cogs.readthedocs.io/en/latest/?badge=latest'>
      <img src='https://readthedocs.org/projects/phen-cogs/badge/?version=latest' alt='Documentation Status' />
  </a>
</p>
<h4 align="center">Various phun and utility cogs for Red-DiscordBot.</h4>

# Installation
`[p]repo add Phen-Cogs https://github.com/phenom4n4n/phen-cogs`

# Cogs
{body}

# Contact
If you encounter bugs or require support, go to *#support_phen-cogs* on the [cog support server](https://discord.gg/GET4DVk).
For feature requests, open a PR/issue on this repo.

# Credits
[Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot)

All Cog Creators
"""


@dataclass
class InfoJson:
    author: List[str]
    description: Optional[str] = ""
    install_msg: Optional[str] = "Thanks for installing"
    short: Optional[str] = ""
    name: Optional[str] = ""
    min_bot_version: Optional[str] = "3.3.0"
    max_bot_version: Optional[str] = "0.0.0"
    hidden: Optional[bool] = False
    disabled: Optional[bool] = False
    required_cogs: Mapping = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    type: Optional[str] = "COG"
    permissions: List[str] = field(default_factory=list)
    min_python_version: Optional[List[int]] = field(default_factory=lambda: [3, 8, 0])
    end_user_data_statement: str = (
        "This cog does not persistently store data or metadata about users."
    )

    @classmethod
    def from_json(cls, data: dict):
        required_cogs: Mapping = {}
        author = data.get("author", [])
        description = data.get("description", "")
        install_msg = data.get("install_msg", "Thanks for installing")
        short = data.get("short", "Thanks for installing")
        min_bot_version = "3.1.8"
        if "bot_version" in data:
            min_bot_version = data["bot_version"]
            if isinstance(min_bot_version, list):
                min_bot_version = ".".join(str(i) for i in data["bot_version"])
        if "min_bot_version" in data:
            min_bot_version = data["min_bot_version"]
            # min_bot_version = "3.3.0"
        max_bot_version = data.get("max_bot_version", "0.0.0")
        name = data.get("name", "")
        if "required_cogs" in data:
            if isinstance(data["required_cogs"], list):
                required_cogs = {}
            else:
                required_cogs = data["required_cogs"]
        requirements = data.get("requirements", [])
        tags = data.get("tags", [])
        hidden = data.get("hidden", False)
        disabled = data.get("disabled", False)
        type = data.get("type", "COG")
        permissions = data.get("permissions", [])
        min_python_version = data.get("min_python_version", [])
        end_user_data_statement = data.get(
            "end_user_data_statement",
            "This cog does not persistently store data or metadata about users.",
        )

        return cls(
            author,
            description,
            install_msg,
            short,
            name,
            min_bot_version,
            max_bot_version,
            hidden,
            disabled,
            required_cogs,
            requirements,
            tags,
            type,
            permissions,
            min_python_version,
            end_user_data_statement,
        )


def save_json(folder, data):
    with open(folder, "w", encoding="utf-8") as newfile:
        json.dump(data, newfile, indent=4, sort_keys=True, separators=(",", " : "))


@click.group()
def cli():
    """Utilities for Cog creation!"""


@cli.command()
def mass_fix():
    """Ensure all info.json files are up-to-date with current standards"""
    for folder in os.listdir(f"{ROOT}/"):
        if folder.startswith("."):
            continue
        try:
            with open(f"{ROOT}/{folder}/info.json", "r", encoding="utf-8") as infile:
                info = InfoJson.from_json(json.load(infile))
            save_json(f"{ROOT}/{folder}/info.json", info.__dict__)
        except Exception:
            log.exception("Error reading info.json in %s", folder)
            continue


@cli.command()
@click.option("--author", default=DEFAULT_AUTHOR, help="Author of the cog", prompt=True)
@click.option("--name", prompt="Enter the name of the cog", help="Name of the cog being added")
@click.option(
    "--description",
    prompt="Enter a longer description for the cog.",
    help="Description about what the cog can do.",
)
@click.option(
    "--install-msg",
    prompt=True,
    default="Thanks for installing!",
    help="Enter the install message you would like. Default is `Thanks for installing!`",
)
@click.option(
    "--short",
    prompt="Enter a short description about the cog.",
    help="Enter a short description about the cog.",
)
@click.option(
    "--min-bot-version",
    default="3.3.0",
    help="This cogs minimum python version requirements.",
    prompt=True,
)
@click.option(
    "--max-bot-version",
    default="0.0.0",
    help="This cogs minimum python version requirements.",
    prompt=True,
)
@click.option(
    "--hidden",
    default=False,
    help="Whether or not the cog is hidden from downloader.",
    prompt=True,
    type=bool,
)
@click.option(
    "--disabled",
    default=False,
    help="Whether or not the cog is disabled in downloader.",
    prompt=True,
    type=bool,
)
@click.option("--required-cogs", default={}, help="Required cogs for this cog to function.")
@click.option("--requirements", prompt=True, default=[], help="Requirements for the cog.")
@click.option(
    "--tags", default=[], prompt=True, help="Any tags to help people find the cog better."
)
@click.option("--permissions", prompt=True, default=[], help="Any permissions the cog requires.")
@click.option(
    "--min-python-version",
    default=[3, 8, 0],
    help="This cogs minimum python version requirements.",
)
@click.option(
    "--end-user-data-statement",
    prompt=True,
    default="This cog does not persistently store data or metadata about users.",
    help="The end user data statement for this cog.",
)
def make(
    author: list,
    name: str,
    description: str = "",
    install_msg: str = "",
    short: str = "",
    min_bot_version: str = "3.3.0",
    max_bot_version: str = "0.0.0",
    hidden: bool = False,
    disabled: bool = False,
    required_cogs: Mapping[str, str] = {},
    requirements: List[str] = [],
    tags: list = [],
    permissions: list = [],
    min_python_version: list = [3, 8, 0],
    end_user_data_statement: str = "This cog does not persistently store data or metadata about users.",
):
    """Generate a new info.json file for your new cog!"""
    if isinstance(author, str):
        author = [author]
        if ", " in author:
            author = author.split(", ")
    if isinstance(requirements, str):
        requirements = requirements.split(" ")
    if isinstance(permissions, str):
        permissions = permissions.split(" ")
    if isinstance(tags, str):
        tags = tags.split(" ")
    if isinstance(min_python_version, str):
        min_python_version = [int(i) for i in min_python_version.split(".")]
    type = "COG"
    data_obj = InfoJson(
        author,
        description,
        install_msg,
        short,
        name,
        min_bot_version,
        max_bot_version,
        hidden,
        disabled,
        required_cogs,
        requirements,
        tags,
        type,
        permissions,
        min_python_version,
        end_user_data_statement,
    )
    print(data_obj)
    save_json(f"{ROOT}/{name}/info.json", data_obj.__dict__)


"""
author: List[str]
description: Optional[str] = ""
install_msg: Optional[str] = "Thanks for installing"
short: Optional[str] = ""
name: Optional[str] = ""
min_bot_version: Optional[str] = "3.3.0"
max_bot_version: Optional[str] = "0.0.0"
hidden: Optional[bool] = False
disabled: Optional[bool] = False
required_cogs: Mapping = field(default_factory=dict)
requirements: List[str] = field(default_factory=list)
tags: List[str] = field(default_factory=list)
type: Optional[str] = "COG"
permissions: List[str] = field(default_factory=list)
min_python_version: Optional[List[int]] = field(default_factory=lambda: [3, 8, 0])
end_user_data_statement: str = "This cog does not persistently store data or metadata about users."
"""


@cli.command()
@click.option("--include-hidden", default=False)
@click.option("--include-disabled", default=False)
def countlines(include_hidden: bool = False, include_disabled: bool = False):
    """Count the number of lines of .py files in all folders"""
    total = 0
    totals = []
    log.info(ROOT)
    for folder in os.listdir(f"{ROOT}/"):
        cog = 0
        if folder.startswith("."):
            continue
        try:
            with open(f"{ROOT}/{folder}/info.json", "r", encoding="utf-8") as infile:
                info = InfoJson.from_json(json.load(infile))
        except Exception:
            continue
        if info.hidden and not include_hidden:
            continue
        if info.disabled and not include_disabled:
            continue
        try:
            for file in glob.glob(f"{ROOT}/{folder}/*.py"):
                try:
                    with open(file, "r", encoding="utf-8") as infile:
                        lines = len(infile.readlines())
                    cog += lines
                    total += lines
                except Exception:
                    pass
            totals.append((folder, cog))
        except Exception:
            pass
    totals = sorted(totals, key=lambda x: x[1], reverse=True)
    totals.insert(0, ("Total", total))
    print(tabulate.tabulate(totals, headers=["Cog", "# ofLines"], tablefmt="pretty"))
    return totals


@cli.command()
@click.option("--include-hidden", default=False)
@click.option("--include-disabled", default=False)
def countchars(include_hidden: bool = False, include_disabled: bool = False):
    """Count the number of lines of .py files in all folders"""
    total = 0
    totals = []
    log.info(ROOT)
    for folder in os.listdir(f"{ROOT}/"):
        cog = 0
        if folder.startswith("."):
            continue
        try:
            with open(f"{ROOT}/{folder}/info.json", "r", encoding="utf-8") as infile:
                info = InfoJson.from_json(json.load(infile))
        except Exception:
            continue
        if info.hidden and not include_hidden:
            continue
        if info.disabled and not include_disabled:
            continue
        try:
            for file in glob.glob(f"{ROOT}/{folder}/*.py"):
                try:
                    with open(file, "r", encoding="utf-8") as infile:
                        lines = len(infile.read())
                    cog += lines
                    total += lines
                except Exception:
                    pass
            totals.append((folder, cog))
        except Exception:
            pass
    totals = sorted(totals, key=lambda x: x[1], reverse=True)
    totals.insert(0, ("Total", total))
    print(tabulate.tabulate(totals, headers=["Cog", "# ofchars"], tablefmt="pretty"))
    return totals


@cli.command()
def makereadme():
    """Generate README.md from info about all cogs"""
    table_data = []
    for folder in sorted(os.listdir(ROOT)):
        if folder.startswith(".") or folder.startswith("_"):
            continue
        _version = ""
        info = None
        for file in glob.glob(f"{ROOT}/{folder}/*"):
            if not file.endswith(".py") and not file.endswith("json"):
                continue
            if file.endswith("info.json"):
                try:
                    with open(file, encoding="utf-8") as infile:
                        data = json.loads(infile.read())
                    info = InfoJson.from_json(data)
                except Exception:
                    log.exception("Error reading info.json %s", file)
            if _version == "":
                with open(file, encoding="utf-8") as infile:
                    data = infile.read()
                    maybe_version = VER_REG.search(data)
                    if maybe_version:
                        _version = maybe_version.group(1)
        if info and not info.disabled and not info.hidden:
            to_append = [info.name, _version]
            description = f"<details><summary>{info.short}</summary>{info.description}</details>"
            to_append.append(description)
            to_append.append(babel_list(info.author, locale="en_US_POSIX"))
            table_data.append(to_append)

    body = tabulate.tabulate(
        table_data,
        headers=["Name", "Status/Version", "Description (Click to see full status)", "Authors"],
        tablefmt="github",
    )
    with open(f"{ROOT}/README.md", "w", encoding="utf-8") as outfile:
        outfile.write(HEADER.format(body=body))


@cli.command()
def makerequirements():
    """Generate a requirements.txt for all cogs.
    Useful when setting up the bot in a new venv and requirements are missing.
    """
    requirements = set()
    for folder in os.listdir(ROOT):
        if folder.startswith(".") or folder.startswith("_"):
            continue
        info = None
        for file in glob.glob(f"{ROOT}/{folder}/*"):
            if not file.endswith(".py") and not file.endswith("json"):
                continue
            if file.endswith("info.json"):
                try:
                    with open(file, encoding="utf-8") as infile:
                        data = json.loads(infile.read())
                    info = InfoJson.from_json(data)
                    if info.disabled:
                        continue
                    for req in info.requirements:
                        requirements.add(req)
                except Exception:
                    log.exception("Error reading info.json %s", file)
    with open(ROOT / "requirements.txt", "w", encoding="utf-8") as outfile:
        outfile.write("\n".join(requirements))


def run_cli():
    try:
        cli()
    except KeyboardInterrupt:
        print("Exiting.")
    else:
        print("Exiting.")


if __name__ == "__main__":
    run_cli()
