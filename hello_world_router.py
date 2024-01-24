from collections.abc import Collection
from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin, BulkFirewallMixin
from lnst.Controller import Controller, HostReq, DeviceReq
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Recipes.ENRT.MeasurementGenerators.FlowMeasurementGenerator import FlowMeasurementGenerator
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Common.IpAddress import Ip4Address

class HelloWorldRecipe(BaseEnrtRecipe, FlowMeasurementGenerator,
                       NftablesMixin):

    # Eliminate BaseEnrtRecipe's host reqs
    host1 = None
    host2 = None

    # Add own host reqs instead
    host_a = HostReq(hostname="vfed-lnst1.vnet")
    host_a.eth0 = DeviceReq(label="A")

    router = HostReq(hostname="vfed-lnst2.vnet")
    router.eth0 = DeviceReq(label="A")
    router.eth1 = DeviceReq(label="B")

    host_b = HostReq(hostname="vfed-lnst3.vnet")
    host_b.eth0 = DeviceReq(label="B")

    @property
    def firewall_rulesets_generator(self):
        ruleset = """
table inet t {
    flowtable ft {
        hook ingress priority filter
        devices = { %s, %s }
    }
    chain forward {
        type filter hook forward priority filter
    }
}""" % (self.matched.router.eth0.name, self.matched.router.eth1.name)
        add_rule_pfx = "\nadd rule inet t forward"

        for scale in [0, 100, 1000, 10000];
            for i in range(scale):
                ruleset += add_rule_pfx + "ip saddr 8.8.8.8 counter drop"
            yield { self.matched.router: ruleset }

        ruleset += add_rule_pfx + "meta l4proto tcp counter flow add @ft"
        yield { self.matched.router: ruleset }

    def test_wide_configuration(self):
        config = super().test_wide_configuration()

        config.configure_and_track_ip(self.matched.host_a.eth0,
                                      Ip4Address("192.168.101.1/24"))
        self.matched.host_a.eth0.up_and_wait()
        self.matched.host_a.eth0._ipr_wrapper("route", "add",
                                                  dst="192.168.102.0/24",
                                                  gateway="192.168.101.2")

        config.configure_and_track_ip(self.matched.router.eth0,
                                      Ip4Address("192.168.101.2/24"))
        config.configure_and_track_ip(self.matched.router.eth1,
                                      Ip4Address("192.168.102.2/24"))
        self.matched.router.eth0.up_and_wait()
        self.matched.router.eth1.up_and_wait()
        self.matched.router.run("sysctl -w net.ipv4.ip_forward=1")

        config.configure_and_track_ip(self.matched.host_b.eth0,
                                      Ip4Address("192.168.102.1/24"))
        self.matched.host_b.eth0.up_and_wait()
        self.matched.host_b.eth0._ipr_wrapper("route", "add",
                                                  dst="192.168.101.0/24",
                                                  gateway="192.168.102.2")

        self.wait_tentative_ips(config.configured_devices)
        return config

    def generate_ping_endpoints(self, config):
        return [PingEndpoints(self.matched.host_a.eth0,
                              self.matched.host_b.eth0)]

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        return [ip_endpoint_pairs(config, (self.matched.host_a.eth0,
                                           self.matched.host_b.eth0))]

ctl = Controller()
recipe_instance = HelloWorldRecipe(ip_versions=('ipv4',),
                                   ping_count=3,
                                   perf_duration=10,
                                   perf_iterations=1,
                                   perf_tests=['tcp_stream'])
ctl.run(recipe_instance)
