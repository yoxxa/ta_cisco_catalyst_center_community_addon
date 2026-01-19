import time
from logging import Logger
from dnacentersdk import DNACenterAPI, MalformedRequest, ApiError

class CatalystCenterReport:
    def __init__(
        self, 
        report_name: str,
        api: DNACenterAPI,
        logger: Logger 
    ) -> None:
        self.report_name: str = report_name
        self.api: DNACenterAPI = api
        self.logger: Logger = logger

        # Optionally override these
        # (e.g. a specific report requires more/less time to process)
        # TODO - figure out appropriate .sleep() timer
        self.sleep_timer: int = 10
        
        self._report = dict()
        self.execution_id = None
        self.data: bytes = None

    def gather_report(self, catalyst_center_conf_file: dict, input_item: dict) -> None:
        try:
            self.get_report()
            self.get_execution_detail()
            self.load_csv_report()
            return self.prepare_for_kv_store(
                catalyst_center_conf_file.get(input_item.get("catalyst_center")).get("catalyst_center_host")
            )
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

    def gather_report_rows(self, cisco_dnac_host: str) -> list[list[str]]:
        report_rows = [data.split(",") for data in self.data.decode("utf-8").splitlines()]
        self.tag_cisco_dnac_host(report_rows, cisco_dnac_host)
        return report_rows

    def tag_cisco_dnac_host(self, rows: list[list[str]], cisco_dnac_host: str) -> None:
        rows[0].append("cisco_dnac_host")
        for index in range(1, len(rows)):
            rows[index].append(cisco_dnac_host)

    def prepare_for_kv_store(self, cisco_dnac_host: str) -> list[dict]:
        report_rows = self.gather_report_rows(cisco_dnac_host)
        headers = report_rows[0]
        rows = report_rows[1:]
        return [dict(zip(headers, row)) for row in rows]