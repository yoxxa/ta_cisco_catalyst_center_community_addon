from io import TextIOWrapper
import time
from pathlib import Path
import csv
from logging import Logger
from dnacentersdk import DNACenterAPI, MalformedRequest, ApiError
import fcntl

# TODO - add MalformedRequest and ApiError try except blocks
class CatalystCenterReport:
    def __init__(
        self, 
        report_name: str,
        lookup_file_path: Path,
        api: DNACenterAPI,
        logger: Logger 
    ) -> None:
        self.report_name: str = report_name
        self.lookup_table_path: Path = lookup_file_path
        self.api: DNACenterAPI = api
        self.logger: Logger = logger

        # Optionally override these
        # (e.g. a specific report requires more/less time to process)
        # TODO - figure out appropriate .sleep() timer
        self.sleep_timer: int = 10
        
        self._report = dict()
        self.execution_id = None
        self.data: bytes = None

    def report(self, cisco_dnac_host: str) -> None:
        try:
            self.get_report()
            self.get_execution_detail()
            self.load_csv_report()
            self.update_lookup_table(cisco_dnac_host)
        except (MalformedRequest, ApiError) as error:
            raise error

    def get_report(self) -> None:
        """Retrives Catalyst Center report details for a given report name into memory"""
        for scheduled_report in self.api.reports.get_list_of_scheduled_reports():
            if scheduled_report["name"] == self.report_name:
                self._report = scheduled_report
                # report already found, no need to iterate further
                break 
        if not self._report:
            raise ValueError(f"Could not find report with name {self.report_name}!")

    def get_execution_detail(self) -> None:
        """Retrieves execution ID from a given Catalyst Center report ID where possible"""
        while True:
            execution = self.api.reports.get_all_execution_details_for_a_given_report(self._report["reportId"])
            if execution["executions"][0]["processStatus"] == "SUCCESS":
                self.execution_id = execution["executions"][0]["executionId"]
                break
            if execution["executions"][0]["processStatus"] == "IN_PROGRESS":
                time.sleep(self.sleep_timer)
                pass
            # TODO - Figure out why it might error and handle failure case
            if execution["executions"][0]["processStatus"] == "FAIL":
                self.logger.error(f"{self.report_name} is having status FAIL")
                raise ValueError("Report execution ID == FAIL")

    def get_report_contents(self) -> bytes:
        """Loads into memory a report from Catalyst Center as bytes"""
        resource_path = f"/dna/intent/api/v1/data/reports/{self._report['reportId']}/executions/{self.execution_id}"
        report_contents = self.api.custom_caller.call_api(
                method = "GET",
                resource_path = resource_path,
                original_response = True
            ).content
        return report_contents
    
    def load_csv_report(self) -> None:
        """Loads into a Polars dataframe a .csv report"""
        report_bytes = self.get_report_contents()
        self.data = report_bytes.split(b"\n\n")[-1]

    def update_lookup_table(self, cisco_dnac_host: str) -> None:
        """Updates the lookup table on disk"""
        with open(self.lookup_table_path, "r+") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            report_rows = self.gather_report_rows(cisco_dnac_host)
            report_rows.extend(self.get_valid_rows_from_lookup(file, cisco_dnac_host))
            self.write_to_lookup(file, report_rows)
            fcntl.flock(file, fcntl.LOCK_UN)

    def gather_report_rows(self, cisco_dnac_host: str) -> list[list[str]]:
        report_rows = [data.split(",") for data in self.data.decode("utf-8").splitlines()]
        self.tag_cisco_dnac_host(report_rows, cisco_dnac_host)
        return report_rows

    def tag_cisco_dnac_host(self, rows: list[list[str]], cisco_dnac_host: str) -> None:
        rows[0].append("cisco_dnac_host")
        for index in range(1, len(rows)):
            rows[index].append(cisco_dnac_host)

    def get_valid_rows_from_lookup(self, file: TextIOWrapper, cisco_dnac_host: str) -> list[list[str]]:
        file.seek(0)
        reader = csv.reader(file, lineterminator="\n")
        preserved_rows = list()
        old_rows = list(reader)
        if old_rows:
            headers = old_rows[0]
            try:
                host_idx = headers.index("cisco_dnac_host")
                # Keep rows not matching cisco_dnac_host
                for row in old_rows[1:]:
                    if len(row) > host_idx and row[host_idx] != cisco_dnac_host:
                        preserved_rows.append(row)
            except ValueError:
                raise
        return preserved_rows

    def write_to_lookup(self, file: TextIOWrapper, rows: list[list[str]]) -> None:
        file.seek(0)
        writer = csv.writer(file, lineterminator="\n")
        writer.writerows(rows)