# LLM trong NeMo Agent Toolkit (NAT)

Tài liệu này tổng hợp cách cấu hình LLM, format input/output, và cách agent sử dụng LLM để tools hoạt động được.

---

## 1. Cấu hình LLM trong YAML

### 1.1. Khai báo trong `llms`

LLM **phải được định nghĩa trước** các functions dùng chúng.

```yaml
llms:
  nim_llm:
    _type: nim
    model_name: meta/llama-3.1-70b-instruct
    max_tokens: 4096
    api_key: $NVIDIA_API_KEY

  reasoning_llm:
    _type: nim
    model_name: deepseek-ai/deepseek-r1
    max_tokens: 8192
    temperature: 0.2
    api_key: $DEEPSEEK_R1_API_KEY
```

- **`_type`**: Loại provider (`nim`, `openai`, `aws_bedrock`, `azure_openai`, `nat_test_llm`).
- **`model_name`**: Tên model trên API.
- **`max_tokens`**: Giới hạn token sinh ra.
- **`temperature`**, **`top_p`**: Tuỳ provider/model (có thể bị gated).
- **`api_key`**: Thường dùng biến môi trường `$VAR_NAME`.

### 1.2. Functions tham chiếu LLM qua `llm_name`

```yaml
functions:
  my_agent:
    _type: react_agent
    llm_name: nim_llm          # <-- tham chiếu tên đã khai báo trong llms
    tool_names: [file_reader, save_file_code]
    system_prompt: |
      You are a helpful assistant.
```

**Quy tắc:** Giá trị `llm_name` phải trùng với một key trong `llms`.

---

## 2. Kiến trúc: Provider vs Client

NAT tách hai lớp:

| Lớp | Vai trò | Ví dụ |
|-----|--------|--------|
| **LLM Provider** | Config (model_name, api_key, temperature, ...) | `NIMModelConfig`, `OpenAIModelConfig` |
| **LLM Client** | Implementation gọi API, theo từng framework | LangChain: `ChatNVIDIA`, `ChatOpenAI` |

- Một **provider** (ví dụ `nim`) có thể có nhiều **client** (LangChain, LlamaIndex, ...).
- Agent trong NAT hiện dùng **LangChain/LangGraph**, nên khi gọi `get_llm(..., wrapper_type=LLMFrameworkEnum.LANGCHAIN)` thì NAT trả về đối tượng LangChain (ví dụ `ChatNVIDIA`).

---

## 3. Input/Output format của LLM (khi dùng qua LangChain)

### 3.1. LLM nhận gì (input)

Qua LangChain, LLM nhận **messages** (chat format):

- **Kiểu input** có thể là:
  - `str` → được chuyển thành `[SystemMessage(optional), HumanMessage(content=str)]`
  - `BaseMessage` (một message)
  - `Sequence[BaseMessage]` (nhiều message)
  - `PromptValue` (đã chứa messages)

- **Các loại message thường dùng:**
  - `SystemMessage(content="...")` – system prompt
  - `HumanMessage(content="...")` – user / human turn
  - `AIMessage(content="...")` – assistant turn
  - `ToolMessage(content="...", tool_call_id=...)` – kết quả tool (trong tool-calling flow)

Ví dụ đơn giản (như `chat_completion`):

```python
# Chat completion: gửi string
response = await llm.ainvoke(prompt)
# Trong LangChain client, prompt (str) thường được wrap thành HumanMessage
```

Ví dụ ReAct agent (phức tạp hơn):

- Prompt là `ChatPromptTemplate` với các placeholder: `question`, `chat_history`, `agent_scratchpad`.
- Mỗi lần gọi LLM, agent truyền dict vào template, template sinh ra **danh sách messages** (system + user + optional scratchpad).
- LLM nhận đúng danh sách messages đó.

### 3.2. LLM trả về gì (output)

- **Kiểu trả về:** `AIMessage` (LangChain).
- **Nội dung:** `response.content` là **string** (text do model sinh ra).
- ReAct agent **parse string này** để lấy:
  - `Thought`, `Action`, `Action Input`, hoặc
  - `Final Answer`.

Tóm lại: **Input = messages (system/human/ai/tool), Output = AIMessage với content là string.**

---

## 4. Tools và LLM: tools hoạt động như thế nào với agent

### 4.1. Tools không gửi trực tiếp "input/output của LLM"

- **LLM** chỉ nhận **text (messages)** và sinh **text (AIMessage.content)**.
- **Tools** là functions độc lập: input/output của tool là **Pydantic model** (và/hoặc string) do NAT và LangChain wrapper quy định, **không** phải "input/output format của LLM".

Luồng thực tế:

