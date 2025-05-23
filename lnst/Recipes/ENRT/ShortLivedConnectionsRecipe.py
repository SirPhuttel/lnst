from collections.abc import Collection
from lnst.Common.IpAddress import interface_addresses
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.BaremetalEnrtRecipe import BaremetalEnrtRecipe
from lnst.Common.Parameters import (
    Param,
    ListParam,
    ChoiceParam,
    StrParam,
    IPv4NetworkParam,
)
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration
from lnst.Recipes.ENRT.ConfigMixins.CommonHWSubConfigMixin import (
    CommonHWSubConfigMixin)
from lnst.Recipes.ENRT.RecipeReqs import SimpleNetworkReq


class ShortLivedConnectionsRecipe(CommonHWSubConfigMixin, SimpleNetworkReq, BaremetalEnrtRecipe):
    net_ipv4 = IPv4NetworkParam(default="192.168.101.0/24")

    # Neper is the only option for RR type tests.
    net_perf_tool = ChoiceParam(default='neper', type=StrParam, choices=set(['neper']))

    perf_tests = Param(default=("tcp_rr", "tcp_crr", "udp_rr"))
    ip_versions = Param(default=("ipv4",))
    perf_msg_sizes = ListParam(default=[1000, 5000, 7000, 10000, 12000])

    def test_wide_configuration(self, config):
        host1, host2 = self.matched.host1, self.matched.host2

        config = super().test_wide_configuration(config)

        ipv4_addr = interface_addresses(self.params.net_ipv4, default_start="192.168.101.10/24")
        for host in [host1, host2]:
            host.eth0.down()
            config.configure_and_track_ip(host.eth0, next(ipv4_addr))
            host.eth0.up()

        self.wait_tentative_ips(config.configured_devices)

        return config

    def generate_test_wide_description(self, config: EnrtConfiguration):
        desc = super().generate_test_wide_description(config)
        desc += [
            "\n".join([
                "Configured {}.{}.ips = {}".format(
                    dev.host.hostid, dev.name, dev.ips
                )
                for dev in config.configured_devices
            ])
        ]
        return desc

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        return [ip_endpoint_pairs(config, (self.matched.host1.eth0, self.matched.host2.eth0))]

    @property
    def mtu_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def dev_interrupt_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def parallel_stream_qdisc_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]
