# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from . import weather_update_tool  # noqa: F401  # pylint: disable=unused-import

logger = logging.getLogger(__name__)


class ADKAIQConfig(FunctionBaseConfig, name="adk"):
    description: str
    llm_name: str
    tool_names: list[str] = []


@register_function(config_type=ADKAIQConfig, framework_wrappers=[LLMFrameworkEnum.ADK])
async def adk_demo(config: ADKAIQConfig, builder: Builder):

    from google.adk import Runner
    from google.adk.agents import Agent
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    model = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.ADK)
    tools = builder.get_tools(config.tool_names, wrapper_type=LLMFrameworkEnum.ADK)

    agent = Agent(
        name="weather_time_agent",
        model=model,
        description=("Agent to answer questions about the time and weather in a city."),
        instruction=(
            "You are a helpful agent who can answer user questions "
            "about weather in a city. You also have a sub-agent "
            "that can answer questions about the time in a city."
        ),
        tools=tools,
    )

    # Initialize the Runner with the agent and services
    app_name = "my_app"
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )
    user_id_1 = "user1"
    session_11 = await session_service.create_session(
        app_name=app_name, user_id=user_id_1
    )

    async def _response_fn(input_message: str) -> str:

        async def run_prompt(new_message: str):
            content = types.Content(
                role="user", parts=[types.Part.from_text(text=new_message)]
            )
            # print("** User says:", content.model_dump(exclude_none=True))
            async for event in runner.run_async(
                user_id=user_id_1,
                session_id=session_11.id,
                new_message=content,
            ):
                if event.content.parts and event.content.parts[0].text:
                    # print(f"** {event.author}: {event.content.parts[0].text}")
                    return event.content.parts[0].text

        return await run_prompt(input_message)

    def convert_dict_to_str(  # noqa: W0612  # pylint: disable=unused-variable
        response: dict,
    ) -> str:
        return response["output"]

    try:
        yield FunctionInfo.create(single_fn=_response_fn)
    except GeneratorExit:
        logger.exception("Exited early!", exc_info=True)
    finally:
        logger.debug("Cleaning up")
