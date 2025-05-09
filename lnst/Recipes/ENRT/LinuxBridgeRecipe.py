from collections.abc import Collection
from lnst.Common.Parameters import IPv4NetworkParam, IPv6NetworkParam, Param
from lnst.Common.IpAddress import interface_addresses
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.BaremetalEnrtRecipe import BaremetalEnrtRecipe
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration
from lnst.Recipes.ENRT.ConfigMixins.CommonHWSubConfigMixin import CommonHWSubConfigMixin
from lnst.Recipes.ENRT.ConfigMixins.OffloadSubConfigMixin import (
    OffloadSubConfigMixin,
)
from lnst.Recipes.ENRT.RecipeReqs import SimpleNetworkReq
from lnst.Devices import BridgeDevice


class LinuxBridgeRecipe(CommonHWSubConfigMixin, OffloadSubConfigMixin, SimpleNetworkReq, BaremetalEnrtRecipe):
    """
    This recipe implements Enrt testing for a simple network scenario that looks
    as follows

    .. code-block:: none

                    +--------+
             +------+ switch +-----+
             |      +--------+     |
          +--+-+                 +-+--+
        +-|eth0|-+             +-|eth0|-+
        | +----+ |             | +----+ |
        |   |    |             |   |    |
        |  br0   |             |  br0   |
        |        |             |        |
        | host1  |             | host2  |
        +--------+             +--------+

    All sub configurations are included via Mixin classes.

    The actual test machinery is implemented in the :any:`BaseEnrtRecipe` class.
    """
    offload_combinations = Param(
        default=(
            dict(gro="on", gso="on", tso="on", tx="on", rx="on"),
        )
    )

    net_ipv4 = IPv4NetworkParam(default="192.168.101.0/24")
    net_ipv6 = IPv6NetworkParam(default="fc00::/64")

    def test_wide_configuration(self, config):
        """
        Test wide configuration for this recipe involves adding the matched
        NICs into a Linux bridge and configuring an IPv4 and IPv6 address
        on the bridge device on both hosts.

        host1.br0 = 192.168.101.1/24 and fc00::1/64

        host2.br0 = 192.168.101.2/24 and fc00::2/64
        """
        host1, host2 = self.matched.host1, self.matched.host2
        config = super().test_wide_configuration(config)

        ipv4_addr = interface_addresses(self.params.net_ipv4)
        ipv6_addr = interface_addresses(self.params.net_ipv6)

        for host in [host1, host2]:
            host.br0 = BridgeDevice()
            host.eth0.down()
            host.br0.slave_add(host.eth0)
            host.eth0.up_and_wait()
            host.br0.up_and_wait()
            config.configure_and_track_ip(host.br0, next(ipv4_addr))
            config.configure_and_track_ip(host.br0, next(ipv6_addr))

        self.wait_tentative_ips(config.configured_devices)

        return config

    def generate_test_wide_description(self, config: EnrtConfiguration):
        """
        Test wide description is extended with the configured addresses
        """
        desc = super().generate_test_wide_description(config)
        desc += [
            "\n".join(
                [
                    "Created bridge device {} on host {}".format(
                        dev.name,
                        dev.host.hostid,
                    )
                    for dev in config.configured_devices
                ]
            ),
            "\n".join(
                [
                    "Added device {} to bridge device {} on host {}".format(
                        dev.name,
                        br_dev.name,
                        dev.host.hostid,
                    )
                    for br_dev in config.configured_devices
                    for dev in br_dev.slaves
                ]
            ),
            "\n".join(
                [
                    "Configured {}.{}.ips = {}".format(
                        dev.host.hostid, dev.name, dev.ips
                    )
                    for dev in config.configured_devices
                ]
            ),
        ]
        return desc

    def generate_ping_endpoints(self, config):
        """
        The ping endpoints for this recipe are the created bridge devices:

        host1.br0 and host2.br0

        Returned as::

            [PingEndpoints(self.matched.host1.br0, self.matched.host2.br0)]
        """
        return [PingEndpoints(self.matched.host1.br0, self.matched.host2.br0)]

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        """
        The perf endpoints for this recipe are the created bridge devices:

        host1.br0 and host2.br0
        """
        return [ip_endpoint_pairs(config, (self.matched.host1.br0, self.matched.host2.br0))]

    @property
    def pause_frames_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def offload_nics(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def mtu_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def dev_interrupt_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def parallel_stream_qdisc_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]
