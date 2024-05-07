from collections.abc import Collection
from lnst.Common.Parameters import Param
from lnst.Controller import Controller, HostReq, DeviceReq
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Recipes.ENRT.MeasurementGenerators.FlowMeasurementGenerator import FlowMeasurementGenerator
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Common.IpAddress import Ip4Address
from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin
from lnst.Recipes.ENRT.SimpleNetnsRouterRecipe import SimpleNetnsRouterRecipe


class HelloWorldNetnsRecipe(SimpleNetnsRouterRecipe, NftablesMixin, FlowMeasurementGenerator):

    rulescale = [ 0, 1000, 10000 ]

    @property
    def firewall_rulesets_generator(self):
        base_ruleset = """
flush ruleset
table inet t {
    chain forward {
        type filter hook forward priority filter
    }
}"""
        out = { self.matched.host2: base_ruleset }
        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t forward ip saddr 8.8.8.8 counter drop"
            yield out
        devs = f"{self.matched.host2.eth0.name}, {self.matched.host2.pn0.name}"
        out[self.matched.host2] += "\nadd flowtable inet t ft { hook ingress priority 0; devices = { " + devs + " }; }"
        out[self.matched.host2] += "\nadd rule inet t forward ct state established flow add @ft"
        yield out

        for host in out.keys():
            out[host] = base_ruleset

        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t forward ct state new,established ip saddr 8.8.8.8 drop"
            yield out

ctl = Controller()
recipe_instance = HelloWorldNetnsRecipe(perf_tests=["udp_stream"],
                                        offload_combinations=[])
ctl.run(recipe_instance)
