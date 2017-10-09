"""
Defines the BridgeDevice class.

Copyright 2017 Red Hat, Inc.
Licensed under the GNU General Public License, version 2 as
published by the Free Software Foundation; see COPYING for details.
"""

__author__ = """
olichtne@redhat.com (Ondrej Lichtner)
"""

from lnst.Common.ExecCmd import exec_cmd
from lnst.Devices.MasterDevice import MasterDevice

class BridgeDevice(MasterDevice):
    _name_template = "t_br"
    _link_type = "bridge"

    _linkinfo_data_map = {"ageing_time": "IFLA_BR_AGEING_TIME",
                          "stp_state": "IFLA_BR_STP_STATE",
                          "vlan_filtering": "IFLA_BR_VLAN_FILTERING"}

    # def _get_bridge_dir(self):
        # return "/sys/class/net/%s/bridge" % self.name

    #TODO redo to work with pyroute - select which options are interesing as
    # properties?
    # def set_option(self, option, value):
        # exec_cmd('echo "%s" > %s/%s' % (value,
                                        # self._get_bridge_dir(),
                                        # option))

    # def set_options(self, options):
        # for option, value in options:
            # self.set_option(option, value)
