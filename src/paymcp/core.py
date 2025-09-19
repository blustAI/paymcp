# paymcp/core.py
from enum import Enum
from .providers import build_providers
from .utils.messages import description_with_price
from .payment.flows import make_flow
from .utils.constants import FlowType
from .state_store import StateStoreProvider, InMemoryStore
from importlib.metadata import version, PackageNotFoundError
import logging
logger = logging.getLogger(__name__)

try:
    __version__ = version("paymcp")
except PackageNotFoundError:
    __version__ = "unknown"

class PayMCP:
    def __init__(self, mcp_instance, providers=None, payment_flow: FlowType = FlowType.TWO_STEP, state_store: StateStoreProvider = None):
        logger.debug(f"PayMCP v{__version__}")
        flow_name = payment_flow.value
        self._wrapper_factory = make_flow(flow_name)
        self.mcp = mcp_instance
        self.providers = build_providers(providers or {})
        # Initialize state store (default to InMemoryStore)
        self.state_store = state_store or InMemoryStore()
        logger.info(f"PayMCP initialized with flow={payment_flow.value}, state_store={self.state_store.__class__.__name__}")
        self._patch_tool()

    def _patch_tool(self):
        original_tool = self.mcp.tool
        def patched_tool(*args, **kwargs):
            def wrapper(func):
                # Read @price decorator
                price_info = getattr(func, "_paymcp_price_info", None)

                if price_info:
                    # --- Create payment using provider ---
                    provider = next(iter(self.providers.values())) #get first one - TODO allow to choose
                    if provider is None:
                        raise RuntimeError(
                            f"No payment provider configured"
                        )

                    # Deferred payment creation, so do not call provider.create_payment here
                    kwargs["description"] = description_with_price(kwargs.get("description") or func.__doc__ or "", price_info)
                    target_func = self._wrapper_factory(
                        func, self.mcp, provider, price_info, self.state_store
                    )
                else:
                    target_func = func

                return original_tool(*args, **kwargs)(target_func)
            return wrapper

        self.mcp.tool = patched_tool