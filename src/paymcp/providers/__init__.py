from .stripe import StripeProvider
from .walleot import WalleotProvider   
PROVIDER_MAP = {
    "stripe": StripeProvider,
    "walleot": WalleotProvider
}

def build_providers(config: dict):
    """
    Convert a dict like
        {"stripe": {"apiKey": "..."},
         "walleot": {"apiKey": "..."}}
    into {"stripe": StripeProvider(...), "walleot": WalleotProvider(...)}.
    """
    instances = {}
    for name, kwargs in config.items():
        cls = PROVIDER_MAP.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown provider: {name}")
        instances[name] = cls(**kwargs)
    return instances