"""
Threat Designer Model Module.

This module provides model initialization and configuration functions for the Threat Designer application.
It handles the creation of LangChain-compatible Bedrock model clients with various configurations.
"""

import json
import logging
import os
from typing import Dict

import boto3
from botocore.config import Config
from langchain_aws.chat_models.bedrock import ChatBedrockConverse

logger = logging.getLogger()
logger.setLevel(logging.INFO)


config = Config(read_timeout=1000)
region = os.environ.get("REGION", "us-west-2")
# Create the main bedrock runtime client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime", region_name=region, config=config
)


def _get_budget(reasoning: str) -> int:
    """
    Get token budget based on reasoning level.

    Args:
        reasoning (str): Reasoning level (1, 2, or 3)

    Returns:
        int: Token budget amount (4000, 8000, or 16000). Default is 4000 if invalid reasoning level.
    """
    budget = {1: 4000, 2: 8000, 3: 16000}
    return budget.get(reasoning, 4000)


def initialize_models(
    reasoning: int = 0,
) -> Dict[str, ChatBedrockConverse]:
    """
    This function creates multiple Bedrock model clients.
    It sets up a main model with optional reasoning capabilities, a structured model and a summary model.

    Args:
        reasoning (int): Level to enable/disable reasoning capabilities for main models.
                        0 disables reasoning, 1-3 enables with different token budgets.

    Returns:
        Dict[str, ChatBedrockConverse]: Dictionary containing:
            - 'main_model': ChatBedrockConverse instance
            - 'struct_model': ChatBedrockConverse instance for structured outputs
    """

    # Parse model configurations from environment
    model_main = json.loads(os.environ.get("MAIN_MODEL", "{}"))
    model_struct = json.loads(os.environ.get("MODEL_STRUCT", "{}"))
    model_summary = json.loads(os.environ.get("MODEL_SUMMARY", "{}"))
    reasoning_models = json.loads(os.environ.get("REASONING_MODELS", "[]"))

    # Base configuration for main model with default client
    main_model_config = {
        "client": bedrock_runtime,
        "region_name": region,
        "max_tokens": model_main.get("max_tokens"),
        "model_id": model_main.get("id"),
        "stop": ["Human:", "User:", "Assistant:", "\nAI:"],
    }

    # Add reasoning parameters if enabled and model supports it
    if int(reasoning) != 0 and model_main.get("id") in reasoning_models:
        reasoning_config = {
            "thinking": {"type": "enabled", "budget_tokens": _get_budget(reasoning)}
        }

        main_model_config["additional_model_request_fields"] = reasoning_config
        main_model_config["temperature"] = 1
    else:
        main_model_config["temperature"] = 0

    # Structured model configuration
    struct_model_config = {
        "client": bedrock_runtime,
        "region_name": region,
        "max_tokens": model_struct.get("max_tokens"),
        "model_id": model_struct.get("id"),
        "temperature": 0,
        "stop": ["Human:", "User:", "Assistant:", "\nAI:"],
    }

    summary_model_config = {
        "client": bedrock_runtime,
        "region_name": region,
        "max_tokens": model_summary.get("max_tokens"),
        "model_id": model_summary.get("id"),
        "temperature": 0,
        "stop": ["Human:", "User:", "Assistant:", "\nAI:"],
    }

    return {
        "main_model": ChatBedrockConverse(**main_model_config),
        "struct_model": ChatBedrockConverse(**struct_model_config),
        "summary_model": ChatBedrockConverse(**summary_model_config),
    }
