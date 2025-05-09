from collections.abc import Collection
from lnst.Common.Parameters import (
    Param,
    IntParam,
    IPv4NetworkParam,
    IPv6NetworkParam,
)
from lnst.Common.IpAddress import interface_addresses
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.BaremetalEnrtRecipe import BaremetalEnrtRecipe
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration
from lnst.Recipes.ENRT.ConfigMixins.OffloadSubConfigMixin import (
    OffloadSubConfigMixin)
from lnst.Recipes.ENRT.ConfigMixins.CommonHWSubConfigMixin import (
    CommonHWSubConfigMixin)
from lnst.Recipes.ENRT.ConfigMixins.PerfReversibleFlowMixin import (
    PerfReversibleFlowMixin)
from lnst.Recipes.ENRT.BondingMixin import BondingMixin
from lnst.Devices import VlanDevice
from lnst.Devices.VlanDevice import VlanDevice as Vlan
from lnst.Recipes.ENRT.PingMixins import VlanPingEvaluatorMixin
from lnst.Recipes.ENRT.RecipeReqs import BondOrTeamReq
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints


class VlansOverBondRecipe(BondingMixin, PerfReversibleFlowMixin, VlanPingEvaluatorMixin,
    CommonHWSubConfigMixin, OffloadSubConfigMixin,
    BondOrTeamReq, BaremetalEnrtRecipe):
    r"""
    This recipe implements Enrt testing for a network scenario that looks
    as follows

    .. code-block:: none

                              .--------.
                .-------------+ switch +--------.
                |         .---+        |        |
                |         |   '--------'        |
          .-----|---------|----.                |
          | .---'--.  .---'--. |             .--'---.
        .-|-| eth0 |--| eth1 |-|-.   .-------| eth0 |------.
        | | '------'  '------' | |   |       '------'      |
        | |        bond0       | |   |      /   |    \     |
        | '-------/--|--\------' |   | vlan0  vlan1  vlan2 |
        |        /   |   \       |   | id=10  id=20  id=30 |
        |   vlan0  vlan1  vlan2  |   |                     |
        |   id=10  id=20  id=30  |   |                     |
        |                        |   |                     |
        |          host1         |   |        host2        |
        '------------------------'   '---------------------'

    Refer to :any:`BondingMixin` for parameters to configure the bonding
    device.

    All sub configurations are included via Mixin classes.

    The actual test machinery is implemented in the :any:`BaseEnrtRecipe` class.
    """
    vlan0_id = IntParam(default=10)
    vlan1_id = IntParam(default=20)
    vlan2_id = IntParam(default=30)

    offload_combinations = Param(default=(
        dict(gro="on", gso="on", tso="on", tx="on"),
        dict(gro="off", gso="on", tso="on", tx="on"),
        dict(gro="on", gso="off", tso="off", tx="on"),
        dict(gro="on", gso="on", tso="off", tx="off")))

    vlan0_ipv4 = IPv4NetworkParam(default="192.168.10.0/24")
    vlan0_ipv6 = IPv6NetworkParam(default="fc00:0:0:1::/64")

    vlan1_ipv4 = IPv4NetworkParam(default="192.168.20.0/24")
    vlan1_ipv6 = IPv6NetworkParam(default="fc00:0:0:2::/64")

    vlan2_ipv4 = IPv4NetworkParam(default="192.168.30.0/24")
    vlan2_ipv6 = IPv6NetworkParam(default="fc00:0:0:3::/64")

    def test_wide_configuration(self, config):
        """
        Test wide configuration for this recipe involves creating one bonding
        device on the first host. This device bonds two NICs matched by the
        recipe. The bonding mode and miimon interval is configured on the
        bonding device according to the recipe parameters. Then three
        VLAN (802.1Q) tunnels are created on top of the bonding device on the
        first host and on the matched NIC on the second host. The tunnels are
        configured with VLAN ids from vlan0_id, vlan1_id and vlan2_id params (by
        default: 10, 20, 30).

        An IPv4 and IPv6 address is configured on each tunnel endpoint.

        | host1.vlan0 = 192.168.10.1/24 and fc00:0:0:1::1/64
        | host1.vlan1 = 192.168.20.1/24 and fc00:0:0:2::1/64
        | host1.vlan2 = 192.168.30.1/24 and fc00:0:0:3::1/64

        | host2.vlan0 = 192.168.10.2/24 and fc00:0:0:1::2/64
        | host2.vlan1 = 192.168.20.2/24 and fc00:0:0:2::2/64
        | host2.vlan2 = 192.168.30.2/24 and fc00:0:0:3::2/64
        """
        host1, host2 = self.matched.host1, self.matched.host2
        config = super().test_wide_configuration(config)

        self.create_bond_devices(
            config,
            {
                "host1":
                {
                    "bond0": [host1.eth0, host1.eth1]
                }
            }
        )

        host1.vlan0 = VlanDevice(realdev=host1.bond0, vlan_id=self.params.vlan0_id)
        host1.vlan1 = VlanDevice(realdev=host1.bond0, vlan_id=self.params.vlan1_id)
        host1.vlan2 = VlanDevice(realdev=host1.bond0, vlan_id=self.params.vlan2_id)
        host2.vlan0 = VlanDevice(realdev=host2.eth0, vlan_id=self.params.vlan0_id)
        host2.vlan1 = VlanDevice(realdev=host2.eth0, vlan_id=self.params.vlan1_id)
        host2.vlan2 = VlanDevice(realdev=host2.eth0, vlan_id=self.params.vlan2_id)

        config.track_device(host1.bond0)

        vlan0_ipv4_addr = interface_addresses(self.params.vlan0_ipv4)
        vlan0_ipv6_addr = interface_addresses(self.params.vlan0_ipv6)
        vlan1_ipv4_addr = interface_addresses(self.params.vlan1_ipv4)
        vlan1_ipv6_addr = interface_addresses(self.params.vlan1_ipv6)
        vlan2_ipv4_addr = interface_addresses(self.params.vlan2_ipv4)
        vlan2_ipv6_addr = interface_addresses(self.params.vlan2_ipv6)

        for host in [host1, host2]:
            config.configure_and_track_ip(host.vlan0, next(vlan0_ipv4_addr))
            config.configure_and_track_ip(host.vlan1, next(vlan1_ipv4_addr))
            config.configure_and_track_ip(host.vlan2, next(vlan2_ipv4_addr))
            config.configure_and_track_ip(host.vlan0, next(vlan0_ipv6_addr))
            config.configure_and_track_ip(host.vlan1, next(vlan1_ipv6_addr))
            config.configure_and_track_ip(host.vlan2, next(vlan2_ipv6_addr))

        for dev in [host1.eth0, host1.eth1, host1.bond0, host1.vlan0,
            host1.vlan1, host1.vlan2, host2.eth0, host2.vlan0,
            host2.vlan1, host2.vlan2]:
            dev.up()

        self.wait_tentative_ips(config.configured_devices)

        return config

    def generate_test_wide_description(self, config: EnrtConfiguration):
        desc = super().generate_test_wide_description(config)
        desc += [
            "\n".join([
                "Configured {}.{}.ips = {}".format(
                    dev.host.hostid, dev.name, dev.ips
                )
                for dev in config.configured_devices if isinstance(dev,
                    Vlan)
            ]),
            "\n".join([
                "Configured {}.{}.vlan_id = {}".format(
                    dev.host.hostid, dev.name, dev.vlan_id
                )
                for dev in config.configured_devices if isinstance(dev,
                    Vlan)
            ]),
            "\n".join([
                "Configured {}.{}.realdev = {}".format(
                    dev.host.hostid, dev.name,
                    '.'.join([dev.host.hostid, dev.realdev.name])
                )
                for dev in config.configured_devices if isinstance(dev,
                    Vlan)
            ]),
        ]

        return desc

    def generate_ping_endpoints(self, config):
        """
        The ping endpoints for this recipe are the matching VLAN tunnel
        endpoints of the hosts.

        Returned as::

            [PingEndpoints(host1.vlan0, host2.vlan0),
             PingEndpoints(host1.vlan1, host2.vlan1),
             PingEndpoints(host1.vlan2, host2.vlan2)]
        """
        host1, host2 = self.matched.host1, self.matched.host2

        return [PingEndpoints(host1.vlan0, host2.vlan0),
                PingEndpoints(host1.vlan1, host2.vlan1),
                PingEndpoints(host1.vlan2, host2.vlan2)]


    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        """
        The perf endpoints for this recipe are the VLAN tunnel endpoints with
        VLAN id from parameter vlan_ids[0] (by default: 10):

        host1.vlan0 and host2.vlan0
        """
        return [ip_endpoint_pairs(config, (self.matched.host1.vlan0, self.matched.host2.vlan0))]

    @property
    def offload_nics(self):
        """
        The `offload_nics` property value for this scenario is a list of the
        physical devices carrying data of the configured VLAN tunnels:

        host1.eth0, host1.eth1 and host2.eth0

        For detailed explanation of this property see :any:`OffloadSubConfigMixin`
        class and :any:`OffloadSubConfigMixin.offload_nics`.
        """
        host1, host2 = self.matched.host1, self.matched.host2
        return [host1.eth0, host1.eth1, host2.eth0]

    @property
    def mtu_hw_config_dev_list(self):
        """
        The `mtu_hw_config_dev_list` property value for this scenario is a
        list of all configured VLAN tunnel devices and the underlying bonding
        or physical devices:

        | host1.bond0, host1.vlan0, host1.vlan1, host1.vlan2
        | host2.eth0, host2.vlan0, host2.vlan1, host2.vlan2

        For detailed explanation of this property see :any:`MTUHWConfigMixin`
        class and :any:`MTUHWConfigMixin.mtu_hw_config_dev_list`.
        """
        host1, host2 = self.matched.host1, self.matched.host2
        result = []
        for host in [host1, host2]:
            for dev in [host.vlan0, host.vlan1, host.vlan2]:
                result.append(dev)
        result.extend([host1.bond0, host2.eth0])
        return result

    @property
    def dev_interrupt_hw_config_dev_list(self):
        """
        The `dev_interrupt_hw_config_dev_list` property value for this scenario
        is a list of the physical devices carrying data of the configured
        VLAN tunnels:

        host1.eth0, host1.eth1 and host2.eth0

        For detailed explanation of this property see :any:`DevInterruptHWConfigMixin`
        class and :any:`DevInterruptHWConfigMixin.dev_interrupt_hw_config_dev_list`.
        """
        host1, host2 = self.matched.host1, self.matched.host2
        return [host1.eth0, host1.eth1, host2.eth0]

    @property
    def parallel_stream_qdisc_hw_config_dev_list(self):
        """
        The `parallel_stream_qdisc_hw_config_dev_list` property value for
        this scenario is a list of the physical devices carrying data of the
        configured VLAN tunnels:

        host1.eth0, host1.eth1 and host2.eth0

        For detailed explanation of this property see
        :any:`ParallelStreamQDiscHWConfigMixin` class and
        :any:`ParallelStreamQDiscHWConfigMixin.parallel_stream_qdisc_hw_config_dev_list`.
        """
        host1, host2 = self.matched.host1, self.matched.host2
        return [host1.eth0, host1.eth1, host2.eth0]

    @property
    def pause_frames_dev_list(self):
        """
        The `pause_frames_dev_list` property value for this scenario is a list
        of the physical devices carrying data of the configured VLAN tunnels:

        host1.eth0, host1.eth1 and host2.eth0

        For detailed explanation of this property see
        :any:`PauseFramesHWConfigMixin` and
        :any:`PauseFramesHWConfigMixin.pause_frames_dev_list`.
        """
        host1, host2 = self.matched.host1, self.matched.host2
        return [host1.eth0, host1.eth1, host2.eth0]

    @property
    def vf_trust_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host1.eth1]
