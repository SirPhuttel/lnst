from lnst.Common.Parameters import (
    IntParam,
    StrParam,
    DictParam
)
from lnst.Common.IpAddress import interface_addresses
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.DoubleBondRecipe import DoubleBondRecipe


class BaseLACPRecipe(DoubleBondRecipe):
    bonding_mode = StrParam(mandatory=True)
    miimon_value = IntParam(mandatory=True)

    lacp_mode = StrParam(default="ACTIVE", choices=["ACTIVE", "PASSIVE", "ON"])
    topology = DictParam(mandatory=True)
    """
    Topology should be in following format:
    ```
    {
        "SWITCH_LACP_INTERFACE": [
            "INTERFACE1",
            "INTERFACE2"
        ]
    }
    ```
    """

    def test_wide_switch_configuration(self):
        """
        This method needs to implement switch configuration for LACP.
        """
        raise NotImplementedError()

    def test_wide_configuration(self, config):
        """
        This method is almost the same as DoubleBondRecipe.test_wide_configuration,
        however, it configures multiple IP addresses on the bond0 interface as well as
        it calls switch configuration method.
        """
        host1, host2 = self.matched.host1, self.matched.host2
        config = super(DoubleBondRecipe, self).test_wide_configuration(config)

        ipv4_addr = interface_addresses(self.params.net_ipv4)
        ipv6_addr = interface_addresses(self.params.net_ipv6)

        self.create_bond_devices(
            config,
            {
                "host1": {
                    "bond0": [host1.eth0, host1.eth1]
                },
                "host2": {
                    "bond0": [host2.eth0, host2.eth1]
                }
            }
        )

        for host in [host1, host2]:
            host.bond0.xmit_hash_policy = "layer2+3"

            config.configure_and_track_ip(host.bond0, next(ipv4_addr))
            config.configure_and_track_ip(host.bond0, next(ipv4_addr))

            config.configure_and_track_ip(host.bond0, next(ipv6_addr))
            config.configure_and_track_ip(host.bond0, next(ipv6_addr))

            for dev in [host.eth0, host.eth1, host.bond0]:
                dev.up_and_wait()

        self.test_wide_switch_configuration()

        self.wait_tentative_ips(config.configured_devices)

        return config

    def test_wide_switch_deconfiguration(self):
        raise NotImplementedError()

    def test_wide_deconfiguration(self, config):
        self.test_wide_switch_deconfiguration()

        super().test_wide_deconfiguration(config)

    def generate_perf_endpoints(self, config):
        return [ip_endpoint_pairs(config, (self.matched.host1.bond0, self.matched.host2.bond0), combination_func=zip)]
