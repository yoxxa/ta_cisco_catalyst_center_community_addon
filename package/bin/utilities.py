import logging

from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "ta_cisco_catalyst_center_community_addon"
# TODO - change this to be dynamic with user input
DNAC_VERSION = "2.3.7.9"

def logger_for_input(input_name: str) -> logging.Logger:
    """Get the Logger instance for the input with name `input_name`"""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")