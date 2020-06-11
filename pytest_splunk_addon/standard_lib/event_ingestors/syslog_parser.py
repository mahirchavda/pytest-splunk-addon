"""
syslog parser class
"""
import re
import logging

LOGGER = logging.getLogger("pytest-splunk-addon")

class SysLogParser(object):
    """
    Class to parse the headers of syslog format data
    """

    def __init__(self, data, params):
        """
        init method for class
        Args:
            data: raw syslog data
            data_format::
                ***SPLUNK*** source=<source> sourcetype=<sourcetype>

                fiels_1   field2   field3
                value1    value2   value3
            params: params used while ingesting the data
            params_format::
                {
                    "host": "host"
                }
        """
        self.data = data
        self.params = params

    def sys_log_header_data_parser(self):
        """
        This method is to process the syslog formated samples data
        Returns:
            syslog data and params that contains syslog_headers
        """
        try:
            header = self.data.split("\n", 1)[0] 
            data = self.data.split("\n", 1)[1]

            header_props = ["source", "sourcetype", "host", "index"]

            for header_prop in header_props:
                header_property = re.search(f"{header_prop}=[^\s]+", header)
                property_value = self.get_props_value(header_property)
                if property_value is not None:
                    self.params[header_prop] = property_value

            return data, self.params
        except IndexError as error:
            LOGGER.error(f"Unexpected data found. Error: {error}")
            raise Exception(error)

    def get_props_value(self, property):
        """
        This method is to get the header_property value
        Args:
            property: syslog header property
            property_format::
                ['sourcetype=<sourcetype>']
        Returns:
            value of the header property
        """
        if property:
            property_value = property[0].split("=")[1]
            return property_value




#TO INTEGRATE THIS PARSER WITH HEC AND SC4S INGESTIONS
# Add following condition into code
'''
if isinstance(data, str) and data.startswith("***SPLUNK***"):
    sys_log_parser = SysLogParser(data, params)
    data, params =  sys_log_parser.sys_log_header_data_parser()
'''
