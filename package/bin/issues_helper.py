import utilities

from dnacentersdk import DNACenterAPI
import logging

import import_declare_test
from solnlib import log
from splunklib import modularinput as smi

DATA = dict({
    "cisco:catc:issue": list()
})

def get_devices(api: DNACenterAPI, logger: logging.Logger) -> None:
    response = api.issues.get_the_details_of_issues_for_given_set_of_filters(
        payload= {"attributes": ["additionalAttributes"]}
    ).response
    for issue in response:
        for additionalAttribute in issue.additionalAttributes:
            # do not flatten any private Cat-C attributes starting with "_"
            # str[0] == "_" is slightly faster than str.startswith("_")
            if additionalAttribute["key"] not in issue and not additionalAttribute["key"][0] == "_":
                issue.update({additionalAttribute["key"]: additionalAttribute["value"]})
    DATA["cisco:catc:issue"] = response

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
            get_devices(api, logger)
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
