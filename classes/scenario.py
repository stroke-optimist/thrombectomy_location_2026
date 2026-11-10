"""
Scenario class with global parameters for the pathway model.
"""


class Scenario(object):

    """
    Global variables for model.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor class for Scenario.
        """

        # General
        self.name = 'No_name'

        # Geography
        self.limit_to_england = True

        # Process times
        self.process_time_call_ambulance = 30
        self.process_time_ambulance_response = 20
        self.process_ambulance_on_scene_duration = 30
        self.process_time_arrival_to_needle = 30
        self.process_time_arrival_to_puncture = 90
        self.process_MT_net_delay = 60

        # Save options
        self.save_lsoa_results = False

        # Overwrite default values (can take named arguments or a dictionary)
        for dictionary in args:
            for key in dictionary:
                setattr(self, key, dictionary[key])

        for key in kwargs:
            setattr(self, key, kwargs[key])
