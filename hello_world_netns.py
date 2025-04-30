from collections.abc import Collection
from lnst.Controller import Controller, HostReq, DeviceReq
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Recipes.ENRT.MeasurementGenerators.FlowMeasurementGenerator import FlowMeasurementGenerator
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Common.IpAddress import Ip4Address
from lnst.Recipes.ENRT.NftablesNetnsRoutingRecipe import NftablesNetnsRoutingRecipe

class HelloWorldNetnsRecipe(NftablesNetnsRoutingRecipe, FlowMeasurementGenerator):

    rulescale = [ 0, 100, 1000, 10000 ]

    @property
    def firewall_rulesets_generator(self):
        base_ruleset = """
table inet t {
    chain input {
        type filter hook input priority filter
    }
}"""
        out = { self.matched.host2: base_ruleset }
        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t input ip saddr 8.8.8.8 counter drop"
            yield out

ctl = Controller()
recipe_instance = HelloWorldNetnsRecipe()
ctl.run(recipe_instance)
