import logging
from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from . import workflow_coordinator
from . import product_manager_phase
from . import architect_phase
from . import project_manager_phase
from . import engineer_phase
from . import tester_phase
from . import integrator_phase

logger = logging.getLogger(__name__)

# Explicitly import registered functions to ensure decorators execute
# This helps catch any import errors and ensures registration happens
try:
    from .engineer_phase import mas_engineer_phase  # noqa: F401
except Exception as e:
    logger.warning(f"Could not import mas_engineer_phase: {e}")

try:
    from .tester_phase import mas_tester_phase  # noqa: F401
except Exception as e:
    logger.warning(f"Could not import mas_tester_phase: {e}")

try:
    from .integrator_phase import mas_integrator_phase  # noqa: F401
except Exception as e:
    logger.warning(f"Could not import mas_integrator_phase: {e}")


class MASProductManagerConfig(FunctionBaseConfig, name="mas_product_manager"):
    """Invoke MAS ProductManager and return its Final Answer (text)."""
    description: str = Field(default="MAS Product Manager wrapper")


@register_function(config_type=MASProductManagerConfig)
async def mas_product_manager(config: MASProductManagerConfig, builder: Builder):
    async def _response_fn(input_message: str) -> str:
        from mas_agents.nat_integration import NATProductManagerFn
        fn = NATProductManagerFn()
        return await fn(input_message)

    yield FunctionInfo.create(single_fn=_response_fn)


class MASArchitectConfig(FunctionBaseConfig, name="mas_architect"):
    """Invoke MAS SoftwareArchitect and return its Final Answer (text)."""
    description: str = Field(default="MAS Architect wrapper")


@register_function(config_type=MASArchitectConfig)
async def mas_architect(config: MASArchitectConfig, builder: Builder):
    async def _response_fn(input_message: str) -> str:
        from mas_agents.nat_integration import NATArchitectFn
        fn = NATArchitectFn()
        return await fn(input_message)

    yield FunctionInfo.create(single_fn=_response_fn)


class MASProjectManagerConfig(FunctionBaseConfig, name="mas_project_manager"):
    """Invoke MAS ProjectManager and return its Final Answer (text)."""
    description: str = Field(default="MAS Project Manager wrapper")


@register_function(config_type=MASProjectManagerConfig)
async def mas_project_manager(config: MASProjectManagerConfig, builder: Builder):
    async def _response_fn(input_message: str) -> str:
        from mas_agents.nat_integration import NATProjectManagerFn
        fn = NATProjectManagerFn()
        return await fn(input_message)

    yield FunctionInfo.create(single_fn=_response_fn)
