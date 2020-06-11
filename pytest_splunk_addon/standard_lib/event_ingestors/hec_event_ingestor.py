"""
HEC Event Ingestor class
"""
from base_event_ingestor import EventIngestor
import requests

requests.urllib3.disable_warnings()


class HECEventIngestor(EventIngestor):
    """
    Class to ingest event via HEC
    """

    def __init__(self, hec_uri, session_headers):
        """
        init method for the class
        Args:
            hec_uri(str): {splunk_hec_scheme}://{splunk_host}:{hec_port}/services/collector/{port_type}
                port_type can be "raw" or "event"
            session_headers(dict): requesr header info.
            header_format::
                    {
                        "Authorization": f"Splunk <hec-token>",
                    }
        """
        self.hec_uri = hec_uri
        self.session_headers = session_headers

    def ingest(self, data):
        """
        Ingests data into splunk using HEC token.
        Args:
            data(dict): data dict with the info of the data to be ingested.

        For ingesting data at raw or event endpoint using HEC:
            This format must be followed for ingestion at /services/collector/event endpoint.
        data_format::
                {
                    "sourcetype": "sample_HEC",
                    "source": "sample_source",
                    "host": "sample_host",
                    "event": "data to be ingested, can be raw or json"
                }
        
        For ingestion of metrics data using HEC:
            Use the /services/collector REST API endpoint to send data to the metrics index.
            You have to set your metric_name and _value for that measurement in the fields along dict with other dimentions.
            Do NOT make more than 99,999 events in same timestamp.
            It will cause Splunk to error on any searches due to more 100K or more events in the index for the same timestamp.
        data_format::
                {
                    "time": 1505501123.000,
                    "index": "em_metrics",
                    "event": "metric",
                    "fields": {
                        "region": "us-west-1",
                        "datacenter": "us-west-1a",
                        "os": "Ubuntu16.10",
                        "_value":1099511627776,
                        "metric_name":"total"
                    }
                }

        For batch ingestion of events via HEC provide a list of events to be ingested with other required info.
        data_format::
                {
                    "sourcetype": "sample_HEC",
                    "source": "sample_source",
                    "host": "sample_host",
                    "index": "metrics_index"
                    "event": ["event1", "event2", "event3"]
                }
        """
        try:
            response = requests.post(
                self.hec_uri,
                auth=None,
                json=data,
                headers=self.session_headers,
                verify=False,
            )
            if response.status_code not in (200, 201):
                raise Exception

        except Exception:
            print(
                "Status code: {} Reason: {} ".format(
                    response.status_code, response.reason
                )
            )
            print(response.text)
