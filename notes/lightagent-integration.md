# LightAgent Integration Notes

Date checked: 2026-05-31.

## Download Status

LightAgent has been cloned locally:

```text
agent-context-isolation/third_party/LightAgent
```

Current commit:

```text
396ea2d
```

The shell initially failed to resolve `github.com` because the environment used `socks5://127.0.0.1:7890`, which performs DNS resolution locally. Switching the clone command to `socks5h://127.0.0.1:7890` fixed it by resolving DNS through the proxy.

Command used:

```bash
ALL_PROXY=socks5h://127.0.0.1:7890 \
HTTPS_PROXY=socks5h://127.0.0.1:7890 \
HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/wanxingai/LightAgent.git agent-context-isolation/third_party/LightAgent
```

## Relevant Local Files

- `third_party/LightAgent/LightAgent/core.py`
- `third_party/LightAgent/LightAgent/skills.py`
- `third_party/LightAgent/LightAgent/skill_tools.py`
- `third_party/LightAgent/example/06.chat_with_history.py`

## Why This Baseline Is Useful

`LightAgent.run()` accepts an explicit `history` argument. The current flow builds model messages as:

```text
system prompt + history + current user query
```

It also injects available skill metadata into the system prompt when `use_skills=True`.

This gives a clean experimental insertion point:

```text
raw chat session
  -> TaskContextManager
  -> selected task-scoped history
  -> LightAgent.run(query, history=scoped_history)
```

## First Integration Target

Do not modify LightAgent internals first. Add a wrapper around it:

```python
class IsolatedLightAgent:
    def __init__(self, agent, task_context_manager):
        self.agent = agent
        self.task_context_manager = task_context_manager

    def run(self, query, session_id, user_id="default_user", **kwargs):
        scoped_history = self.task_context_manager.select_history(
            session_id=session_id,
            user_id=user_id,
            query=query,
        )
        return self.agent.run(query, history=scoped_history, user_id=user_id, **kwargs)
```

This keeps the baseline intact and makes ablation easier:

- full session history
- recent-N turns
- task-scoped history
- task-scoped history plus task-local skill candidates

