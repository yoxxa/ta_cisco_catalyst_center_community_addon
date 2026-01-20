from certificate import Certificate

import json
import logging
from dnacentersdk import DNACenterAPI

from solnlib import conf_manager, log
from splunklib import modularinput as smi
import splunklib.client as client

ADDON_NAME = "ta_cisco_catalyst_center_community_addon"

# used for tagging Compliance input with Cat-C site hierarchy
DEVICE_ID_FIELDS = ["uuid", "deviceUuid", "deviceId"]
EXCLUDED_SOURCETYPES = [
    "cisco:catc:eox_summary",
    "cisco:catc:network_settings",
    "cisco:catc:swim_summary"
]

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

def construct_dnacentersdk(
    catalyst_center_conf_file: dict, 
    account_conf_file: dict,
    input_item: dict,
    cert: Certificate
) -> DNACenterAPI:
    """Creates a new `DNACenterAPI` object"""
    return DNACenterAPI(
        username = account_conf_file.get(catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("account")).get("username"),
        password = account_conf_file.get(catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("account")).get("password"),
        base_url = catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_host"),
        version = catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_version"),
        verify = cert.certificate(catalyst_center_conf_file, input_item)
    )

def construct_certificate(catalyst_center_conf_file: dict, input_item: dict) -> Certificate:
    return Certificate(
        catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("dnac_certificate")
    )

# defining cert typehint as `Certificate | None` causes not found error - what the...
def cleanup_cert(cert: Certificate) -> None:
    if cert is not None:
        cert.cleanup()

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

def tag_site_hierarchy(api: DNACenterAPI, data: dict) -> None:
    cache = dict()
    for sourcetype in data:
        if sourcetype in EXCLUDED_SOURCETYPES:
            pass
        if isinstance(data[sourcetype], dict):
            update_with_site_hierarchy(api, data[sourcetype], cache)
        if isinstance(data[sourcetype], list):
            for _data in data[sourcetype]:
                update_with_site_hierarchy(api, _data, cache)

def update_with_site_hierarchy(api: DNACenterAPI, data: dict, cache: dict) -> None:
    index: int = None
    for field in data.keys():
        try:
            index = DEVICE_ID_FIELDS.index(field)
        except ValueError: 
            continue
    if index is not None:
        # get the correct field name from DEVICE_ID_FIELDS (i.e. deviceUuid vs deviceId)
        uuid = data[DEVICE_ID_FIELDS[index]]
        if uuid not in cache:
            # else find the ID (device not seen before)
            response = api.devices.get_the_device_data_for_the_given_device_id_uuid(uuid).response
            cache[uuid] = response.siteHierarchy
        data.update({"siteHierarchy": cache[uuid]})

def save_to_kv_store(
    kv_data: list[dict], 
    inputs: dict, 
    kv_collection: str, 
    cisco_dnac_host: str
) -> None:
    service = client.connect(
        token = inputs.metadata["session_key"],
        owner = "nobody",
        app = ADDON_NAME
    )
    collection = service.kvstore[kv_collection]
    # flush out old rows
    collection.data.delete(query = json.dumps({"cisco_dnac_host": cisco_dnac_host}))
    if kv_data:
        batch_size = 500 
        for i in range(0, len(kv_data), batch_size):
            # slice the list to get the dicts
            chunk = kv_data[i : i + batch_size]
            # no idea why we need to deref
            collection.data.batch_save(*chunk)

def format_mac_address(device: dict) -> None:
    try:
        # format macAddress to `-` to avoid Splunk misread of `:` as new field
        device["macAddress"] = device["macAddress"].replace(":", "-")
    except AttributeError:
        pass