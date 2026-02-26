import utilities

from dnacentersdk import DNACenterAPI
import logging

import import_declare_test
from solnlib import log
from splunklib import modularinput as smi

DATA = dict({
    "cisco:catc:eox": list(),
    "cisco:catc:eox_detail": list(),
    "cisco:catc:eox_summary": dict(),
    "cisco:catc:network_settings": list(),
    "cisco:catc:device_network_settings": list(),
    "cisco:catc:swim": list(),
    "cisco:catc:swim_detail": list(),
    "cisco:catc:swim_summary": list(),
})

def get_eox_status_for_all_devices(api: DNACenterAPI, logger: logging.Logger) -> None:
    response = api.eox.get_eox_status_for_all_devices().response
    response = [eox for eox in response if eox.alertCount is not 0]
    DATA["cisco:catc:eox"] = response

def get_eox_details_for_all_devices(api: DNACenterAPI, logger: logging.Logger) -> None:
    response = list()
    for eox in DATA["cisco:catc:eox"]:
        response.append(
            api.eox.get_eox_details_per_device(eox.deviceId).response
        )
    DATA["cisco:catc:eox_detail"] = response

def get_eox_summary(api: DNACenterAPI, logger: logging.Logger) -> None:
    DATA["cisco:catc:eox_summary"] = api.eox.get_eox_summary().response

def get_network_settings(api: DNACenterAPI, logger: logging.Logger) -> None:
    DATA["cisco:catc:network_settings"] = api.compliance.get_compliance_detail(
        compliance_status = "NON_COMPLIANT",
        compliance_type = "NETWORK_SETTINGS"
    ).response

def get_device_network_settings(api: DNACenterAPI, logger: logging.Logger) -> None:
    response = list()
    for device in DATA["cisco:catc:network_settings"]:
        response.append(
            api.compliance.compliance_details_of_device(
                device_uuid = device.deviceUuid,
                compliance_type = "NETWORK_SETTINGS"
            ).response[0]
        )
    DATA["cisco:catc:device_network_settings"] = response

def get_swim(api: DNACenterAPI, logger: logging.Logger) -> None:
    DATA["cisco:catc:swim"] = api.compliance.get_compliance_detail(
        compliance_status = "NON_COMPLIANT",
        compliance_type = "IMAGE"
    ).response

def get_swim_detail(api: DNACenterAPI, logger: logging.Logger) -> None:
    response = list()
    for device in DATA["cisco:catc:swim"]:
        response.append(
            api.compliance.compliance_details_of_device(
                device_uuid = device.deviceUuid,
                compliance_type = "IMAGE"
            ).response[0]
        )
    add_software_versions(api, response)
    DATA["cisco:catc:swim_detail"] = response

def add_software_versions(api: DNACenterAPI, data: list[dict]) -> None:
    for device in data:
        response = api.devices.get_device_by_id(device.deviceUuid).response
        device.update({"softwareVersion": response.softwareVersion})

def returns_the_image_summary_for_the_given_site(api: DNACenterAPI, logger: logging.Logger) -> None:
    DATA["cisco:catc:swim_summary"] = api.software_image_management_swim.returns_the_image_summary_for_the_given_site().response

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
            get_eox_status_for_all_devices(api, logger)
            get_eox_details_for_all_devices(api, logger)
            get_eox_summary(api, logger)
            get_network_settings(api, logger)
            get_device_network_settings(api, logger)
            get_swim(api, logger)
            get_swim_detail(api, logger)
            returns_the_image_summary_for_the_given_site(api, logger)
            utilities.tag_cisco_dnac_host(
                DATA,
                catalyst_center_conf_file,
                input_item,
            )
            utilities.tag_site_hierarchy(
                api,
                DATA
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
