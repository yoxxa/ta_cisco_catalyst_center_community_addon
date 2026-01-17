import json
import logging
from dnacentersdk import DNACenterAPI

from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "ta_cisco_catalyst_center_community_addon"

def logger_for_input(input_name: str) -> logging.Logger:
    """Get the Logger instance for the input with name `input_name`"""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def set_logger_level(inputs: dict, logger: logging.Logger) -> None:
    session_key = inputs.metadata["session_key"]
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=ADDON_NAME,
        conf_name=f"{ADDON_NAME}_settings",
    )
    logger.setLevel(log_level)

def get_catalyst_center_conf_file(inputs: dict) -> dict:
    """
    example return dict:
    {"account": "admin", "catalyst_center_host": "https://1.1.1.1", "catalyst_center_version": "2.3.7.9", ...}
    """
    session_key = inputs.metadata["session_key"]
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME}_catalyst_center",
    )
    catalyst_center_conf_file = cfm.get_conf(f"{ADDON_NAME}_catalyst_center")
    return catalyst_center_conf_file

def get_account_conf_conf_file(inputs: dict) -> dict:
    session_key = inputs.metadata["session_key"]
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME}_account",
    )
    account_conf_file = cfm.get_conf(f"{ADDON_NAME}_account")
    return account_conf_file

# TODO - add certificate handling
def construct_dnacentersdk(
    catalyst_center_conf_file: dict, 
    account_conf_file: dict,
    input_item: dict
) -> DNACenterAPI:
    """Creates a new `DNACenterAPI` object"""
    return DNACenterAPI(
        username = account_conf_file.get(catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("account")).get("username"),
        password = account_conf_file.get(catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("account")).get("password"),
        base_url = catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_host"),
        version = catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_version"),
        # see TODO
        verify = False
    )

def send_data_to_splunk(
    event_writer: smi.EventWriter, 
    data: dict, 
    logger: logging.Logger,
    input_item: dict, 
    input_name: str
) -> None:
    for sourcetype in data:
        # single record i.e. dict
        if isinstance(data[sourcetype], dict):
            event_writer.write_event(
                smi.Event(
                    data = json.dumps(data[sourcetype], ensure_ascii=False, default=str),
                    index = input_item["index"],
                    sourcetype = sourcetype,
                )
            )
        # multiple records i.e. list
        if isinstance(data[sourcetype], list):
            for _data in data[sourcetype]:
                event_writer.write_event(
                    smi.Event(
                        data = json.dumps(_data, ensure_ascii=False, default=str),
                        index = input_item["index"],
                        sourcetype = sourcetype,
                    )
                )
        log.events_ingested(
            logger,
            input_name,
            sourcetype,
            len(data[sourcetype]),
            input_item["index"]
        )

def tag_cisco_dnac_host(data: dict, catalyst_center_conf_file: dict, input_item: dict) -> None:
    for sourcetype in data:
        # single record i.e. dict
        if isinstance(data[sourcetype], dict):
            data[sourcetype].update({"cisco_dnac_host": catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_host")})
        # multiple records i.e. list
        if isinstance(data[sourcetype], list):
            for _data in data[sourcetype]:
                _data.update({"cisco_dnac_host": catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_host")})