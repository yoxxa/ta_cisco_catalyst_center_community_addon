import utilities
from report import CatalystCenterReport

from dnacentersdk import DNACenterAPI
from os.path import expandvars
from pathlib import Path
import csv

import import_declare_test
from solnlib import log
from splunklib import modularinput as smi

KV_STORE_COLLECTION = "cc_eox"

def transform_for_kv_store(data: csv.DictReader) -> list[dict]:
    kv_data = list()
    for row in data:
        kv_data.append(
            {
                "device_name": row["Device Name"],
                "ip_address": row["IP Address"],
                "device_type": row["Device Type"],
                "serial_number": row["Serial Number"],
                "image_version": row["Image Version"],
                "site": row["Site"],
                "device_model_name": row["Device Model Name"],
                "device_image_type": row["Device Image Type"],
                "eox_scan_status": row["EOX Scan Status"],
                "eox_type": row["EOX Type"],
                "end_of_life_external_announcement_date": row["End Of Life External Announcement Date"],
                "end_of_sale_date": row["End Of Sale Date"],
                "end_of_last_hardware_shipdate": row["End Of Last Hardware ShipDate"],
                "end_of_software_maintenance_releases_date": row["End Of Software Maintenance Releases Date"],
                "end_of_hardware_new_service_attachment_date": row["End Of Hardware New Service Attachment Date"],
                "end_of_software_vulnerability_or_security_support_date": row["End Of Software Vulnerability Or Security Support Date"],
                "end_of_hardware_service_contract_renewal_date": row["End Of Hardware Service Contract Renewal Date"],
                "last_date_of_support": row["Last Date Of Support"],
                "eox_last_scan_time": row["EOX Last Scan Time"],
                "cisco_dnac_host": row["cisco_dnac_host"]
            }
        )
    return kv_data

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
            report = CatalystCenterReport(
                input_item["report_name"],
                api,
                logger
            )
            kv_data = report.gather_report(catalyst_center_conf_file, input_item)
            kv_data = transform_for_kv_store(kv_data)
            utilities.save_to_kv_store(
                kv_data, 
                inputs, 
                KV_STORE_COLLECTION, 
                catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_host")
            )
            utilities.cleanup_cert(cert)
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")
