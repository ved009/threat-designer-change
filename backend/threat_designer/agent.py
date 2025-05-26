"""
Threat Designer Agent module that handles architecture analysis and threat modeling workflows.
This module defines the state graph and node functions for the threat modeling process.
"""

import logging
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages.human import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.types import Command
from prompts import (summary_prompt, asset_prompt, flow_prompt, gap_prompt,
                     threats_improve_prompt, threats_prompt)
from state import (SummaryState, AgentState, AssetsList, ContinueThreatModeling, FlowsList,
                   ThreatsList)
from typing_extensions import TypedDict
from utils import (create_dynamodb_item, handle_asset_error, update_job_state,
                   update_trail)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


AGENT_TABLE = os.environ.get("AGENT_STATE_TABLE")
MODEL = os.environ.get("MODEL")
MAX_RETRY = 15


class ConfigSchema(TypedDict):
    """Configuration schema for the workflow.

    Attributes:
        model_main: Main model configuration
        model_gap: Gap analysis model configuration
        model_struct: Structured output model configuration
        start_time: Workflow start time
        reasoning: Flag to enable reasoning
    """

    model_main: Any
    model_gap: Any
    model_struct: Any
    start_time: datetime
    reasoning: bool


human_structure = HumanMessage(
    content=[
        {"type": "text", "text": "Convert the <response> into a structured output"},
    ]
)


def image_to_base64(state: AgentState, config: RunnableConfig) -> Dict[str, str]:
    """Convert image data from state to base64 format and generates a short summary.

    Args:
        state: Current agent state containing image data
        config: Configuration for the runnable

    Returns:
        Dictionary containing base64 encoded image data and optionally summary
    """
    
    if not state.get("summary", None):
        configurable = config.get("configurable", {})
        model_summary = configurable.get("model_summary")
        tools = [SummaryState]

        content = [
            {"type": "text", "text": "Generate a short headline summary of max 40 words this architecture using the diagram and description if available"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{state["image_data"]}"},
            },
            {"type": "text", "text": f"<description>{state.get("description", "")}</description>"}
        ]
        human_message = HumanMessage(content=content)
        summary_message = [summary_prompt(), human_message]

        # Configure model based on reasoning requirement
        model_with_tools = model_summary.bind_tools(tools)

        # Process response
        response = model_with_tools.invoke(summary_message)
        response = SummaryState(**response.tool_calls[0]["args"])
        return {
            "image_data": state["image_data"],
            "summary": response.summary
            }
    
    return {"image_data": state["image_data"]}


def list_to_string(str_list):
    """Convert a list of strings to a single string.

    Args:
        str_list: List of strings to join

    Returns:
        Single string with elements joined by newlines, or space if list is empty
    """
    if not str_list:
        return " "
    return "\n".join(str_list)


def prepare_message_content(image_data, description, assumptions):
    """Helper function to prepare message content.

    Args:
        image_data: Base64 encoded image data
        description: Description text
        assumptions: Assumptions text

    Returns:
        List of content items for message
    """
    return [
        {"type": "text", "text": "Analyze the following architecture:"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
        },
        {"type": "text", "text": f"<description>{description}</description>"},
        {"type": "text", "text": f"<assumptions>{assumptions}</assumptions>"},
    ]


def define_assets(state: AgentState, config: RunnableConfig):
    """Define assets from the architecture image and description.

    Args:
        state: Current agent state
        config: Configuration for the runnable

    Returns:
        Dictionary containing processed assets
    """
    # Extract configuration values with defaults
    configurable = config.get("configurable", {})
    model_structured = configurable.get("model_struct")
    model = configurable.get("model_main")
    reasoning = configurable.get("reasoning", False)

    # Update job state
    update_job_state(state["job_id"], "ASSETS")

    # Prepare data for prompt
    assumptions = list_to_string(state.get("assumptions", []))
    tools = [AssetsList]

    # Construct message with image and text components
    content = prepare_message_content(
        state["image_data"], state.get("description", ""), assumptions
    )
    human_message = HumanMessage(content=content)
    struct_message = [asset_prompt(), human_message]

    # Configure model based on reasoning requirement
    model_with_tools = model.bind_tools(
        tools, tool_choice="any" if not reasoning else None
    )

    # Process response
    response = model_with_tools.invoke(struct_message)

    # Update trail if reasoning is enabled
    if reasoning and response.content and len(response.content) > 0:
        reasoning_text = response.content[0].get("reasoning_content", {}).get("text")
        if reasoning_text:
            update_trail(job_id=state["job_id"], assets=reasoning_text)

    # Process assets with error handling
    @handle_asset_error(
        model_structured, AssetsList, thinking=configurable.get("reasoning", True)
    )
    def process_assets(response):
        return AssetsList(**response.tool_calls[0]["args"])

    processed_assets = process_assets(response)
    return {"assets": processed_assets}


