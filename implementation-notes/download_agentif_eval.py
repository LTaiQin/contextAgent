from pathlib import Path

from huggingface_hub import hf_hub_download


target_dir = Path("/22liushoulong/agent/agent-context-isolation/data/agentif")
target_dir.mkdir(parents=True, exist_ok=True)

path = hf_hub_download(
    repo_id="THU-KEG/AgentIF",
    repo_type="dataset",
    filename="eval.json",
    local_dir=target_dir,
)

print(path)
