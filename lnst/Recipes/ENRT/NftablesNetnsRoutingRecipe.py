from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Common.IpAddress import interface_addresses
from lnst.Common.Parameters import IPv4NetworkParam
from lnst.Devices import VethPair, RemoteDevice
from lnst.Controller import HostReq, DeviceReq
from lnst.Controller.NetNamespace import NetNamespace
import logging

class NftablesNetnsRoutingRecipe(SimpleNetnsRouterRecipe, NftablesMixin):
    pass