def define_flows(state: AgentState, config: RunnableConfig):
    """Define data flows between assets in the architecture.

    Args:
        state: Current agent state
        config: Configuration for the runnable

    Returns:
        Dictionary containing processed system architecture flows
    """
    # Extract configuration values with defaults
    configurable = config.get("configurable", {})
    model_structured = configurable.get("model_struct")
    model = configurable.get("model_main")
    reasoning = configurable.get("reasoning", False)

    # Log and update job state
    update_job_state(state["job_id"], "FLOW")

    # Prepare data for prompt
    assumptions = list_to_string(state.get("assumptions", []))
    tools = [FlowsList]

    # Construct message with image and text components
    content = [
        {"type": "text", "text": "This is the architecture and related information:"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{state['image_data']}"},
        },
        {
            "type": "text",
            "text": f"<description>{state.get('description', '')}</description>",
        },
        {"type": "text", "text": f"<assumptions>{assumptions}</assumptions>"},
    ]
    human_message = HumanMessage(content=content)
    struct_message = [flow_prompt(state["assets"]), human_message]

    # Configure model based on reasoning requirement
    model_with_tools = model.bind_tools(
        tools, tool_choice="any" if not reasoning else None
    )

    # Process response
    response = model_with_tools.invoke(struct_message)

    # Update trail if reasoning is enabled
    if reasoning and response.content and len(response.content) > 0:
        reasoning_text = response.content[0].get("reasoning_content", {}).get("text")
        if reasoning_text:
            update_trail(job_id=state["job_id"], flows=reasoning_text)

    # Process flows with error handling
    @handle_asset_error(
        model_structured, FlowsList, thinking=configurable.get("reasoning", True)
    )
    def process_flows(response):
        return FlowsList(**response.tool_calls[0]["args"])

    processed_flows = process_flows(response)
    return {"system_architecture": processed_flows}


def create_gap_message(state, assumptions):
    """Create message content for gap analysis.

    Args:
        state: Current agent state
        assumptions: Formatted assumptions text

    Returns:
        HumanMessage with appropriate content
    """
    content = [
        {"type": "text", "text": "There are gaps in the <threats> ??\n"},
        {
            "type": "text",
            "text": f"<threats>{state.get('threat_list', '')}</threats>\n",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{state['image_data']}"},
        },
        {
            "type": "text",
            "text": f"<solution_description>{state.get('description', '')}</solution_description>",
        },
        {"type": "text", "text": f"<assumptions>{assumptions}</assumptions>"},
    ]
    return HumanMessage(content=content)


def gap_analysis(state: AgentState, config: RunnableConfig):
    """Analyze gaps in the threat model.

    Args:
        state: Current agent state
        config: Configuration for the runnable

    Returns:
        Command to either continue threat modeling or finalize
    """
    assumptions = list_to_string(state.get("assumptions", []))
    model = config["configurable"].get("model_main")
    model_structured = config["configurable"].get("model_struct")
    reasoning = config["configurable"].get("reasoning", False)
    tools = [ContinueThreatModeling]
    flush = 0 if int(state.get("retry", 1)) == 1 else 1

    human_message = create_gap_message(state, assumptions)
    messages = [
        gap_prompt(state.get("gap", []), state["assets"], state["system_architecture"]),
        human_message,
    ]

    model_with_tools = model.bind_tools(
        tools, tool_choice="any" if not reasoning else None
    )

    try:
        response = model_with_tools.invoke(messages)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error("Error in defining threats: %s\n%s", e, stack_trace)
        raise

    if reasoning:
        reasoning_text = (
            response.content[0].get("reasoning_content", {}).get("text", None)
        )
        update_trail(job_id=state["job_id"], gaps=reasoning_text, flush=flush)

    @handle_asset_error(
        model_structured,
        ContinueThreatModeling,
        thinking=config["configurable"].get("reasoning", True),
    )
    def process_gaps(response):
        return ContinueThreatModeling(**response.tool_calls[0]["args"])

    try:
        response = process_gaps(response)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error("Error in defining threats: %s\n%s", e, stack_trace)
        raise

    if response.stop:
        return Command(goto="finalize")

    return Command(goto="threats", update={"gap": [response.gap]})


def check_continuation(retry_count, iteration, start_time, current_time):
    """Check if threat modeling should continue or finalize.

    Args:
        retry_count: Current retry count
        iteration: Current iteration
        start_time: Start time of the process
        current_time: Current time

    Returns:
        Boolean indicating if process should finalize
    """
    max_retries_reached = retry_count > MAX_RETRY
    iteration_limit_reached = (retry_count > iteration) and (iteration != 0)
    time_limit_reached = (current_time - start_time).total_seconds() >= 12 * 60

    return max_retries_reached or iteration_limit_reached or time_limit_reached


