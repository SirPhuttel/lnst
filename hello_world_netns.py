from collections.abc import Collection
from lnst.Controller import Controller, HostReq, DeviceReq
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Recipes.ENRT.MeasurementGenerators.FlowMeasurementGenerator import FlowMeasurementGenerator
from lnst.RecipeCommon.Ping.PingEndpoints import PingEndpoints
from lnst.RecipeCommon.endpoints import EndpointPair, IPEndpoint
from lnst.Recipes.ENRT.helpers import ip_endpoint_pairs
from lnst.Common.IpAddress import Ip4Address
from lnst.Recipes.ENRT.NftablesNetnsRoutingRecipe import NftablesNetnsRoutingRecipe

class HelloWorldNetnsRecipe(FlowMeasurementGenerator, NftablesNetnsRoutingRecipe):

    def test_wide_configuration(self):
        config = super().test_wide_configuration()
        self.test_ifaces = self.configureNetns(config)
        return config

    def generate_ping_endpoints(self, config):
        return [PingEndpoints(self.test_ifaces[0], self.test_ifaces[1])]

    def generate_perf_endpoints(self, config: EnrtConfiguration) -> list[Collection[EndpointPair[IPEndpoint]]]:
        return [ip_endpoint_pairs(config, self.test_ifaces)]

ctl = Controller()
recipe_instance = HelloWorldNetnsRecipe()
ctl.run(recipe_instance)
