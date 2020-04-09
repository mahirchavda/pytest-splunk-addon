# -*- coding: utf-8 -*-

from .data_model_handler import DataModelHandler
from .addon_parser import AddonParser

class CIMTestGenerator(object):
    """
    Generate the CIM based test cases. 
        1. Parse the data model JSON
        2. Parse the add-on 
        3. Check which data model is mapped for each tags stanza
        4. Generate test cases for each data model mapped
    """

    def __init__(
        self, addon_path, data_model_path="data_models", 
    ):

        self.data_model_handler = DataModelHandler(data_model_path)
        self.addon_parser = AddonParser(addon_path)

    def get_cim_models(self):
        yield from self.data_model_handler.get_mapped_data_models(self.addon_parser)

    def generate_cim_fields(self):
        for each_model in self.get_cim_models():
            # get each fields from the model 
            # Generate test case for each model 
            pass

    def generate_tests(self):

        pass
