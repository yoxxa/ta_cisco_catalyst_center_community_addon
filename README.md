# ta_cisco_catalyst_center_community_addon

### Summary

A community developed Splunk TA for gathering telemetry from Cisco Catalyst Center. 

This is the production release of two combined Proof-of-Concepts developed in private. The design choice was to make ingestion configuration as user friendly as possible.

The Catalyst Center Community Add-on allows a Splunk administrator to collect:
API (JSON):
- Network Health (RT, SW, AP, WLC)
- Device Health (Region/Site Level)
- Client Health (Wireless/Wired)
- Compliance (EoX, SWIM, Misconfiguration)
- Issues (P1, P2, P3)

Reports (CSV):
- Network Device Inventory 
- Security Advisories (Cisco PSIRTs)

### Details

##### Prerequisites

Please ensure the following:
- Known valid credentials, perhaps a RO service account.
- Daily Recurring Report (Security Advisories/Security Advisories Data - v1)
- Daily Recurring Report (Inventory/All Data Version 2.0 - v1)

Consider it is best practice to run the report(s) 10-15 minutes before creating the equivalent Splunk input to buffer for processing and generation.

##### Configure a Catalyst Center Account
1. Make your way to the `Configuration` upper tab and click the `Accounts` tab.
2. Navigate to the `Add` button on the middle right, below the `OpenAPI.json` button.
3. Fill out the form, including a name for this account, the username and password.

##### Configure a Catalyst Center
1. Navigate to the `Catalyst Center` tab on the `Configuration` upper tab.
2. Navigate to the `Add` button on the middle right, below the `OpenAPI.json` button.
3. Fill out the form, including a name for the Catalyst Center, the FQDN or IP address with a `https://` prefix. Choose the closest Catalyst Center version for your instance, and attach a certificate if necessary. Finally, select the previously created account from the `Account` tab.

##### Configure an API Input
1. Select which API input type you want to ingest.
2. Fill out the form with a unique name, the interval to collect, which index to store the data, and the Catalyst Center to gather data from.

##### Configure a Report Input
1. Select which Report input type you want to ingest.
2. Fill out the form with a unique name, the interval to collect should try to be timed to after a report has ran. Take note of the report name on your Catalyst Center instance, we need to use this to identify the report we gather. Once more, select the Catalyst Center to gather data from.

### Installation
Standard installation process, download via Splunkbase and install via Web UI.

### Troubleshooting
Troubleshooting is not built in, but possible. A global Logger instance per input is instantiated for all types, but alas, this will require for you to write your own `logger.info()` calls around the codebase via filesystem access to `$SPLUNK_HOME/etc/apps/ta_cisco_catalyst_center_community_addon/bin`.

All error messages will be caught by a try except block per Input. Check logs at `$SPLUNK_HOME/var/log/splunk/ta_cisco_catalyst_center_community_addon_{INPUT_NAME}` for your failing Input.