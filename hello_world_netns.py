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
from lnst.Recipes.ENRT.NftablesRuleScaleRecipe import NftablesRuleScaleRecipe


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
        devs = f"{self.matched.host2.eth0.name}, {self.matched.host2.pn0.name}"
        flowtable_addon = """
table inet t {
    flowtable ft {
        hook ingress priority 0;
        devices = { """ + devs + """ }
    }
}"""
        out = { self.matched.host2: base_ruleset }
        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t forward ip saddr 8.8.8.8 counter drop"
            yield out
        out[self.matched.host2] += "\n" + flowtable_addon
        out[self.matched.host2] += "\nadd rule inet t forward ct state established flow add @ft"
        yield out

        for host in out.keys():
            out[host] = base_ruleset

        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t forward ct state new,established ip saddr 8.8.8.8 drop"
            yield out
        out[self.matched.host2] += "\n" + flowtable_addon
        out[self.matched.host2] += "\nadd rule inet t forward ct state established flow add @ft"
        yield out

        for host in out.keys():
            out[host] = base_ruleset

        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t forward fib saddr . iif oif missing drop"
            yield out
        out[self.matched.host2] += "\n" + flowtable_addon
        out[self.matched.host2] += "\nadd rule inet t forward ct state established flow add @ft"
        yield out

    def generate_sub_configuration_description(self, config):
        desc = super().generate_sub_configuration_description(config)

        for host, ruleset in config.firewall_rulesets.items():
            rslines = ruleset.split("\n")
            nlines = len(rslines)
            desc.append(f"Firewall: ruleset with {nlines} lines on host {host}")

            rules = [l for l in rslines if l.startswith("add rule")]
            if not len(rules):
                return desc

            curidx = 0
            rulesums = {rules[0]: 1}
            for idx in range(1, len(rules)):
                if rules[idx] == rules[curidx]:
                    rulesums[rules[idx]] += 1
                else:
                    curidx = idx
                    rulesums[rules[idx]] = 1
            for k,v in rulesums.items():
                desc.append(f"Firewall: ruleset has {v} times '{k}'")

        return desc


ctl = Controller()
#recipe_instance = HelloWorldNetnsRecipe(perf_tests=["udp_stream"],
#                                        offload_combinations=[])
recipe_instance = NftablesRuleScaleRecipe(perf_tests=["udp_stream"], offload_combinations=[], rule="fib saddr . iif oif missing drop", scale=1000)
ctl.run(recipe_instance)
