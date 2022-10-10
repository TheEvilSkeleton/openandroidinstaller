"""Class to load config files for the install procedure."""

# This file is part of OpenAndroidInstaller.
# OpenAndroidInstaller is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.

# OpenAndroidInstaller is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with OpenAndroidInstaller.
# If not, see <https://www.gnu.org/licenses/>."""
# Author: Tobias Sterbak

from pathlib import Path
from typing import List, Optional
import schema
from schema import Regex, Schema, SchemaError

import yaml
from loguru import logger


class Step:
    def __init__(
        self,
        title: str,
        type: str,
        content: str,
        command: str = None,
        img: str = "placeholder.png",
        allow_skip: bool = False,
    ):
        self.title = title
        self.type = type
        self.content = content
        self.command = command
        self.img = img
        self.allow_skip = allow_skip


class InstallerConfig:
    def __init__(
        self,
        unlock_bootloader: List[Step],
        flash_recovery: List[Step],
        install_os: List[Step],
        metadata: dict,
    ):
        self.unlock_bootloader = unlock_bootloader
        self.flash_recovery = flash_recovery
        self.install_os = install_os
        self.metadata = metadata

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as stream:
            try:
                raw_config = yaml.safe_load(stream)
                if validate_config(raw_config):
                    config = dict(raw_config)
                    raw_steps = config["steps"]
                    metadata = config["metadata"]
                else:
                    logger.info("Validation of config failed.")
                    return None
            except yaml.YAMLError as exc:
                logger.info(exc)
                return None

        if raw_steps.get("unlock_bootloader") is not None:
            unlock_bootloader = [
                Step(**raw_step) for raw_step in raw_steps.get("unlock_bootloader")
            ]
        else:
            unlock_bootloader = []
        flash_recovery = [Step(**raw_step) for raw_step in raw_steps.get("flash_recovery", [])]
        install_os = [Step(**raw_step) for raw_step in raw_steps.get("install_os", [])]
        return cls(unlock_bootloader, flash_recovery, install_os, metadata)


def _load_config(device_code: str, config_path: Path) -> Optional[InstallerConfig]:
    """
    Function to load a function from given path and directory path.

    Try to load local file in the same directory as the executable first, then load from assets.
    """
    # try loading a custom local file first
    custom_path = Path.cwd().joinpath(Path(f"{device_code}.yaml"))
    try:
        config = InstallerConfig.from_file(custom_path)
        logger.info(f"Loaded custom device config from {custom_path}.")
        logger.info(f"Config metadata: {config.metadata}.")
        return config
    except FileNotFoundError:
        # if no localfile, then try to load a config file from assets
        path = config_path.joinpath(Path(f"{device_code}.yaml"))
        try:
            config = InstallerConfig.from_file(path)
            logger.info(f"Loaded device config from {path}.")
            if config:
                logger.info(f"Config metadata: {config.metadata}.")
            return config
        except FileNotFoundError:
            logger.info(f"No device config found for {path}.")
            return None


def validate_config(config: str) -> bool:
    """Validate the schema of the config.""" 

    step_schema = {
        "title": str,
        "type": Regex(r"text|confirm_button|call_button|call_button_with_input"),
        "content": str,
        schema.Optional("command"): Regex(r"^adb\s|^fastboot\s|^heimdall\s"), 
        schema.Optional("allow_skip"): bool,
        schema.Optional("img"): str,
    }

    config_schema = Schema({
        "metadata": {
            "maintainer": str,
            "devicename": str,
            "devicecode": str,
        },
        "steps": {
            "unlock_bootloader": schema.Or(None, [step_schema]),
            "flash_recovery": [step_schema],
            "install_os": [step_schema],
        }
    })
    try:
        config_schema.validate(config)
        logger.info("Config is valid.")
        return True
    except SchemaError as se:
        logger.info(f"Config is invalid. Error {se}")
        return False