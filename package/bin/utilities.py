import logging
from dnacentersdk import DNACenterAPI

from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "ta_cisco_catalyst_center_community_addon"

def logger_for_input(input_name: str) -> logging.Logger:
    """Get the Logger instance for the input with name `input_name`"""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

# TODO - revise if return type of `dict` is accurate: account_conf_file seems to be a dict-like object
def get_account_conf_file(inputs: dict, logger: logging.Logger) -> dict:
    session_key = inputs.metadata["session_key"]
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME}_account",
    )
    account_conf_file = cfm.get_conf(f"{ADDON_NAME}_account")
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=ADDON_NAME,
        conf_name=f"{ADDON_NAME}_settings",
    )
    logger.setLevel(log_level)
    return account_conf_file

# TODO - add certificate handling
def construct_dnacentersdk(account_conf_file: dict, input_item: dict) -> DNACenterAPI:
    """Creates a new `DNACenterAPI` object"""
    return DNACenterAPI(
        username = account_conf_file.get(input_item.get("account")).get("username"),
        password = account_conf_file.get(input_item.get("account")).get("password"),
        base_url = input_item["catalyst_center_host"],
        version = input_item["catalyst_center_version"],
        # see TODO
        verify = False
    )