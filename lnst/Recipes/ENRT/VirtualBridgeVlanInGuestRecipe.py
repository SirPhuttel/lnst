from collections.abc import Collection
from lnst.Common.Parameters import Param, IntParam, IPv4NetworkParam, IPv6NetworkParam
from lnst.Common.IpAddress import interface_addresses
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Recipes.ENRT.BaseEnrtRecipe import EnrtConfiguration
from lnst.Recipes.ENRT.VirtualEnrtRecipe import VirtualEnrtRecipe
from lnst.Recipes.ENRT.ConfigMixins.OffloadSubConfigMixin import (
    OffloadSubConfigMixin)
from lnst.Recipes.ENRT.ConfigMixins.CommonHWSubConfigMixin import (
    CommonHWSubConfigMixin)
from lnst.Recipes.ENRT.RecipeReqs import VirtualBridgeReq
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.Devices import VlanDevice
from lnst.Devices.VlanDevice import VlanDevice as Vlan
from lnst.Devices import BridgeDevice

class VirtualBridgeVlanInGuestRecipe(CommonHWSubConfigMixin,
    OffloadSubConfigMixin, VirtualBridgeReq, VirtualEnrtRecipe):
    vlan_id = IntParam(default=10)

    offload_combinations = Param(default=(
        dict(gro="on", gso="on", tso="on", tx="on", rx="on"),
        dict(gro="off", gso="on", tso="on", tx="on", rx="on"),
        dict(gro="on", gso="off", tso="off", tx="on", rx="on"),
        dict(gro="on", gso="on", tso="off", tx="off", rx="on"),
        dict(gro="on", gso="on", tso="on", tx="on", rx="off")))

    net_ipv4 = IPv4NetworkParam(default="192.168.10.0/24")
    net_ipv6 = IPv6NetworkParam(default="fc00:0:0:1::/64")

    def test_wide_configuration(self, config):
        host1, host2, guest1 = (self.matched.host1, self.matched.host2,
            self.matched.guest1)

        host1.br0 = BridgeDevice()
        for dev in [host1.eth0, host1.tap0]:
            dev.down()
            host1.br0.slave_add(dev)

        host2.eth0.down()
        guest1.eth0.down()

        host2.vlan0 = VlanDevice(realdev=host2.eth0, vlan_id=self.params.vlan_id)
        guest1.vlan0 = VlanDevice(realdev=guest1.eth0, vlan_id=self.params.vlan_id)

        config = super().test_wide_configuration(config)

        ipv4_addr = interface_addresses(self.params.net_ipv4)
        ipv6_addr = interface_addresses(self.params.net_ipv6, default_start="fc00:0:0:1::2/64")

        config.configure_and_track_ip(host1.br0, next(ipv4_addr))
        for machine in [host2, guest1]:
            config.configure_and_track_ip(machine.vlan0, next(ipv4_addr))
            config.configure_and_track_ip(machine.vlan0, next(ipv6_addr))

        for dev in [host1.eth0, host1.tap0, host1.br0, host2.eth0,
                    host2.vlan0, guest1.eth0, guest1.vlan0]:
            dev.up()

        self.wait_tentative_ips(config.configured_devices)

        return config

    def generate_test_wide_description(self, config: EnrtConfiguration):
        host1, host2 = self.matched.host1, self.matched.host2
        desc = super().generate_test_wide_description(config)
        desc += [
            "\n".join([
                "Configured {}.{}.ips = {}".format(
                    dev.host.hostid, dev.name, dev.ips
                )
                for dev in config.configured_devices
            ]),
            "\n".join([
                "Configured {}.{}.vlan_id = {}".format(
                    dev.host.hostid, dev.name, dev.vlan_id
                )
                for dev in config.configured_devices if isinstance(dev,
                    Vlan)
            ]),
            "\n".join([
                "Configured {}.{}.realdev = {}".format(
                    dev.host.hostid, dev.name,
                    '.'.join([dev.host.hostid, dev.realdev.name])
                )
                for dev in config.configured_devices if isinstance(dev,
                    Vlan)
            ]),
            "Configured {}.{}.slaves = {}".format(
                host1.hostid, host1.br0.name,
                ['.'.join([host1.hostid, slave.name])
                for slave in host1.br0.slaves]
            )
        ]
        return desc

    def generate_ping_endpoints(self, config):
        return [PingEndpoints(self.matched.guest1.vlan0, self.matched.host2.vlan0)]

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        return [ip_endpoint_pairs(config, (self.matched.guest1.vlan0, self.matched.host2.vlan0))]

    @property
    def offload_nics(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0,
            self.matched.guest1.eth0]

    @property
    def mtu_hw_config_dev_list(self):
        host1, host2, guest1 = (self.matched.host1, self.matched.host2,
            self.matched.guest1)
        return [host1.eth0, host1.tap0, host1.br0, guest1.eth0,
            host2.eth0, host2.vlan0, guest1.vlan0]

    @property
    def dev_interrupt_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]

    @property
    def parallel_stream_qdisc_hw_config_dev_list(self):
        return [self.matched.host1.eth0, self.matched.host2.eth0]
