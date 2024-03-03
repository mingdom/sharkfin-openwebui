#!/usr/bin/env python
import os

# Define a list of environment variable names
env_vars = [
    ("FMP_API_KEY", "https://site.financialmodelingprep.com/developer/docs/dashboard"),
    ("OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
    (
        "LANGCHAIN_API_KEY",
        "https://smith.langchain.com/o/1e3cb2ec-8975-44b1-af99-f5279ac65743/settings",
    ),
    (
        "SERPER_API_KEY",
        "https://python.langchain.com/docs/integrations/providers/google_serper",
    ),
    # (
    #     "GOOGLE_CSE_ID",
    #     "https://python.langchain.com/docs/integrations/tools/google_search",
    # ),
    # (
    #     "GOOGLE_API_KEY",
    #     "https://python.langchain.com/docs/integrations/tools/google_search",
    # ),
]

# Iterate through the list and check if each variable is set
for var, site in env_vars:
    if os.getenv(var):
        print(f"{var} is set: {os.getenv(var)}")
    else:
        print(f"{var} is not set! See {site}")
