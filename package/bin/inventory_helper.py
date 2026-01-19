import utilities
from report import CatalystCenterReport

from dnacentersdk import DNACenterAPI
from os.path import expandvars
from pathlib import Path

import import_declare_test
from solnlib import log
from splunklib import modularinput as smi

KV_STORE_COLLECTION = "inventory"

def transform_for_kv_store(data: list[dict]) -> list[dict]:
    kv_data = list()
    for row in data:
        kv_data.append(
            {
                "sl_no": int(row["Sl.No"]),
                "device_family": row["Device Family"],
                "device_type": row["Device Type"],
                "device_name": row["Device Name"],
                "serial_no": row["Serial No."],
                "ip_address": row["IP Address"],
                "status": row["Status"],
                "software_version": row["Software Version"],
                "up_time": row["Up Time"],
                "part_no": row["Part No."],
                "location": row["Location"],
                "no_of_users": int(row["No. of Users"]),
                "no_of_ethernet_ports": int(row["No. of ethernet ports"]),
                "time_since_code_upgrade_via_catalyst_center_swim": row["Time Since Code Upgrade via Catalyst Center SWIM"],
                "dna_license": row["DNA License"],
                "device_license": row["Device License"],
                "cns_license": row["CNS License"],
                "fabric_roles": row["Fabric Roles"],
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
