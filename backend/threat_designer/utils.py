import boto3
import os
from botocore.exceptions import ClientError
import base64
import datetime
import decimal
from aws_lambda_powertools import Logger
from datetime import datetime, timezone
from prompts import structure_prompt
from langchain_core.messages.human import HumanMessage


logger = Logger()
JOB_STATUS = os.environ.get("JOB_STATUS_TABLE")
TRAIL_TABLE = os.environ.get("AGENT_TRAIL_TABLE")


def convert_decimals(obj):
    """Recursively converts Decimal to float or int in a dictionary."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, decimal.Decimal):
        return (
            int(obj) if obj % 1 == 0 else float(obj)
        )  # Convert to int if it's a whole number
    else:
        return obj


def update_job_state(job_id, state, retry=None):
    try:
        # Create a DynamoDB resource
        dynamodb = boto3.resource("dynamodb")

        # Get the table
        table = dynamodb.Table(JOB_STATUS)

        # Get current UTC timestamp
        current_utc = datetime.now(timezone.utc).isoformat()

        # Build update expression and attributes
        update_expr = "SET #state = :state, #timestamp = :timestamp"
        expr_names = {"#state": "state", "#timestamp": "updated_at"}
        expr_values = {":state": state, ":timestamp": current_utc}

        # Add retry if provided
        if retry is not None:
            update_expr += ", #retry = :retry"
            expr_names["#retry"] = "retry"
            expr_values[":retry"] = retry

        # Update the item
        response = table.update_item(
            Key={"id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="UPDATED_NEW",
        )

        logger.info(f"Successfully updated job {job_id} state to {state}")
        return response

    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None

def update_trail(job_id, assets=None, flows=None, threats=None, gaps=None, flush=0):
    try:
        # Create a DynamoDB resource
        dynamodb = boto3.resource("dynamodb")

        # Get the table
        table = dynamodb.Table(TRAIL_TABLE)
        
        # Initialize update expression and attribute dictionaries
        update_expr = "SET "
        expr_names = {}
        expr_values = {}
        
        # Track if this is the first attribute to avoid leading comma
        is_first = True

        # Handle string fields (assets, flows)
        if assets is not None:
            update_expr += "#assets = :assets"
            expr_names["#assets"] = "assets"
            expr_values[":assets"] = assets
            is_first = False

        if flows is not None:
            if not is_first:
                update_expr += ", "
            update_expr += "#flows = :flows"
            expr_names["#flows"] = "flows"
            expr_values[":flows"] = flows
            is_first = False

        # Handle list fields (threats, gaps)
        if threats is not None:
            threats_list = threats if isinstance(threats, list) else [threats]
            
            if not is_first:
                update_expr += ", "
                
            if flush == 0:
                # Replace the entire list
                update_expr += "#threats = :threats"
                expr_names["#threats"] = "threats"
                expr_values[":threats"] = threats_list
            else:
                # Get current item to check if threats exists
                response = table.get_item(Key={"id": job_id}, ProjectionExpression="threats")
                if "threats" in response.get('Item', {}):
                    # Append to existing list
                    update_expr += "#threats = list_append(#threats, :threats)"
                else:
                    # Create new list
                    update_expr += "#threats = :threats"
                expr_names["#threats"] = "threats"
                expr_values[":threats"] = threats_list
            is_first = False

        if gaps is not None:
            gaps_list = gaps if isinstance(gaps, list) else [gaps]
            
            if not is_first:
                update_expr += ", "
                
            if flush == 0:
                # Replace the entire list
                update_expr += "#gap = :gap"
                expr_names["#gap"] = "gap"
                expr_values[":gap"] = gaps_list
            else:
                # Get current item to check if gaps exists
                response = table.get_item(Key={"id": job_id}, ProjectionExpression="gap")
                if "gap" in response.get('Item', {}):
                    # Append to existing list
                    update_expr += "#gap = list_append(#gap, :gap)"
                else:
                    # Create new list
                    update_expr += "#gap = :gap"
                expr_names["#gap"] = "gap"
                expr_values[":gap"] = gaps_list
            is_first = False

        # Only proceed if there's something to update
        if is_first:
            logger.info(f"No fields to update for job {job_id}")
            return None

        # Update the item
        response = table.update_item(
            Key={"id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="UPDATED_NEW",
        )

        logger.info(f"Successfully updated job {job_id}")
        return response

    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None


def parse_s3_image_to_base64(bucket_name, object_key):
    try:
        # Create an S3 client
        s3_client = boto3.client("s3")

        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)

        # Read the content of the object
        image_content = response["Body"].read()

        # Convert the image content to base64
        base64_encoded = base64.b64encode(image_content).decode("utf-8")

        return base64_encoded

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.error(
                f"The object {object_key} does not exist in bucket {bucket_name}."
            )
        elif e.response["Error"]["Code"] == "NoSuchBucket":
            logger.error(f"The bucket {bucket_name} does not exist.")
        else:
            logger.error(f"An error occurred: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None


def create_dynamodb_item(agent_state, table_name):
    # Initialize DynamoDB client
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Get current UTC timestamp
    current_utc = datetime.now(timezone.utc).isoformat()

    # Convert Pydantic model to dict, handling nested Pydantic objects and existing dicts
    item = {
        "job_id": agent_state["job_id"],
        "assets": agent_state["assets"].dict(),
        "system_architecture": agent_state["system_architecture"].dict(),
        "threat_list": agent_state["threat_list"].dict(),
        "description": agent_state.get("description", None),
        "assumptions": agent_state.get("assumptions", None),
        "s3_location": agent_state["s3_location"],
        "title": agent_state.get("title", None),
        "owner": agent_state.get("owner", None),
        "retry": agent_state.get("retry", None),
        "timestamp": current_utc,
    }

    try:
        # Create a new item in DynamoDB
        response = table.put_item(Item=item)
        logger.info("Item created successfully:", response)
    except Exception as e:
        logger.error("Error creating item:", e.response["Error"]["Message"])
        raise


def fetch_results(job_id, table_name):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        response = table.get_item(Key={"job_id": job_id})

        if "Item" in response:
            return {
                "job_id": job_id,
                "state": "Found",
                "item": convert_decimals(
                    response["Item"]
                ),  # Convert Decimals before returning
            }
        else:
            return {"job_id": job_id, "state": "Not Found", "item": None}

    except Exception as e:
        raise

human_structure = HumanMessage(
        content=[
            {"type": "text", "text": "Convert the <response> into a structured output"},
        ]
    )

def _retry(model, response, struct):
    reasoning = response.content[0].get('reasoning_content', {}).get('text', None)
    struct_message = [structure_prompt(reasoning), human_structure]
    model_with_tools = model.with_structured_output(struct)
    return model_with_tools.invoke(struct_message)

def handle_asset_error(model, struct, thinking=True):
    def decorator(func):
        def wrapper(response, *args, **kwargs):
            try:
                return func(response, *args, **kwargs)
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                if thinking:
                    # When thinking=True, call the _retry function
                    return _retry(model, response, struct)
                else:
                    # When thinking=False, let the original error raise
                    raise e
        return wrapper
    return decorator

