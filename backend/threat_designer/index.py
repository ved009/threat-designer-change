import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3
from agent import agent
from model import initialize_models
from state import AgentState, AssetsList, FlowsList
from utils import fetch_results, parse_s3_image_to_base64, update_job_state

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
S3_BUCKET = os.environ.get("ARCHITECTURE_BUCKET")
AGENT_TABLE = os.environ.get("AGENT_STATE_TABLE")


def _initialize_state(event: Dict[str, Any], job_id: str) -> AgentState:
    """
    Initialize the agent state for threat modeling analysis.

    Args:
        event (Dict[str, Any]): The Lambda event containing job configuration
        job_id (str): Unique identifier for the analysis job

    Returns:
        AgentState: Initialized state object for the analysis
    """
    state = AgentState()
    state["job_id"] = job_id
    state["iteration"] = event["iteration"]

    if event.get("replay", False):
        return _handle_replay_state(state, job_id)
    return _handle_new_state(state, event)


def _handle_replay_state(state: AgentState, job_id: str) -> AgentState:
    """
    Handle replay of previous analysis by loading saved state.

    Args:
        state (AgentState): Current agent state
        job_id (str): ID of job to replay

    Returns:
        AgentState: State loaded from previous analysis
    """
    results = fetch_results(job_id, AGENT_TABLE)
    item = results["item"]

    state.update(
        {
            "replay": True,
            "assets": AssetsList(**item["assets"]),
            "system_architecture": FlowsList(**item["system_architecture"]),
            "retry": 1,
            "image_data": parse_s3_image_to_base64(S3_BUCKET, item["s3_location"]),
            "description": item["description"],
            "assumptions": item["assumptions"],
            "title": item["title"],
            "owner": item["owner"],
            "s3_location": item["s3_location"],
        }
    )
    return state


def _handle_new_state(state: AgentState, event: Dict[str, Any]) -> AgentState:
    """
    Initialize state for new analysis.

    Args:
        state (AgentState): Current agent state
        event (Dict[str, Any]): Lambda event with job configuration

    Returns:
        AgentState: Initialized state for new analysis
    """
    state.update(
        {
            "image_data": parse_s3_image_to_base64(S3_BUCKET, event["s3_location"]),
            "description": event.get("description", " "),
            "assumptions": event.get("assumptions", []),
            "s3_location": event["s3_location"],
            "owner": event.get("owner", None),
            "title": event.get("title", None),
        }
    )
    return state


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for threat modeling analysis.

    Args:
        event (Dict[str, Any]): Lambda event containing job configuration
        context: Lambda context object (unused but required by AWS Lambda)

    Returns:
        Dict: Response containing status code and execution result
    """
    reasoning = int(event.get("reasoning", "0"))
    models = initialize_models(reasoning)
    thinking = reasoning != 0
    config = {
        "configurable": {
            "model_main": models["main_model"],
            "model_struct": models["struct_model"],
            "start_time": datetime.now(),
            "reasoning": thinking,
        }
    }

    try:
        job_id = event["id"]
        state = _initialize_state(event, job_id)
        agent.invoke(state, config=config)

        return {
            "statusCode": 200,
            "body": json.dumps("Threat modeling completed successfully"),
        }
    except KeyError as e:
        logger.error(f"Missing required field in event: {e}")
        update_job_state(job_id, "FAILED")
        return {
            "statusCode": 400,
            "body": json.dumps(f"Missing required field: {e}"),
        }
    except Exception as e:
        logger.error(f"Unexpected error during threat modeling: {e}")
        update_job_state(job_id, "FAILED")
        return {
            "statusCode": 500,
            "body": json.dumps("Error processing threat modeling"),
        }
