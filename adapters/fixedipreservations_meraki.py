"""Provides loading/saving of fixed IP reservations. """
import logging
import re
from typing import List
import meraki
from deepdiff import DeepDiff
from netorg_core import devicetable
from netorg_core import networkspace
from netorg_core import ports

class FixedIpReservationsAdapter(ports.FixedIpReservationsPort):
    """Provides loading/saving of fixed IP reservations. """
    # pylint: disable=logging-fstring-interpolation
    # pylint: disable=line-too-long

    def __init__(self, config: dict) -> None:
        self.__logger = logging.getLogger("netorg")
        supress_logging = True
        if self.__logger.getEffectiveLevel() == logging.DEBUG:
            supress_logging = False
        self.dashboard = meraki.DashboardAPI(config['api_key'], suppress_logging=supress_logging)
        self.network_id = config['network_id']
        self.vlan_id = str(config['vlan_id'])
        self.vlan_subnet = config['vlan_subnet']

    # overriding abstract method
    def load(self) -> List[ports.FixedIpReservation]:
        list_of_fixed_ip_reservations: List[ports.FixedIpReservation] = []
        vlan = self.dashboard.appliance.getNetworkApplianceVlan(self.network_id, str(self.vlan_id))
        reservations = vlan['fixedIpAssignments']
        if reservations:
            for mac, reservation_details in reservations.items():
                fixed_ip_reservation = ports.FixedIpReservation(
                    mac=mac,
                    name=reservation_details['name'],
                    ip_address=reservation_details['ip']
                )
                list_of_fixed_ip_reservations.append(fixed_ip_reservation)
        self.__logger.debug(f"FixedIpReservationsMerakiAdapter.load() returned {len(list_of_fixed_ip_reservations)} fixed IP reservations")
        return list_of_fixed_ip_reservations

    # overriding abstract method
    def save(self,device_table: devicetable.DeviceTable) -> None:
        network_mapper = networkspace.NetworkMapper(self.vlan_subnet,device_table)
        network_mapper.map_to_network_space()
        self.__logger.info(f'Network space is {network_mapper.get_percent_used():.2f}% full')
        new_fixed_ip_reservations = FixedIpReservationsAdapter.__generate_fixed_ip_reservations(device_table)
        before_vlan = self.dashboard.appliance.getNetworkApplianceVlan(self.network_id, str(self.vlan_id))
        old_fixed_ip_reservations = before_vlan['fixedIpAssignments']
        FixedIpReservationsAdapter.__show_diffs(old_fixed_ip_reservations, new_fixed_ip_reservations)
        # pylint: disable=unused-variable
        response = self.dashboard.appliance.updateNetworkApplianceVlan(
            self.network_id, self.vlan_id,
            fixedIpAssignments=new_fixed_ip_reservations)
        self.__logger.debug(f"FixedIpReservationsAdapter.save() response from Meraki {response}")

    @staticmethod
    def __generate_fixed_ip_reservations(device_table: devicetable.DeviceTable) -> dict:
        """Generate fixed IP reservations."""
        # pylint: disable=invalid-name
        logger = logging.getLogger("netorg")
        ip_reservations_dict = {}
        df = device_table.get_df()
        skip_these_macs = df.query("not known and reserved and not active").mac.unique().tolist()
        macs = df.mac.unique().tolist()
        for mac in macs :
            if mac not in skip_these_macs:
                device_df = df.query('mac == @mac')
                if device_df.shape[0] == 1:
                    ip = device_df.iloc[0]['ip']
                    name = device_df.iloc[0]['name']
                    ip_reservations_dict[mac] = {
                        'ip': ip,
                        'name': name
                    }
            else:
                logger.debug(f'FixedIpReservationsAdapter: skipping {mac}')
        return ip_reservations_dict

    @staticmethod
    def __show_diffs(old_fixed_ip_reservations, new_fixed_ip_reservations):
        """Show the before and after differences to the fixed IP reservations."""
        logger = logging.getLogger("netorg")
        diff = DeepDiff(old_fixed_ip_reservations, new_fixed_ip_reservations)
        if diff:
            logger.info("Fixed IP reservation differences are as follows:")
            if 'dictionary_item_added' in diff:
                logger.info("  Adding reservations:")
                added_list = diff['dictionary_item_added']
                for added in added_list:
                    added = re.search("'.*'", added)
                    if added:
                        added = added.group()
                        added = added.strip("'")
                        # pylint: disable=line-too-long
                        logger.info(f'    {new_fixed_ip_reservations[added]["ip"]} for device {added} named {new_fixed_ip_reservations[added]["name"]}')
            else:
                logger.info("  There are no new fixed IP reservations")
            if 'dictionary_item_removed' in diff:
                logger.info("  Removing reservations:")
                removed_list = diff['dictionary_item_removed']
                for removed in removed_list:
                    removed = re.search("'.*'", removed)
                    if removed:
                        removed = removed.group()
                        removed = removed.strip("'")
                        # pylint: disable=line-too-long
                        logger.info(f'    {old_fixed_ip_reservations[removed]["ip"]} for device {removed} named {old_fixed_ip_reservations[removed]["name"]}')
        else:
            logger.info("There are no changes to fixed IP reservations")
