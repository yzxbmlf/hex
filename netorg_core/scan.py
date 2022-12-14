"""This is the main module for Netorg scanning."""
import logging
from netorg_core import format_utils

# pylint: disable=line-too-long
# pylint: disable=logging-fstring-interpolation


class NetorgScanner:
    """All things associated with Netorg scanning"""

    def __init__(self, device_table):
        # pylint: disable=line-too-long
        self.__logger = logging.getLogger("netorg")
        self.device_table = device_table
        self.analysis = {
            'not_known_not_reserved_ACTIVE': {
                'query': 'not known and not reserved and active',
                'device_names': [],
                'action': 'New device(s)? These will be known as un-classified during the next organize'
            },
            'not_known_RESERVED_not_active': {
                'query': 'not known and reserved and not active',
                'device_names': [],
                'action': 'Retired device(s)? The reserved IP will be removed during the next organize'
            },
            'not_known_RESERVED_ACTIVE': {
                'query': 'not known and reserved and active',
                'device_names': [],
                'action': 'These will be known as un-classified during the next organize'
            },
            'KNOWN_not_reserved_not_active': {
                'query': 'known and not reserved and not active',
                'device_names': [],
                'action': 'A reserved IP will be created during the next organize'
            },
            'KNOWN_not_reserved_ACTIVE': {
                'query': 'known and not reserved and active',
                'device_names': [],
                'action': 'The current IP will be converted to a static IP during the next organize'
            },
            'KNOWN_RESERVED_not_active': {
                'query': 'known and reserved and not active',
                'device_names': [],
                'action': 'These devices are currently inactive - no action will be taken during the next organize'
            },
            'KNOWN_RESERVED_ACTIVE': {
                'query': 'known and reserved and active',
                'device_names': [],
                'action': 'Normal state - no action will be taken during the next organize'
            },
            'ACTIVE_UNCLASSIFIED': {
                'query': "active and group == 'unclassified'",
                'device_names': [],
                'action': 'You should consider classifying them before the next organize'
            }
        }

    def run(self):
        """Run the analysis updating the analysis dictionary with the findings."""
        # pylint: disable=invalid-name
        # pylint: disable=unused-variable
        df = self.device_table.get_df()
        for k, v in self.analysis.items():
            query_result_df = df.query(v['query'])
            v['device_names'] = query_result_df['name'].values.tolist()

    def report(self):
        """Report on the findings discovered by run()."""
        # pylint: disable=invalid-name
        # pylint: disable=unused-variable
        for k, v in self.analysis.items():
            if len(v["device_names"]) == 0:
                self.__logger.info(
                    f'Did not find any devices that are: {v["query"]}')
            else:
                self.__logger.info(
                    f'Found {len(v["device_names"])} device(s) that are: {v["query"]}')
                self.__logger.info(f'{v["action"]}')
                for row in format_utils.adaptive_columnize(v['device_names'], left_margin_width=3):
                    self.__logger.info(f"{' '.join(row)}")