1. User/Orchestrator gửi **user message** (ví dụ câu hỏi).
2. Agent đưa message + system prompt + (có thể) scratchpad vào **LLM**.
3. LLM trả về **text** (Thought/Action/Action Input hoặc Final Answer).
4. Agent **parse** text đó để biết:
   - gọi tool nào,
   - **action input** là gì (thường là string/JSON string).
5. Agent **map** action input vào **input schema của tool** (Pydantic), gọi `tool.ainvoke(tool_input)`.
6. Tool trả về **string** (hoặc object được serialize thành string).
7. Agent đưa kết quả này vào **Observation** (HumanMessage hoặc tương đương), đưa lại vào **LLM** (vòng lặp ReAct).

Vậy: **"Input/output của LLM"** là **text (messages → text)**. **"Input/output của tool"** là **schema của function (Pydantic)**. Agent là cầu nối: từ **output text của LLM** → parse thành **tool name + tool input** → gọi tool → đưa **output của tool** (dạng text) lại thành **input (messages)** cho LLM.

### 4.2. Tool được mô tả trong prompt (ReAct)

Trong ReAct, tools được **mô tả bằng text** trong system prompt:

- `{tools}`: danh sách tên tool + mô tả + (tuỳ config) **input schema** (field names, types).
- `{tool_names}`: danh sách tên tool, ví dụ `file_reader, save_file_code`.

LLM **chỉ đọc text** này để quyết định:
- Gọi tool nào (`Action: file_reader`),
- Ghi gì vào `Action Input:` (thường là JSON string hoặc text phù hợp schema).

Sau đó agent parse `Action` và `Action Input` từ output text của LLM và gọi `tool.ainvoke(...)` với input đã được convert sang đúng `input_schema` của tool.

### 4.3. Tool input từ LLM: string → Pydantic

- LLM sinh ra **string** (ví dụ `{"file_path": "output/doc/pm_output.txt"}`).
- Agent (hoặc wrapper) sẽ:
  - parse string (JSON),
  - validate/convert sang **Pydantic model** (chính là `input_schema` của tool),
  - gọi `tool.ainvoke(pydantic_input)`.

Nếu LLM sinh JSON lỗi format, có thể dẫn đến parse/validation lỗi; một số tool (như `save_file_code` cũ) cố gắng "sửa" nhiều dạng input (nhiều strategy parse) thay vì ép LLM output đúng schema.

---

## 5. Tóm tắt: Cấu hình để agent (và tools) hoạt động

1. **Khai báo LLM** trong `llms` với `_type` và `model_name` (và api_key, max_tokens, ...).
2. **Khai báo tools** trong `functions` (mỗi tool có `_type` tương ứng, ví dụ `file_reader`, `save_file_code`, hoặc `nat_mas_agents_v2/list_files`, ...).
3. **Khai báo agent** (ví dụ `react_agent`) với:
   - `llm_name`: trỏ tới một key trong `llms`,
   - `tool_names`: list tên function (tools) đã khai báo trong `functions`,
   - (tuỳ chọn) `system_prompt`, `additional_instructions`.
4. **Workflow** gọi agent (ví dụ entry point là agent, hoặc workflow chứa bước gọi agent).

Khi chạy:

- Builder load config → **get_llm(llm_name, LANGCHAIN)** → trả về LLM client (LangChain).
- **get_tools(tool_names, LANGCHAIN)** → trả về list tool (LangChain `BaseTool`), mỗi tool có `name`, `description`, `input_schema` (từ Pydantic).
- Agent build prompt (system + user + placeholders), mỗi vòng: **LLM.ainvoke(messages)** → text → parse → **tool.ainvoke(parsed_input)** → observation → đưa lại vào messages → lặp đến khi Final Answer.

---

## 6. Gợi ý cho MAS V2 (tool-grounded, state-based)

- **Không** phụ thuộc LLM "tưởng tượng": mọi thông tin quan trọng nên nằm trong **TaskState** hoặc **output của tools** (file, test results, logs).
- **Planner/Worker/Executor/Critic** có thể là **functions** nhận `TaskState` (Pydantic), gọi LLM với **prompt được build từ state** (ví dụ: "Objective: … Current subtask: … Last critique: …") và **tools** (list_files, read_file, run_shell, …), rồi **cập nhật state** từ kết quả thực tế (tool output, execution logs).
- **Input/output của LLM** vẫn là **messages → text**. Input/output **của từng step** (Planner, Worker, …) nên là **TaskState** (structured), để tránh truyền thông tin qua free-text giữa các agent.

Như vậy, tools hoạt động dựa trên **output text của LLM** (được parse thành tool name + tool input) và **input của tools** là **Pydantic model**; LLM không "biết" trực tiếp Pydantic, mà chỉ sinh text mà agent sẽ map vào schema của tool.
