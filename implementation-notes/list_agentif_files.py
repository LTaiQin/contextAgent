from huggingface_hub import list_repo_files


for filename in list_repo_files("THU-KEG/AgentIF", repo_type="dataset"):
    print(filename)
