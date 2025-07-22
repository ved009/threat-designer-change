"""
Threat Designer Model Module.

This module provides model initialization and configuration functions for the Threat Designer application.
It handles the creation of LangChain-compatible Gemini model clients with various configurations.
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, TypedDict

import google.generativeai as genai
from constants import (DEFAULT_BUDGET,
                       ENV_GOOGLE_API_KEY, ENV_MAIN_MODEL,
                       ENV_MODEL_STRUCT, ENV_MODEL_SUMMARY,
                       ENV_REASONING_MODELS,
                       MODEL_TEMPERATURE_DEFAULT, MODEL_TEMPERATURE_REASONING,
                       TOKEN_BUDGETS)
from langchain_google_genai import ChatGoogleGenerativeAI
from monitoring import logger, operation_context, with_error_context


class ThreatModelingError(Exception):
    """Custom exception for threat modeling operations."""

    pass


class ModelConfig(TypedDict):
    """Type definition for model configuration."""

    id: str
    max_tokens: int


@dataclass
class ModelConfigurations:
    """Container for all model configurations."""

    main_model: ModelConfig
    struct_model: ModelConfig
    summary_model: ModelConfig
    reasoning_models: list[str]


@with_error_context("load model configurations")
def _load_model_configs() -> ModelConfigurations:
    """
    Load and validate model configurations from environment variables.

    Returns:
        ModelConfigurations: Validated model configurations.

    Raises:
        ThreatModelingError: If configuration loading fails.
    """
    try:
        logger.debug("Loading model configurations from environment")

        main_model = json.loads(os.environ.get(ENV_MAIN_MODEL, "{}"))
        struct_model = json.loads(os.environ.get(ENV_MODEL_STRUCT, "{}"))
        summary_model = json.loads(os.environ.get(ENV_MODEL_SUMMARY, "{}"))
        reasoning_models = json.loads(os.environ.get(ENV_REASONING_MODELS, "[]"))

        # Validate required fields
        for model_name, model_config in [
            (ENV_MAIN_MODEL, main_model),
            (ENV_MODEL_STRUCT, struct_model),
            (ENV_MODEL_SUMMARY, summary_model),
        ]:
            if not model_config.get("id") or not model_config.get("max_tokens"):
                raise ValueError(
                    f"Missing required fields 'id' or 'max_tokens' in {model_name}"
                )

        logger.info(
            "Model configurations loaded successfully",
            main_model_id=main_model.get("id"),
            struct_model_id=struct_model.get("id"),
            summary_model_id=summary_model.get("id"),
            reasoning_models_count=len(reasoning_models),
        )

        return ModelConfigurations(
            main_model=main_model,
            struct_model=struct_model,
            summary_model=summary_model,
            reasoning_models=reasoning_models,
        )

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in environment variables", error=str(e))
        raise
    except Exception as e:
        logger.error("Error loading model configurations", error=str(e))
        raise




def _get_token_budget(reasoning: int) -> int:
    """
    Get token budget based on reasoning level.

    Args:
        reasoning: Reasoning level (1, 2, or 3).

    Returns:
        int: Token budget amount (4000, 8000, or 16000). Default is 4000 if invalid level.
    """
    budget = TOKEN_BUDGETS.get(reasoning, DEFAULT_BUDGET)
    logger.debug("Token budget determined", reasoning_level=reasoning, budget=budget)
    return budget


def _build_standard_model_config(model_config: ModelConfig) -> dict:
    """
    Build standard model configuration dictionary.

    Args:
        model_config: Model configuration with id and max_tokens.

    Returns:
        dict: Standard model configuration.
    """
    config = {
        "model": model_config["id"],
        "max_output_tokens": model_config["max_tokens"],
        "temperature": MODEL_TEMPERATURE_DEFAULT,
    }

    logger.debug(
        "Standard model config built",
        model_id=model_config["id"],
        max_tokens=model_config["max_tokens"],
    )

    return config


def _build_main_model_config(
    model_config: ModelConfig,
    reasoning_models: list,
    reasoning: int,
) -> dict:
    """
    Build configuration dictionary for main model with optional reasoning.

    Args:
        model_config: Model configuration with id and max_tokens.
        reasoning_models: List of model IDs that support reasoning.
        reasoning: Reasoning level (0 disables reasoning).

    Returns:
        dict: Main model configuration with reasoning if applicable.
    """
    config = _build_standard_model_config(model_config)

    # Add reasoning configuration if enabled and supported
    reasoning_enabled = reasoning != 0 and model_config["id"] in reasoning_models

    if reasoning_enabled:
        budget = _get_token_budget(reasoning)
        config["temperature"] = MODEL_TEMPERATURE_REASONING

        logger.info(
            "Reasoning enabled for main model",
            model_id=model_config["id"],
            reasoning_level=reasoning,
            token_budget=budget,
        )
    else:
        if reasoning != 0:
            logger.warning(
                "Reasoning requested but not supported by model",
                model_id=model_config["id"],
                reasoning_level=reasoning,
                supported_models=reasoning_models,
            )

    return config


def initialize_models(
    reasoning: int = 0,
    api_key: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, ChatGoogleGenerativeAI]:
    """
    Initialize Gemini model clients with proper error handling.

    This function creates multiple Gemini model clients with different configurations:
    - Main model: Primary model with optional reasoning capabilities
    - Struct model: Model optimized for structured outputs
    - Summary model: Model optimized for summarization tasks

    Args:
        reasoning: Reasoning level (0-3). 0 disables reasoning, 1-3 enables with different token budgets.
        api_key: Optional Google API key for Gemini. Falls back to env var.
        job_id: Optional job ID for operation tracking.

    Returns:
        Dict[str, ChatGoogleGenerativeAI]: Dictionary containing:
            - 'main_model': Primary ChatGoogleGenerativeAI instance
            - 'struct_model': ChatGoogleGenerativeAI instance for structured outputs
            - 'summary_model': ChatGoogleGenerativeAI instance for summarization

    Raises:
        ThreatModelingError: If model initialization fails.
    """
    job_id = job_id or "model-init"

    with operation_context("initialize_models", job_id):
        try:
            logger.info("Starting model initialization", reasoning_level=reasoning)

            # Load and validate configurations
            configs = _load_model_configs()

            api_key = api_key or os.environ.get(ENV_GOOGLE_API_KEY)
            if not api_key:
                raise ThreatModelingError("GOOGLE_API_KEY not provided")

            genai.configure(api_key=api_key)

            # Build model configurations
            logger.debug("Building model configurations")

            main_config = _build_main_model_config(
                configs.main_model, configs.reasoning_models, reasoning
            )

            struct_config = _build_standard_model_config(configs.struct_model)
            summary_config = _build_standard_model_config(configs.summary_model)

            # Initialize models
            logger.debug("Initializing ChatGoogleGenerativeAI instances")

            models = {
                "main_model": ChatGoogleGenerativeAI(**main_config),
                "struct_model": ChatGoogleGenerativeAI(**struct_config),
                "summary_model": ChatGoogleGenerativeAI(**summary_config),
            }

            logger.info(
                "Models initialized successfully",
                model_count=len(models),
                main_model_id=configs.main_model["id"],
                struct_model_id=configs.struct_model["id"],
                summary_model_id=configs.summary_model["id"],
                reasoning_enabled=reasoning != 0
                and configs.main_model["id"] in configs.reasoning_models,
            )

            return models

        except Exception as e:
            logger.error(
                "Model initialization failed",
                reasoning_level=reasoning,
                error=str(e),
                job_id=job_id,
            )
            raise
