import utilities
from report import CatalystCenterReport

from dnacentersdk import DNACenterAPI
from os.path import expandvars
from pathlib import Path
import csv

import import_declare_test
from solnlib import log
from splunklib import modularinput as smi

KV_STORE_COLLECTION = "cc_config_archive"

def transform_for_kv_store(data: csv.DictReader) -> list[dict]:
    kv_data = list()
    for row in data:
        kv_data.append(
            {
                "sl_no": int(row["Sl.No"]),
                "device_name": row["Device Name"],
                "device_family": row["Device Family"],
                "device_type": row["Device Type"],
                "ip_address": row["IP Address"],
                "created_time": row["Created Time"], 
                "triggered_by": row["Triggered By"], 
                "category": row["Category"], 
                "device_user_name": row["Device User Name"], 
                "connection_mode": row["Connection Mode"], 
                "client_ip_address": row["Client IP Address"], 
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
