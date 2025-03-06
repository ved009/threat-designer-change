from langchain_aws.chat_models.bedrock import ChatBedrockConverse
import boto3
from botocore.config import Config
import os
import json
from typing import Tuple
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _get_budget(reasoning: str):
    budget = {
        1: 4000,
        2: 8000,
        3: 16000
    }
    return budget.get(reasoning, 4000)

def initialize_models(reasoning: int = 0) -> Tuple[ChatBedrockConverse, ChatBedrockConverse, ChatBedrockConverse]:
    """
    Initialize three ChatBedrockConverse models with different configurations.
    
    Args:
        reasoning (bool): Flag to enable/disable reasoning capabilities for main model
        
    Returns:
        Tuple[ChatBedrockConverse, ChatBedrockConverse, ChatBedrockConverse]: 
            (main_model, model_gap, model_structured)
    """
    config = Config(read_timeout=1000)
    REGION = os.environ.get('REGION', 'us-west-2')
    
    # Parse model configurations from environment
    MODEL_MAIN = json.loads(os.environ.get("MAIN_MODEL", "{}"))
    MODEL_STRUCT = json.loads(os.environ.get("MODEL_STRUCT", "{}"))
    REASONING_MODELS = json.loads(os.environ.get("REASONING_MODELS", "[]"))

    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION,
        config=config
    )

    # Base configuration for main model
    main_model_config = {
        "client": bedrock_runtime,
        "region_name": REGION,
        "max_tokens": MODEL_MAIN.get("max_tokens"),
        "model_id": MODEL_MAIN.get("id"),
        "stop": ["Human:", "User:", "Assistant:", "\nAI:"],
    }

    # Add reasoning parameters if enabled and model supports it
    if int(reasoning) != 0 and MODEL_MAIN.get("id") in REASONING_MODELS:
        main_model_config["additional_model_request_fields"] = {
            "thinking": {
                "type": "enabled",
                "budget_tokens": _get_budget(reasoning)
            }
        }
        main_model_config["temperature"] = 1
    else:
        main_model_config["temperature"] = 0
    # Structured model configuration
    struct_model_config = {
        "client": bedrock_runtime,
        "region_name": REGION,
        "max_tokens": MODEL_STRUCT.get("max_tokens"),
        "model_id": MODEL_STRUCT.get("id"),
        "temperature": 0,
        "stop": ["Human:", "User:", "Assistant:", "\nAI:"],
    }

    return (
        ChatBedrockConverse(**main_model_config),
        ChatBedrockConverse(**struct_model_config)
    )
