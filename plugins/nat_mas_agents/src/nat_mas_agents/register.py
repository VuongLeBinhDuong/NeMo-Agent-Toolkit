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