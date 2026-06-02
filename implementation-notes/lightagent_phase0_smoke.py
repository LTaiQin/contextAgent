import sys
from types import SimpleNamespace

sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/third_party/LightAgent")

from LightAgent import LightAgent


class StaticCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        message = SimpleNamespace(content="x = 4", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


agent = LightAgent(
    model="mock-model",
    api_key="test-key",
    base_url="http://127.0.0.1:9/v1",
    auto_discover_skills=False,
)
completions = StaticCompletions()
agent.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

history = [
    {"role": "user", "content": "上一题：今天吃什么？"},
    {"role": "assistant", "content": "可以吃米饭。"},
]

result = agent.run(
    "Solve 2x + 3 = 11",
    history=history,
    result_format="object",
    trace=True,
)

params = completions.calls[0]
print("content:", result.content)
print("trace_types:", [event["type"] for event in result.trace])
print("message_count:", len(params["messages"]))
print("roles:", [message["role"] for message in params["messages"]])
print("last_user:", params["messages"][-1]["content"])
print("has_tools:", "tools" in params)
print("trace_request:", result.trace[1]["data"])
