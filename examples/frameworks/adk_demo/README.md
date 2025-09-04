<!--
SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Google Agent Development Kit (ADK) Example

A minimal example using Agent Development Kit showcasing a simple weather time agent that can call tools (a function tool and an MCP tool).

## Installation and Setup

If you have not already done so, follow the instructions in the [Install Guide](../../../docs/source/quick-start/installing.md#install-from-source) to create the development environment and install NeMo Agent Toolkit.

### Install this Workflow:

From the root directory of the NAT library, run the following commands:

```bash
uv pip install -e '.[adk]' --prerelease=allow
uv pip install -e examples/frameworks/adk_demo
```

### Set Up API Keys

Since Google ADK uses LiteLLM, you can use whichever model that is supported by LiteLLM. Please set the appropriate environment variables for the model you want to use.

### Run the Workflow

#### Set up the MCP server
This example also demonstrates how NAT can interact with MCP servers on behalf of ADK.

First run the MCP server with this command.

```bash
python examples/frameworks/adk_demo/src/nat_adk_demo/time_mcp_tool.py
```

Then query the AIQ instance with this command

```bash
nat run --config_file examples/frameworks/adk_demo/configs/config.yml --input "What is the weather and time in New York today?"
```

**Expected Output**

```console
The weather in New York today is sunny with a high of 75°F and a low of 60°F.
```
