import utilities

from dnacentersdk import DNACenterAPI
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

DATA = dict({
    "cisco:catc:network_health": dict(),
    "cisco:catc:area_health": list(),
    "cisco:catc:building_health": list()
})

def get_overall_network_health(api: DNACenterAPI, logger: logging.Logger) -> None:
    # Only ever a single record in the list, hence [0]
    response = api.topology.get_overall_network_health().response[0]
    response.pop("time")
    DATA["cisco:catc:network_health"] = response

def get_area_health(api: DNACenterAPI, logger: logging.Logger) -> None:
    DATA["cisco:catc:area_health"] = api.sites.get_site_health(site_type = "AREA").response

def get_building_health(api: DNACenterAPI, logger: logging.Logger) -> None:
    DATA["cisco:catc:building_health"] = api.sites.get_site_health(site_type = "BUILDING").response

def validate_input(definition: smi.ValidationDefinition):
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = utilities.logger_for_input(normalized_input_name)
        utilities.set_logger_level(inputs, logger)
        log.modular_input_start(logger, normalized_input_name)
        try:
            catalyst_center_conf_file = utilities.get_catalyst_center_conf_file(inputs)
            account_conf_file = utilities.get_account_conf_conf_file(inputs)
            api = utilities.construct_dnacentersdk(
                catalyst_center_conf_file, 
                account_conf_file, 
                input_item
            )
            get_overall_network_health(api, logger)
            get_area_health(api, logger)
            get_building_health(api, logger)
            utilities.tag_cisco_dnac_host(
                DATA,
                catalyst_center_conf_file,
                input_item
            )
            utilities.send_data_to_splunk(
                event_writer,
                DATA,
                logger,
                input_item,
                input_name
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")
