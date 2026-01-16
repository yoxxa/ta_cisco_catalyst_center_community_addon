import utilities
from report import CatalystCenterReport

from dnacentersdk import DNACenterAPI
from os.path import expandvars
from pathlib import Path

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

LOOKUP_FILE_PATH = Path(expandvars("$SPLUNK_HOME/etc/apps/ta_cisco_catalyst_center_community_addon/lookups/inventory.csv"))

def validate_input(definition: smi.ValidationDefinition):
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = utilities.logger_for_input(normalized_input_name)
        log.modular_input_start(logger, normalized_input_name)
        try:
            account_conf_file = utilities.get_account_conf_file(inputs, logger)
            api = utilities.construct_dnacentersdk(account_conf_file, input_item)
            report = CatalystCenterReport(
                input_item["report_name"],
                LOOKUP_FILE_PATH,
                api,
                logger
            )
            report.report()
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")
