from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin, IptablesMixin
from lnst.Controller import Controller, HostReq, DeviceReq
from lnst.Recipes.ENRT.SimpleNetworkRecipe import BaseSimpleNetworkRecipe
from lnst.Recipes.ENRT import BaseEnrtRecipe
from lnst.Recipes.ENRT.MeasurementGenerators.FlowMeasurementGenerator import FlowMeasurementGenerator

# XXX: use SimpleNetworkRecipe and disable offload choices?
class HelloWorldRecipe(BaseSimpleNetworkRecipe, FlowMeasurementGenerator, NftablesMixin):

    rulescale = [ 0, 100, 1000, 10000 ]

    @property
    def firewall_rulesets_generator(self):
        base_ruleset = """
table inet t {
    chain input {
        type filter hook input priority filter
    }
}"""
        out = {
                self.matched.host1: base_ruleset,
                self.matched.host2: base_ruleset
        }
        for rs in self.rulescale:
            for host in out.keys():
                for i in range(rs):
                    out[host] += "\nadd rule inet t input ip saddr 8.8.8.8 counter drop"
            yield out

class HelloWorldRecipeIpt(BaseSimpleNetworkRecipe, FlowMeasurementGenerator, IptablesMixin):

    rulescale = [ 0, 100, 1000, 10000 ]

    @property
    def firewall_rulesets_generator(self):
        ruleset = "*filter"
        for rs in self.rulescale:
            for i in range(rs):
                ruleset += "\n-A INPUT -s 8.8.8.8 -j DROP"
            out = {
                    self.matched.host1: ruleset + "\nCOMMIT",
                    self.matched.host2: ruleset + "\nCOMMIT",
            }
            yield out

ctl = Controller()
recipe_instance = HelloWorldRecipe(ip_versions=('ipv4',), perf_duration=10, perf_iterations=1, perf_tests=['tcp_stream'])
ctl.run(recipe_instance)

recipe_instance = HelloWorldRecipeIpt(ip_versions=('ipv4',), perf_duration=10, perf_iterations=1, perf_tests=['tcp_stream'])
ctl.run(recipe_instance)
