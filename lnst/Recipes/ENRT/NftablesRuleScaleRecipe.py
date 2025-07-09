from lnst.Recipes.ENRT.SimpleNetnsRouterRecipe import SimpleNetnsRouterRecipe
from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin
from lnst.Recipes.ENRT.MeasurementGenerators.FlowMeasurementGenerator import FlowMeasurementGenerator
from lnst.Common.Parameters import StrParam, IntParam, BoolParam

class NftablesRuleScaleRecipe(SimpleNetnsRouterRecipe, NftablesMixin, FlowMeasurementGenerator):
    """
    :param rule:
        The actual rule to insert repeatedly into the router's forwarding
        chain.
    :type rule: :any:`StrParam` representing the nftables rule.

    :param scale:
        The number of times to insert :any:`rule` into the ruleset.
    :type scale: :any:`IntParam` > 0

    :param flowtable:
        Whether to offload established connections to a flowtable or not.
    :type flowtable: :any:`BoolParam`
    """
    rule = StrParam(mandatory=True)
    scale = IntParam(mandatory=True)
    flowtable = BoolParam(mandatory=False, default=False)

    @property
    def firewall_rulesets_generator(self):
        rule = self.params.get('rule', None)
        scale = self.params.get('scale', None)
        ruleset = [
            "flush ruleset",
            "add table inet t",
            "add chain inet t forward { type filter hook forward priority filter; }",
        ]
        ruleset.extend([f"add rule inet t forward {rule}" for s in range(scale)])
        if self.params.get('flowtable', None):
            devs = f"{self.matched.host2.eth0.name}, {self.matched.host2.pn0.name}"
            ftspec = f"hook ingress priority filter; devices = {{ {devs} }};"
            ruleset.append(f"add flowtable inet t ft {{ {ftspec} }}")
            ruleset.append("add rule inet t forward ct state established flow add @ft")
        yield { self.matched.host2: "\n".join(ruleset) }

    def generate_sub_configuration_description(self, config):
        rule = self.params.get('rule', None)
        scale = self.params.get('scale', None)
        desc = super().generate_sub_configuration_description(config)
        msg = f"NftablesScale: Ruleset with {scale} times '{rule}'"
        if self.params.get('flowtable', None):
            msg += " and a flowtable"
        desc.append(msg)
        return desc