def create_threat_message(state, assumptions):
    """Create message content for threat definition.

    Args:
        state: Current agent state
        assumptions: Formatted assumptions text

    Returns:
        HumanMessage with appropriate content
    """
    content = [
        {
            "type": "text",
            "text": "Define threats and mitigations for the following solution:",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{state['image_data']}"},
        },
        {
            "type": "text",
            "text": f"<solution_description>{state.get('description', '')}</solution_description>",
        },
        {"type": "text", "text": f"<assumptions>{assumptions}</assumptions>"},
    ]
    return HumanMessage(content=content)


def define_threats(state: AgentState, config: RunnableConfig):
    """Define threats and mitigations for the architecture.

    Args:
        state: Current agent state
        config: Configuration for the runnable

    Returns:
        Command to continue threat analysis or finalize
    """
    model_structured = config["configurable"].get("model_struct")
    model = config["configurable"].get("model_main")
    reasoning = config["configurable"].get("reasoning", False)
    retry_count = int(state.get("retry", 1))
    iteration = int(state.get("iteration", 0))
    assumptions = list_to_string(state.get("assumptions", []))
    tools = [ThreatsList]
    gap = state.get("gap", [])

    start_time = config["configurable"].get("start_time")
    current_time = datetime.now()

    if check_continuation(retry_count, iteration, start_time, current_time):
        return Command(goto="finalize")

    model_with_tools = model.bind_tools(
        tools, tool_choice="any" if not reasoning else None
    )

    human_message = create_threat_message(state, assumptions)

    if state.get("retry", 1) > 1:
        update_job_state(state["job_id"], "THREAT_RETRY", retry_count)
        system_prompt = threats_improve_prompt(
            gap, state.get("threat_list"), state["assets"], state["system_architecture"]
        )
    else:
        update_job_state(state["job_id"], "THREAT", retry_count)
        system_prompt = threats_prompt(state["assets"], state["system_architecture"])

    struct_message = [system_prompt, human_message]

    try:
        response = model_with_tools.invoke(struct_message)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error("Error in defining threats: %s\n%s", e, stack_trace)
        raise

    if reasoning:
        flush = 0 if int(state.get("retry", 1)) == 1 else 1
        reasoning_text = (
            response.content[0].get("reasoning_content", {}).get("text", None)
        )
        update_trail(job_id=state["job_id"], threats=reasoning_text, flush=flush)

    @handle_asset_error(
        model_structured,
        ThreatsList,
        thinking=config["configurable"].get("reasoning", True),
    )
    def process_threats(response):
        return ThreatsList(**response.tool_calls[0]["args"])

    try:
        response = process_threats(response)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error("Error in processing threats: %s\n%s", e, stack_trace)
        raise

    retry_count += 1
    if iteration == 0:
        return Command(
            goto="gap_analysis", update={"threat_list": response, "retry": retry_count}
        )

    return Command(
        goto="threats", update={"threat_list": response, "retry": retry_count}
    )


def finalize(state: AgentState):
    """Finalize the threat modeling process.

    Args:
        state: Current agent state

    Returns:
        Command to end workflow
    """
    try:
        update_job_state(state["job_id"], "FINALIZE")
        create_dynamodb_item(state, AGENT_TABLE)
        time.sleep(3)
        update_job_state(state["job_id"], "COMPLETE")
        return Command(goto=END)
    except Exception as e:
        update_job_state(state["job_id"], "FAILED")
        raise e


def route_replay(state: AgentState):
    """Route workflow based on replay flag.

    Args:
        state: Current agent state

    Returns:
        String indicating whether to replay or do full analysis
    """
    if state.get("replay", False):
        update_trail(job_id=state["job_id"], threats=[], gaps=[], flush=0)
        try:
            return "replay"
        except Exception as e:
            print(e)
            raise e

    return "full"


workflow = StateGraph(AgentState, ConfigSchema)

workflow.add_node("asset", define_assets)
workflow.add_node("image_to_base64", image_to_base64)
workflow.add_node("flows", define_flows)
workflow.add_node("threats", define_threats)
workflow.add_node("gap_analysis", gap_analysis)
workflow.add_node("finalize", finalize)


workflow.set_entry_point("image_to_base64")
workflow.add_conditional_edges(
    "image_to_base64", route_replay, {"replay": "threats", "full": "asset"}
)
workflow.add_edge("asset", "flows")
workflow.add_edge("flows", "threats")

agent = workflow.compile()
