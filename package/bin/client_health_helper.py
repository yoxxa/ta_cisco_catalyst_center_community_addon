import utilities

from dnacentersdk import DNACenterAPI
import logging

import import_declare_test
from solnlib import log
from splunklib import modularinput as smi

DATA = dict({
    "cisco:catc:client_health": list()
})

ATTRIBUTES = list([
    "siteHierarchy",
    "snr",
    "rssi",
    "connectedNetworkDeviceMac",
    "connectedNetworkDeviceId",
    "rxRetries",
    "rxLinkErrorPercentage",
    "txLinkErrorPercentage",
    "rxRetryPercentage"
])

def retrieves_the_list_of_clients_by_applying_complex_filters_while_also_supporting_aggregate_attributes(api: DNACenterAPI, logger: logging.Logger) -> None:
    response = api.clients.retrieves_the_list_of_clients_by_applying_complex_filters_while_also_supporting_aggregate_attributes(
        views = ["WirelessHealth", "WiredHealth"],
        attributes = ATTRIBUTES
    ).response
    for device in response:
        utilities.format_mac_address(device)
    DATA["cisco:catc:client_health"] = response

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
            cert = utilities.construct_certificate(
                catalyst_center_conf_file,
                input_item
            )
            api = utilities.construct_dnacentersdk(
                catalyst_center_conf_file, 
                account_conf_file, 
                input_item,
                cert
            )
            retrieves_the_list_of_clients_by_applying_complex_filters_while_also_supporting_aggregate_attributes(api, logger)
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
            utilities.cleanup_cert(cert)
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")
