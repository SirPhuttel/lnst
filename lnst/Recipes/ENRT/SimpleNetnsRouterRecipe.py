from collections.abc import Collection
from lnst.Recipes.ENRT.SimpleNetworkRecipe import SimpleNetworkRecipe
from lnst.Common.Parameters import IPv4NetworkParam, IPv6NetworkParam
from lnst.Common.IpAddress import interface_addresses
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.Controller.NetNamespace import NetNamespace
from lnst.Devices.VethPair import VethPair

class SimpleNetnsRouterRecipe(SimpleNetworkRecipe):
    """
    This recipe implements Enrt testing for a simple network scenario that looks as follows

    (pic: Just like SimpleNetworkRecipe but with netns in host2)
    """
    netns_ipv4 = IPv4NetworkParam(default="192.168.102.0/24")

    def test_wide_configuration(self, config):
        host2 = self.matched.host2

        host2.ns = NetNamespace("host2ns")

        host2.pn0, host2.np0 = VethPair()
        host2.ns.np0 = host2.np0

        ipv4_addr = interface_addresses(self.params.netns_ipv4)
        pn0_addr = next(ipv4_addr)
        config.configure_and_track_ip(host2.pn0, pn0_addr)
        host2.pn0.up_and_wait()
        config.configure_and_track_ip(host2.ns.np0, next(ipv4_addr))
        host2.ns.np0.up_and_wait()

        host2.ns.np0._ipr_wrapper("route", "add", dst="default",
                                  gateway=f"{pn0_addr}")
        host2.run("sysctl -w net.ipv4.ip_forward=1")

        host1.eth0._ipr_wrapper("route", "add", dst=netns_ipv4,
                                gateway=f"{host2.eth0.ips()[-1]}")
        return config

    def generate_ping_endpoints(self, config):
        return [PingEndpoints(self.matched.host1.eth0, self.matched.host2.ns.np0)]

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        return [ip_endpoint_pairs(config, (self.matched.host1.eth0, self.matched.host2.ns.np0))]
