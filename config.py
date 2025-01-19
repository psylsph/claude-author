"""Configuration for the book generation system"""
from typing import Dict

#lm studio
def get_config(local_url: str = "http://192.168.1.5:1234/v1") -> Dict:
# ollama
#def get_config(local_url: str = "http://localhost:11434/v1") -> Dict:
    """Get the configuration for the agents"""
    
    # Basic config for local LLM
    config_list = [{
        'model': 'mn-violet-lotus-12b',
        'base_url': local_url,
        #'api_type': 'ollama', # disable for lm studio
        'api_key': 'not-needed',
        'price': [0,0],
    }]

    # Common configuration for all agents
    agent_config = {
        "seed": 42,
        "temperature": 0.6,
        "top_p": 0.95,
        "frequency_penalty": 0.3,
        "presence_penalty": 0.2,
        "config_list": config_list,
        "timeout": 600,
        "cache_seed": None
    }
    
    return agent_config