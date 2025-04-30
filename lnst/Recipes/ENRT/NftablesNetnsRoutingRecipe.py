from lnst.Recipes.ENRT.ConfigMixins.FirewallMixin import NftablesMixin
from lnst.Recipes.ENRT.BaseEnrtRecipe import BaseEnrtRecipe, EnrtConfiguration
from lnst.Recipes.ENRT.SimpleNetnsRoutingRecipe import SimpleNetnsRoutingRecipe

class NftablesNetnsRoutingRecipe(SimpleNetnsRouterRecipe, NftablesMixin):
    pass
