from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Common.IpAddress import interface_addresses
from lnst.Common.Parameters import IPv4NetworkParam
from lnst.Devices import VethPair, RemoteDevice
from lnst.Controller import HostReq, DeviceReq
from lnst.Controller.NetNamespace import NetNamespace
import logging

class NftablesNetnsRoutingRecipe(BaseEnrtRecipe, NftablesMixin):

    # Eliminate BaseEnrtRecipe's second host req
    host1 = HostReq()
    host1.nic1 = DeviceReq(label="net1")
    host2 = None

    net1_ipv4 = IPv4NetworkParam(default="192.168.101.0/24")
    net2_ipv4 = IPv4NetworkParam(default="192.168.102.0/24")

    def configureNetns(self, config: EnrtConfiguration) -> tuple[RemoteDevice, RemoteDevice]:
        host1 = self.matched.host1

        host1.rns = NetNamespace("router")
        host1.sns = NetNamespace("server")

        host1.cr0, host1.rc0 = VethPair()
        host1.rs0, host1.sr0 = VethPair()

        host1.rns.rc0 = host1.rc0
        host1.rns.rs0 = host1.rs0
        host1.sns.sr0 = host1.sr0

        ipv4_addr = interface_addresses(self.params.net1_ipv4)
        config.configure_and_track_ip(host1.cr0, next(ipv4_addr))
        host1.cr0.up_and_wait()
        rc0_addr = next(ipv4_addr)
        config.configure_and_track_ip(host1.rns.rc0, rc0_addr)
        host1.rns.rc0.up_and_wait()

        ipv4_addr = interface_addresses(self.params.net2_ipv4)
        rs0_addr = next(ipv4_addr)
        config.configure_and_track_ip(host1.rns.rs0, rs0_addr)
        logging.info(host1.rns.run("ip a s"))
        host1.rns.rs0.up_and_wait()
        config.configure_and_track_ip(host1.sns.sr0, next(ipv4_addr))
        host1.sns.sr0.up_and_wait()

        host1.cr0._ipr_wrapper("route", "add", dst=f"{self.params.net2_ipv4}",
                               gateway=f"{rc0_addr}")
        host1.sns.sr0._ipr_wrapper("route", "add", dst=f"{self.params.net1_ipv4}",
                                   gateway=f"{rs0_addr}")

        host1.rns.run("sysctl -w net.ipv4.ip_forward=1")

        return (host1.cr0, host1.sns.sr0)
