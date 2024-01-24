from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin, IptablesMixin
from lnst.Controller import Controller, HostReq, DeviceReq
from lnst.Recipes.ENRT import BaseEnrtRecipe
import logging

class HelloWorldRecipe(BaseEnrtRecipe, NftablesMixin):
    machine1 = HostReq()
    machine1.nic1 = DeviceReq(label="net1")

    machine2 = HostReq()
    machine2.nic1 = DeviceReq(label="net1")

    @NftablesMixin.firewall_rulesets.getter
    def firewall_rulesets(self):
        ruleset = """
table inet t {
    chain input {
        type filter hook input priority filter
        counter
    }
}"""
        return {self.matched.machine1: ruleset, self.matched.machine2: ruleset}

    def do_tests(self, config):
        self.matched.machine1.nic1.ip_flush()
        self.matched.machine1.nic1.ip_add("192.168.1.1/24")
        self.matched.machine1.nic1.up()
        self.matched.machine2.nic1.ip_flush()
        self.matched.machine2.nic1.ip_add("192.168.1.2/24")
        self.matched.machine2.nic1.up()

        self.matched.machine1.run("ping -c 3 192.168.1.2")
        self.matched.machine1.run("nft list ruleset")
        self.matched.machine2.run("nft list ruleset")

#    def test_wide_configuration(self):
#        return super().test_wide_configuration()

class HelloWorldRecipeIpt(BaseEnrtRecipe, IptablesMixin):
    machine1 = HostReq()
    machine1.nic1 = DeviceReq(label="net1")

    machine2 = HostReq()
    machine2.nic1 = DeviceReq(label="net1")

    @property
    def firewall_rulesets(self):
        ruleset = """
*filter
:INPUT ACCEPT [0:0]
-A INPUT
COMMIT
"""
        return {self.matched.machine1: ruleset, self.matched.machine2: ruleset}

    @firewall_rulesets.setter
    def firewall_rulesets(self, rulesets):
        for host, ruleset in rulesets.items():
            logging.info(f"Applied firewall ruleset from {host}:\n\n{ruleset}")

    def do_tests(self, config):
        self.matched.machine1.nic1.ip_flush()
        self.matched.machine1.nic1.ip_add("192.168.1.1/24")
        self.matched.machine1.nic1.up()
        self.matched.machine2.nic1.ip_flush()
        self.matched.machine2.nic1.ip_add("192.168.1.2/24")
        self.matched.machine2.nic1.up()

        self.matched.machine1.run("ping -c 3 192.168.1.2")
        logging.info(self.matched.machine1.run("iptables-save --counters").stdout)
        logging.info(self.matched.machine2.run("iptables-save --counters").stdout)

ctl = Controller()
recipe_instance = HelloWorldRecipe()
ctl.run(recipe_instance)
