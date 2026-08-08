# ===== START OF FILE core/aws-valid.py =====
# Library for setup and testing AWS API Gateway validation

import os
import json
import boto3
from datetime import datetime, timedelta
import io
import subprocess
from termcolor import colored
from contextlib import redirect_stdout
import pyperclip
    
from core.fileops import *
from core.aws import *

# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
JWT_TEST = os.environ['JWT_03-24']


# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

### AWS LOGGING
LAMBDA_APIS_MAPPING = {
    'deepgram-callback': '[API-GATEWAY-ID]',
    'hash-store': '[API-GATEWAY-ID]',
    'hmac-hash': '[API-GATEWAY-ID]', 
    'qrag-llm': '[API-GATEWAY-ID]',
    'qrag-routing': '[API-GATEWAY-ID]',
    'send-email': '[API-GATEWAY-ID]',
    'vrag-llm': '[API-GATEWAY-ID]'
}
def setup_api_gateway_logging(api_gateway_names=None):
    """
    Set up detailed logging for API Gateway stages.
    If api_gateway_names is None, will configure all APIs in LAMBDA_GLOBALS_MAPPING.
    
    :param api_gateway_names: list of str, optional list of API names to configure
    :return: dict, results of configuration attempts
    """
    api_client = boto3.client('apigateway')
    results = {}
    
    # Use all APIs if none specified
    if api_gateway_names is None:
        api_gateway_names = LAMBDA_APIS_MAPPING.keys()
    
    for api_gateway_name in api_gateway_names:
        try:
            # Get API ID without needing specific method or resource
            apis = api_client.get_rest_apis()['items']
            api = next((api for api in apis if api['name'] == api_gateway_name), None)
            
            if not api:
                results[api_gateway_name] = f"Failed to find API"
                continue
                
            rest_api_id = api['id']
            
            # Get stages for this API
            stages = api_client.get_stages(restApiId=rest_api_id)
            
            for stage in stages['item']:
                stage_name = stage['stageName']
                
                # Update stage settings for detailed logging
                api_client.update_stage(
                    restApiId=rest_api_id,
                    stageName=stage_name,
                    patchOperations=[
                        {
                            'op': 'replace',
                            'path': '/*/*/logging/loglevel',
                            'value': 'INFO'
                        },
                        {
                            'op': 'replace',
                            'path': '/*/*/metrics/enabled',
                            'value': 'true'
                        },
                        # Log full request/response data
                        {
                            'op': 'replace',
                            'path': '/*/*/logging/dataTrace',
                            'value': 'true'
                        },
                        # Include detailed validation errors
                        {
                            'op': 'replace',
                            'path': '/variables/loggingLevel',
                            'value': 'INFO'
                        }
                    ]
                )
                
                results[f"{api_gateway_name} ({stage_name})"] = "Successfully configured logging"
                
        except Exception as e:
            results[api_gateway_name] = f"Error: {str(e)}"
    
    return results
def mrun_setup_api_gateway_logging():
    pass
#if __name__ == "__main__":
    # Configure all APIs
    #results = setup_api_gateway_logging()

    # Configure single API
    cur_lambda_function_name = 'hash-store'
    results = setup_api_gateway_logging([cur_lambda_function_name])
    print("\nAPI Gateway Logging Configuration Results:")
    for api, result in results.items():
        print(f"{api}: {result}")
def fetch_log_streams(client, log_group_name, limit=5, end_time=None):
    """
    Fetch up to 'limit' log streams from 'log_group_name', in descending order
    by last event time, stopping at or before 'end_time' (if given).
    
    :param client: boto3 logs client
    :param log_group_name: str name of the CloudWatch log group
    :param limit: int number of streams to return
    :param end_time: datetime or None. If provided, only include streams whose lastEventTimestamp <= end_time
    :return: list of dict with keys ['logStreamName', 'lastEventTimestamp'] 
    """
    # We'll convert end_time to a timestamp in milliseconds if not None
    end_timestamp_ms = None
    if end_time:
        end_timestamp_ms = int(end_time.timestamp() * 1000)
    
    collected_streams = []
    next_token = None

    while True:
        kwargs = {
            'logGroupName': log_group_name,
            'orderBy': 'LastEventTime',
            'descending': True,
            'limit': 50,  # fetch bigger chunks; we'll filter & trim ourselves
        }
        if next_token:
            kwargs['nextToken'] = next_token
        
        response = client.describe_log_streams(**kwargs)
        streams = response.get('logStreams', [])
        
        for s in streams:
            last_ts = s.get('lastEventTimestamp')
            # If there's no last event, skip it
            if not last_ts:
                continue

            # Changed this condition - now we want streams BEFORE end_time
            if end_timestamp_ms and last_ts < end_timestamp_ms:
                # This stream is older than the requested end time, skip it
                continue

            # Accept it
            collected_streams.append({
                'logStreamName': s['logStreamName'],
                'lastEventTimestamp': s['lastEventTimestamp']
            })
            
            # Stop if we've collected enough
            if len(collected_streams) >= limit:
                break
        
        if len(collected_streams) >= limit:
            break
        
        # Move to the next page if present
        next_token = response.get('nextToken')
        if not next_token:
            break
    
    return collected_streams
def get_stream_events(client, log_group_name, log_stream_name):
    """
    Return *all* events from a given log stream.
    
    :param client: boto3 logs client
    :param log_group_name: str
    :param log_stream_name: str
    :return: list of log event dicts
    """
    all_events = []
    next_token = None

    while True:
        kwargs = {
            'logGroupName': log_group_name,
            'logStreamName': log_stream_name,
            'startFromHead': False,
        }
        if next_token:
            kwargs['nextToken'] = next_token

        response = client.get_log_events(**kwargs)
        events = response.get('events', [])
        all_events.extend(events)

        new_token = response.get('nextForwardToken')
        if new_token == next_token:
            break
        next_token = new_token
    
    return all_events
def parse_access_log_event(message, summary_info):
    """
    Parse a single event message from an API Gateway Access Log group.
    Update summary_info in-place with any found values (method, status, requestId, etc.).
    """
    # Try to parse any JSON message
    if '{' in message:  # Check if message contains JSON
        try:
            # Clean up the message first
            message = message.strip()
            # Fix common JSON formatting issues
            message = message.replace('""', '"')  # Fix double quotes
            message = message.replace('" "', '"')  # Fix spaces between quotes
            
            data = json.loads(message)
            
            # Only update if we find new values
            if 'requestId' in data:
                summary_info['access_request_id'] = data['requestId']
            if 'status' in data:
                summary_info['access_status'] = data['status']
            if 'httpMethod' in data:
                summary_info['access_method'] = data['httpMethod']
                
        except json.JSONDecodeError:
            # Log warning if needed
            pass
def parse_execution_log_event(message, summary_info):
    """
    Parse a single event message from an API Gateway Execution Log group.
    Update summary_info in-place with any found values (requestId, integrationRequestId, method, status, etc.).
    """
    # Example patterns:
    # (requestId) HTTP Method: POST, Resource Path: /some/path
    # (requestId) Method completed with status: 200
    # (requestId) AWS Integration Endpoint RequestId : abc-123
    if 'HTTP Method:' in message:
        # Quick hacky parse; refine as needed
        # e.g. 'HTTP Method: POST, Resource Path: /qrag-routing'
        # We'll look for 'HTTP Method:' and then strip after that
        part = message.split('HTTP Method:')[1].split(',')[0].strip()
        summary_info['execution_method'] = part
    if 'Method completed with status:' in message:
        # e.g. "Method completed with status: 200"
        # We'll parse after the last colon
        status_part = message.split('Method completed with status:')[-1].strip()
        summary_info['execution_status'] = status_part
    if 'AWS Integration Endpoint RequestId' in message:
        # e.g. "AWS Integration Endpoint RequestId : abc-123..."
        integration_part = message.split(':')[-1].strip()
        summary_info['integration_request_id'] = integration_part
    # Also see if there's an original API requestId embedded
    # Usually in the line: (594a3e35-37b8...) Starting execution for request: ...
    # or something that matches the 'access_request_id'
    if 'request:' in message and 'Starting execution for request:' in message:
        # naive parse, refine as you like
        # e.g. "... Starting execution for request: 594a3e35-37b8..."
        start_part = message.split('request:')[-1].strip()
        summary_info['execution_request_id'] = start_part
def parse_lambda_log_event(message, summary_info):
    """
    Parse a single event message from a Lambda log group (/aws/lambda/...).
    Update summary_info in-place with any found values (requestId, etc.).
    """
    # Capture RequestId from START
    if 'START RequestId:' in message:
        try:
            start_part = message.split('START RequestId: ')[1]
            lambda_req_id = start_part.split(' ')[0]
            summary_info['lambda_request_id'] = lambda_req_id
            # Initialize status as STARTED
            summary_info['lambda_status'] = 'STARTED'
        except IndexError:
            pass
            
    # Look for successful completion
    elif 'END RequestId:' in message:
        req_id = message.split('END RequestId: ')[1].split()[0]
        if req_id == summary_info.get('lambda_request_id'):
            summary_info['lambda_status'] = 'SUCCESS'
            
    # Look for REPORT to get execution details
    elif 'REPORT RequestId:' in message:
        try:
            # Extract duration and memory info
            parts = message.split('\t')
            for part in parts:
                if 'Duration:' in part:
                    duration_ms = float(part.split(':')[1].strip().split()[0])
                    if duration_ms > 10000:  # Optional: flag long-running executions
                        summary_info['lambda_status'] = 'SUCCESS-SLOW'
        except:
            pass
            
    # Check for error messages
    elif any(error_indicator in message for error_indicator in [
        'ERROR', 'Error:', 'Exception:', 'Task timed out', 'Process exited'
    ]):
        summary_info['lambda_status'] = 'ERROR'

    # Method should remain N/A for Lambda functions
    summary_info['lambda_method'] = 'N/A'

    # Ensure we have a default status if none was set
    if 'lambda_status' not in summary_info:
        summary_info['lambda_status'] = 'SUCCESS'  # Default to SUCCESS if we see logs but no explicit status
def parse_stream_for_summary(log_group_name, log_stream_name, events):
    """
    Based on the log group type, parse the given events and
    return a dictionary with summary info.
    
    :param log_group_name: str
    :param log_stream_name: str
    :param events: list of CloudWatch log event dicts
    :return: dict of summary info
    """
    summary_info = {
        'log_group': log_group_name,
        'log_stream': log_stream_name,
        'access_request_id': None,
        'access_method': None,
        'access_status': None,
        'execution_request_id': None,
        'execution_method': None,
        'execution_status': None,
        'integration_request_id': None,
        'lambda_request_id': None,
        'lambda_status': None,
    }

    for evt in events:
        msg = evt['message']
        if 'API-Gateway-Access-Logs' in log_group_name:
            parse_access_log_event(msg, summary_info)
        elif 'API-Gateway-Execution-Logs' in log_group_name:
            parse_execution_log_event(msg, summary_info)
        elif '/aws/lambda/' in log_group_name:
            parse_lambda_log_event(msg, summary_info)
        else:
            # some other log group?
            pass
    
    return summary_info
def get_detailed_log_data(client, log_group_name, limit=5, end_time=None):
    """
    High-level function to get recent log streams (up to 'limit') from the specified
    log group, fetch their events, parse summary info for each, and return a list of results.
    
    Each result item is a dict:
      {
        'logStreamName': ...,
        'lastEventTimestamp': ...,
        'summary': {...},
        'events': [ ... ]  # the raw events
      }
    """
    streams = fetch_log_streams(client, log_group_name, limit=limit, end_time=end_time)
    results = []
    
    for s in streams:
        stream_name = s['logStreamName']
        events = get_stream_events(client, log_group_name, stream_name)
        summary = parse_stream_for_summary(log_group_name, stream_name, events)
        
        results.append({
            'logStreamName': stream_name,
            'lastEventTimestamp': s['lastEventTimestamp'],
            'summary': summary,
            'events': events,
        })
    return results
def correlate_api_logs(access_data, execution_data, lambda_data):
    """
    Given the three lists of log data (for Access, Execution, Lambda),
    attempt to correlate them by requestId or other means.
    
    This is just an example stub—actual correlation logic may vary widely
    depending on your needs.
    
    :param access_data: list of dict from get_detailed_log_data() for Access logs
    :param execution_data: list of dict from get_detailed_log_data() for Execution logs
    :param lambda_data: list of dict from get_detailed_log_data() for Lambda logs
    :return: list of correlated items, or a dict keyed by requestId
    """
    # Build index by requestId for each type
    access_by_req = {}
    for item in access_data:
        req_id = item['summary'].get('access_request_id')
        if req_id:
            access_by_req[req_id] = item
    
    execution_by_req = {}
    for item in execution_data:
        req_id = item['summary'].get('execution_request_id')
        if req_id:
            execution_by_req[req_id] = item
    
    lambda_by_req = {}
    for item in lambda_data:
        req_id = item['summary'].get('lambda_request_id')
        if req_id:
            lambda_by_req[req_id] = item
    
    # Attempt to correlate them by matching request IDs
    correlated = []
    for req_id, access_item in access_by_req.items():
        exec_item = execution_by_req.get(req_id)
        # We might also cross-check integrationRequestId, etc.
        # Then see if there's a lambda that used the same requestId
        # (in many cases, the Lambda requestId might match the integrationRequestId, not the same as the access ID)
        # So let's do a naive approach: if the lambda's requestId is found in the execution item, we pair them up.
        
        lambda_item = None
        if exec_item:
            integration_id = exec_item['summary'].get('integration_request_id')
            if integration_id and integration_id in lambda_by_req:
                lambda_item = lambda_by_req[integration_id]
        
        correlated.append({
            'requestId': req_id,
            'access_log': access_item,
            'execution_log': exec_item,
            'lambda_log': lambda_item
        })
    
    return correlated
def get_recent_api_call_logs(lambda_function_name, hours_ago=5, num_streams=5, prompt_overwrite=True):
    """
    Orchestrator function:
      - Determines the log groups (Access, Execution, Lambda) for a given Lambda.
      - Fetches the last 'num_streams' log streams in each group, 
        from 'hours_ago' until now (or less).
      - Correlates them by requestId, etc.
      - Writes a file with everything.
      - Copies latest Lambda stream to clipboard.
    
    :param lambda_function_name: str
    :param hours_ago: int
    :param num_streams: int, how many to fetch in each log group
    :param prompt_overwrite: bool, prompt user if file already exists
    :return: dict with 'correlated' logs and raw lists
    """
    folder_path = 'logs/aws_api_call_logs'
    print(f"Starting log collection for: {lambda_function_name}")
    
    # Prepare the log group names
    api_id = LAMBDA_APIS_MAPPING.get(lambda_function_name, "MISSING_API_ID")
    access_group = f"API-Gateway-Access-Logs_{lambda_function_name}_dev"
    execution_group = f"API-Gateway-Execution-Logs_{api_id}/api"
    lambda_group = f"/aws/lambda/{lambda_function_name}-dev"
    
    # Boto3 client
    client = boto3.client('logs')
    
    # We define the 'end_time' based on hours_ago
    end_time = datetime.now() - timedelta(hours=hours_ago)
    print(f"Using end_time = {end_time.isoformat()} (about {hours_ago} hours ago)")
    
    # Fetch details from each log group
    access_data = get_detailed_log_data(client, access_group, limit=num_streams, end_time=end_time)
    execution_data = get_detailed_log_data(client, execution_group, limit=num_streams, end_time=end_time)
    lambda_data = get_detailed_log_data(client, lambda_group, limit=num_streams, end_time=end_time)
    
    # Correlate
    correlated = correlate_api_logs(access_data, execution_data, lambda_data)
    
    # Build a filename for the logs
    now_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    file_path = f"{folder_path}/{now_str}_API-trace_{lambda_function_name}.md"
    
    if os.path.exists(file_path):
        if prompt_overwrite:
            response = input(f"File already exists: {file_path}\nOverwrite? (y/n): ").strip().lower()
            if response != 'y':
                print("Aborting log file creation.")
                return {
                    'access': access_data,
                    'execution': execution_data,
                    'lambda': lambda_data,
                    'correlated': correlated
                }
        print(f"Overwriting existing file: {file_path}")
    
    # Write to file (markdown)
    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(f"# API Trace Log for {lambda_function_name}\n")
        fh.write(f"Search end time: {end_time.isoformat()} (hours_ago={hours_ago})\n\n")
        
        # Summaries for each log group
        def write_summary_for_group(title, data):
            """Write a summary section for a group of log streams."""
            # Add flag to control ID truncation in summaries
            TRUNCATE_IDS = True
            
            def truncate_id(id_str):
                """Helper to truncate long IDs to first4...last4"""
                if not TRUNCATE_IDS or len(id_str) <= 12:
                    return id_str
                return f"{id_str[:4]}...{id_str[-4:]}"
            
            fh.write(f"## {title}\n")
            if not data:
                fh.write("No streams found.\n\n")
                return
                    
            # Write header with adjusted spacing - increased Status from 11 to 12
            fh.write(f"{'Log Stream':<12} {'Last Event Time':<24} {'Method':<11} {'Status':<13} {'Request ID':<16}\n")
            
            # Use a set to track unique log streams we've already written
            written_streams = set()
            
            # Write each stream's data
            for item in data:
                if not item or 'logStreamName' not in item:
                    continue
                    
                if item['logStreamName'] in written_streams:
                    continue
                written_streams.add(item['logStreamName'])
                
                # For Lambda streams, strip off everything except the final ID
                display_name = item.get('logStreamName', 'unknown')
                if title == "Lambda Log Streams" and '[$LATEST]' in display_name:
                    display_name = display_name.split('[$LATEST]')[1].strip()
                
                # Truncate the log stream ID
                display_name = truncate_id(display_name)
                
                # Safely get timestamp with fallback
                ts = 'N/A'
                if 'lastEventTimestamp' in item:
                    try:
                        ts = datetime.fromtimestamp(item['lastEventTimestamp']/1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                    except:
                        pass
                
                # Safely get summary with fallbacks
                s = item.get('summary', {})
                if not isinstance(s, dict):
                    s = {}
                    
                method = s.get('access_method') or s.get('execution_method') or 'N/A'
                
                # Special handling for Lambda status
                if title == "Lambda Log Streams":
                    status = s.get('lambda_status', 'UNKNOWN')
                else:
                    status = s.get('access_status') or s.get('execution_status') or 'N/A'
                    
                request_id = s.get('access_request_id') or s.get('execution_request_id') or s.get('lambda_request_id') or 'N/A'
                # Truncate the request ID
                request_id = truncate_id(request_id)
                
                # Write data with adjusted spacing to match header
                try:
                    fh.write(f"{display_name:<12} {ts:<24} {method:<11} {status:<13} {request_id:<16}\n")
                except:
                    fh.write(f"{'err':<12} {'N/A':<24} {'N/A':<11} {'N/A':<13} {'N/A':<16}\n")
            
            fh.write("\n")
        
        write_summary_for_group("Access Log Streams", access_data)
        write_summary_for_group("Execution Log Streams", execution_data)
        write_summary_for_group("Lambda Log Streams", lambda_data)
        
        # Correlated summary
        fh.write("## Correlated API Calls\n")
        if not correlated:
            fh.write("No correlations found.\n\n")
        else:
            for c in correlated:
                fh.write(f"- Access RequestId: {c['requestId']}\n")
                if c['access_log']:
                    s = c['access_log']['summary']
                    fh.write(f"  - Access method={s.get('access_method')} status={s.get('access_status')}\n")
                if c['execution_log']:
                    s = c['execution_log']['summary']
                    fh.write(f"  - Execution method={s.get('execution_method')} status={s.get('execution_status')} integrationReqId={s.get('integration_request_id')}\n")
                if c['lambda_log']:
                    s = c['lambda_log']['summary']
                    fh.write(f"  - Lambda requestId={s.get('lambda_request_id')} status={s.get('lambda_status')}\n")
                fh.write("\n")

        # New section: Write detailed events from most recent streams
        fh.write("## Events from most recent log streams\n")
        
        # Get the 2 most recent streams from each group
        latest_lambda_stream_text = None  # Store the text for clipboard
        
        for group_name, data in [
            ("Access Log Streams", access_data[:2]), 
            ("Execution Log Streams", execution_data[:2]), 
            ("Lambda Log Streams", lambda_data[:2])
        ]:
            for stream in data:
                # Get summary info for the header
                ts = datetime.fromtimestamp(stream['lastEventTimestamp']/1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                s = stream['summary']
                method = s.get('access_method') or s.get('execution_method') or 'N/A'
                status = s.get('access_status') or s.get('execution_status') or s.get('lambda_status', 'N/A')
                request_id = s.get('access_request_id') or s.get('execution_request_id') or s.get('lambda_request_id') or 'N/A'
                
                # Write section header for this stream
                header = f"\n### EVENTS FROM {group_name[:-8]}STREAM ID: {stream['logStreamName']}  {ts}  {method}  {status}  {request_id}\n\n"
                fh.write(header)
                
                # Build event text
                event_text = ""
                for event in stream.get('events', []):
                    event_ts = datetime.fromtimestamp(event['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                    event_text += f"{event_ts}:\n{event['message']}\n\n"
                
                fh.write(event_text)
                
                # If this is the first Lambda stream, store its text for clipboard
                if group_name == "Lambda Log Streams" and latest_lambda_stream_text is None:
                    latest_lambda_stream_text = header + event_text
        
        fh.write("\n")
    
    print(f"Correlated logs written to: {file_path}")

    # Copy latest Lambda stream to clipboard if available
    if latest_lambda_stream_text:
        pyperclip.copy(latest_lambda_stream_text)
        print("Latest Lambda stream copied to clipboard")

    return {
        'access': access_data,
        'execution': execution_data,
        'lambda': lambda_data,
        'correlated': correlated
    }
def mrun_get_recent_api_call_logs():
    pass
if __name__ == "__main__":
    #cur_lambda_function_name = 'hash-store'
    cur_lambda_function_name = 'send-email'
    #cur_lambda_function_name = 'qrag-routing'
    #cur_lambda_function_name = 'qrag-llm'
    get_recent_api_call_logs(cur_lambda_function_name, hours_ago=2)


def check_cloudwatch_alarms():
    """
    Check the current status of CloudWatch alarms for API Gateway endpoints.
    Provides a simple summary of which endpoints are being monitored and any active alarms.
    
    :return: None, prints alarm status summary to console
    """
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        # Get all alarms
        paginator = cloudwatch.get_paginator('describe_alarms')
        all_alarms = []
        for page in paginator.paginate():
            all_alarms.extend(page['MetricAlarms'])
            
        # Count monitored APIs and find any in ALARM state
        monitored_apis = set()
        alarms_triggered = []
        
        for alarm in all_alarms:
            # Check if alarm is related to our APIs
            for dim in alarm.get('Dimensions', []):
                if dim['Name'] == 'ApiName' and dim['Value'] in LAMBDA_GLOBALS_MAPPING:
                    monitored_apis.add(dim['Value'])
                    if alarm['StateValue'] == 'ALARM':
                        alarms_triggered.append({
                            'api_gateway_name': dim['Value'],
                            'alarm_name': alarm['AlarmName'],
                            'metric': alarm['MetricName'],
                            'current_value': alarm.get('StateReason', 'No reason provided')
                        })
        
        print("\n=== CloudWatch Alarm Status ===")
        print(f"Checked {len(monitored_apis)} API Gateway endpoints")
        
        if not alarms_triggered:
            print("Status: No alarms currently triggered")
        else:
            print("\nStatus: ALARMS TRIGGERED")
            for alarm in alarms_triggered:
                print(f"  API: {alarm['api_gateway_name']}")
                print(f"  Alarm: {alarm['alarm_name']}")
                print(f"  Metric: {alarm['metric']}")
                print(f"  Reason: {alarm['current_value']}")
                print()
                
    except Exception as e:
        print(f"Error checking CloudWatch alarm status: {e}")
def check_cloudwatch_alarm_status():
    """
    Check the current status of CloudWatch alarms for API Gateway endpoints.
    Provides a simple summary of which endpoints are being monitored and any active alarms.
    
    :return: None, prints alarm status summary to console
    """
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        # Get all alarms
        paginator = cloudwatch.get_paginator('describe_alarms')
        all_alarms = []
        for page in paginator.paginate():
            all_alarms.extend(page['MetricAlarms'])
            
        # Count monitored APIs and find any in ALARM state
        monitored_apis = set()
        alarms_triggered = []
        
        for alarm in all_alarms:
            # Check if alarm is related to our APIs
            for dim in alarm.get('Dimensions', []):
                if dim['Name'] == 'ApiName' and dim['Value'] in LAMBDA_GLOBALS_MAPPING:
                    monitored_apis.add(dim['Value'])
                    if alarm['StateValue'] == 'ALARM':
                        alarms_triggered.append({
                            'api_gateway_name': dim['Value'],
                            'alarm_name': alarm['AlarmName'],
                            'metric': alarm['MetricName'],
                            'current_value': alarm.get('StateReason', 'No reason provided')
                        })
        
        print(colored("\n## ========== CloudWatch Alarm Status ==========", 'blue'))
        print(f"Checked {len(monitored_apis)} API Gateway endpoints")
        
        if not alarms_triggered:
            print(colored("Status: No alarms currently triggered", 'green'))
        else:
            print(colored("\nStatus: ALARMS TRIGGERED", 'red'))
            for alarm in alarms_triggered:
                print(f"  API: {alarm['api_gateway_name']}")
                print(f"  Alarm: {alarm['alarm_name']}")
                print(f"  Metric: {alarm['metric']}")
                print(f"  Reason: {alarm['current_value']}")
                print()
                
    except Exception as e:
        print(f"Error checking CloudWatch alarm status: {e}")
def check_cloudwatch_alarm_configuration():
    """
    Display detailed configuration of CloudWatch alarms for API Gateway endpoints.
    Shows thresholds, actions, and other settings for each alarm.
    
    :return: None, prints alarm configurations to console
    """
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        # Get all alarms
        paginator = cloudwatch.get_paginator('describe_alarms')
        all_alarms = []
        for page in paginator.paginate():
            all_alarms.extend(page['MetricAlarms'])
        
        print(colored("\n## ========== CloudWatch Alarm Configuration ==========", 'blue'))
        
        # Group alarms by API
        for lambda_name, suffix in LAMBDA_GLOBALS_MAPPING.items():
            api_id = LAMBDA_APIS_MAPPING.get(lambda_name)
            
            # Filter alarms for this API
            api_alarms = [
                alarm for alarm in all_alarms
                if any(dim['Name'] == 'ApiName' and dim['Value'] == lambda_name 
                      for dim in alarm.get('Dimensions', []))
            ]
            
            if api_alarms:
                print(f"\n## {lambda_name} (API ID: {api_id})")
                
                for alarm in api_alarms:
                    print(f"\nAlarm: {alarm['AlarmName']}")
                    print(f"  Metric: {alarm['MetricName']}")
                    print(f"  Namespace: {alarm['Namespace']}")
                    print(f"  Comparison: {alarm['ComparisonOperator']} {alarm['Threshold']}")
                    
                    if alarm.get('AlarmActions'):
                        print("  Alarm Actions:")
                        for action in alarm['AlarmActions']:
                            action_type = action.split(':')[2]
                            action_name = action.split(':')[-1]
                            print(f"    - {action_type}: {action_name}")
                    
                    print(f"  Evaluation: {alarm['EvaluationPeriods']} periods of {alarm['Period']} seconds")
                    
    except Exception as e:
        print(colored(f"Error checking CloudWatch alarm configuration: {e}", 'red'))
def check_security_alarm_subscriptions():
    """
    Check the security-alarms SNS topic for subscriptions that might affect resource configurations.
    Analyzes subscriptions to identify any that could trigger automated actions.
    """
    sns = boto3.client('sns')
    lambda_client = boto3.client('lambda')
    
    try:
        print(colored("\n## ========== Security Alarms SNS Topic Analysis ==========", 'blue'))
        
        # First, find the security-alarms topic ARN
        topics = sns.list_topics()['Topics']
        security_topic_arn = next(
            (topic['TopicArn'] for topic in topics 
             if topic['TopicArn'].split(':')[-1] == 'security-alarms'),
            None
        )
        
        if not security_topic_arn:
            print("No 'security-alarms' SNS topic found")
            return
        
        print(f"Topic ARN: {security_topic_arn}")
        
        # Get all subscriptions for this topic
        subscriptions = sns.list_subscriptions_by_topic(
            TopicArn=security_topic_arn
        )['Subscriptions']
        
        if not subscriptions:
            print("No subscriptions found for this topic")
            return
            
        print(f"\nFound {len(subscriptions)} subscription(s):")
        
        # Analyze each subscription
        for sub in subscriptions:
            print(f"\nSubscription Protocol: {sub['Protocol']}")
            print(f"Endpoint: {sub['Endpoint']}")
            
            # Categorize subscription by capability
            try:
                if sub['Protocol'] == 'lambda':
                    lambda_name = sub['Endpoint'].split(':')[-1]
                    lambda_config = lambda_client.get_function_configuration(
                        FunctionName=lambda_name
                    )
                    print("  🔧 Action-Triggering Subscription (Lambda):")
                    print(f"    Name: {lambda_name}")
                    print(f"    Runtime: {lambda_config.get('Runtime', 'unknown')}")
                    print(f"    Description: {lambda_config.get('Description', 'No description')}")
                    print("    NOTE: This Lambda function can execute AWS API calls")
                    
                elif sub['Protocol'] == 'https':
                    print("  🔧 Action-Triggering Subscription (HTTPS):")
                    print("    NOTE: This webhook can trigger external service actions")
                    
                elif sub['Protocol'] in ['email', 'email-json']:
                    print("  📧 Notification-Only Subscription (Email)")
                    
                elif sub['Protocol'] == 'sms':
                    print("  📱 Notification-Only Subscription (SMS)")
                    
                elif sub['Protocol'] == 'sqs':
                    print("  📋 Notification-Only Subscription (SQS Queue)")
                    
                elif sub['Protocol'] == 'application':
                    print("  📱 Notification-Only Subscription (Mobile Push)")
                    
                elif sub['Protocol'] == 'firehose':
                    print("  📊 Data-Streaming Subscription (Kinesis Firehose)")
                    
                elif sub['Protocol'] == 'stepfunctions':
                    print("  🔧 Action-Triggering Subscription (Step Functions):")
                    print("    NOTE: This can orchestrate complex AWS workflows")
                    
                else:
                    print(f"  ❓ Unknown Protocol Type: {sub['Protocol']}")
                    print("    NOTE: Review this subscription type's capabilities")
                
                print(f"  Status: {sub.get('SubscriptionArn', 'pending confirmation')}")
                
            except Exception as e:
                print(colored(f"  Error analyzing subscription: {e}", 'red'))
        
        print("\nSummary:")
        protocol_counts = {}
        for sub in subscriptions:
            protocol_counts[sub['Protocol']] = protocol_counts.get(sub['Protocol'], 0) + 1
            
        for protocol, count in protocol_counts.items():
            print(f"- {protocol}: {count} subscription(s)")
            
        # Identify action-triggering subscriptions
        action_protocols = {'lambda', 'https', 'stepfunctions'}
        action_subs = [sub for sub in subscriptions if sub['Protocol'] in action_protocols]
        if action_subs:
            print("\n⚠️ Warning: Found subscriptions that can trigger automated actions:")
            for sub in action_subs:
                print(f"- {sub['Protocol']}: {sub['Endpoint']}")
                if sub['Protocol'] == 'lambda':
                    print("  (Can execute AWS API calls)")
                elif sub['Protocol'] == 'https':
                    print("  (Can trigger external service actions)")
                elif sub['Protocol'] == 'stepfunctions':
                    print("  (Can orchestrate AWS workflows)")
        else:
            print(colored("\n✓ All subscriptions are notification-only (no automated actions)", 'green'))
            
    except Exception as e:
        print(colored(f"Error checking SNS topic subscriptions: {e}", 'red'))
def check_budget_actions():
    """
    Check AWS Budgets for any budget actions that might trigger on cost or usage thresholds.
    Analyzes both the budgets and their associated actions that could affect services.
    
    :return: None, prints analysis of AWS Budgets and their actions
    """
    budgets = boto3.client('budgets')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    try:
        print(colored("\n## ========== AWS Budget Actions Analysis ==========", 'blue'))
        
        # Get all budgets for the account
        budgets_response = budgets.describe_budgets(
            AccountId=account_id
        )
        
        if not budgets_response.get('Budgets'):
            print("No AWS Budgets found")
            return
            
        print(f"Found {len(budgets_response['Budgets'])} budget(s)")
        
        for budget in budgets_response['Budgets']:
            print(f"\nBudget: {budget['BudgetName']}")
            print(f"Type: {budget['BudgetType']}")
            print(f"Time Unit: {budget['TimeUnit']}")
            
            # Show budget limits
            if 'BudgetLimit' in budget:
                print(f"Limit: {budget['BudgetLimit']['Amount']} {budget['BudgetLimit']['Unit']}")
            
            # Get notifications and actions for this budget
            try:
                notifications = budgets.describe_notifications_for_budget(
                    AccountId=account_id,
                    BudgetName=budget['BudgetName']
                ).get('Notifications', [])
                
                if notifications:
                    print("\n  Associated Notifications and Actions:")
                    for notification in notifications:
                        print(f"\n  📢 Notification:")
                        print(f"    Threshold: {notification.get('Threshold')}%")
                        print(f"    Type: {notification.get('NotificationType')}")
                        print(f"    Comparison: {notification.get('ComparisonOperator')}")
                        
                        # Get subscribers for this notification
                        try:
                            subscribers = budgets.describe_subscribers_for_notification(
                                AccountId=account_id,
                                BudgetName=budget['BudgetName'],
                                Notification=notification
                            ).get('Subscribers', [])
                            
                            if subscribers:
                                print("    Subscribers:")
                                for subscriber in subscribers:
                                    print(f"      - Type: {subscriber.get('SubscriptionType')}")
                                    print(f"        Address: {subscriber.get('Address')}")
                                    
                                    # Check if this is an action-triggering subscription
                                    if subscriber.get('SubscriptionType') == 'SNS':
                                        print("        ⚠️ SNS topic might trigger automated actions")
                                    elif subscriber.get('SubscriptionType') == 'LAMBDA':
                                        print("        ⚠️ Lambda function can execute AWS API calls")
                        except Exception as e:
                            print(f"    Error retrieving subscribers: {e}")
                else:
                    print("  No notifications or actions configured for this budget")
                    
            except Exception as e:
                print(f"  Error retrieving notifications: {e}")
        
        # Summary section
        print("\nSummary:")
        budgets_with_actions = 0
        action_types = set()
        
        for budget in budgets_response['Budgets']:
            notifications = budgets.describe_notifications_for_budget(
                AccountId=account_id,
                BudgetName=budget['BudgetName']
            ).get('Notifications', [])
            
            for notification in notifications:
                subscribers = budgets.describe_subscribers_for_notification(
                    AccountId=account_id,
                    BudgetName=budget['BudgetName'],
                    Notification=notification
                ).get('Subscribers', [])
                
                for subscriber in subscribers:
                    if subscriber.get('SubscriptionType') in ['SNS', 'LAMBDA']:
                        budgets_with_actions += 1
                        action_types.add(subscriber.get('SubscriptionType'))
                        break
                if budgets_with_actions:  # If we found actions, no need to check more notifications
                    break
        
        if budgets_with_actions:
            print(colored(f"⚠️ Found {budgets_with_actions} budget(s) with potential automated actions", 'yellow'))
            print(f"Action types found: {', '.join(action_types)}")
        else:
            print(colored("✓ No automated budget actions configured", 'green'))
            
    except Exception as e:
        print(colored(f"Error checking budget actions: {e}", 'red'))
def check_waf_configuration():
    """
    Check WAF configuration and its association with API Gateways.
    Shows rate limits, rules, and which APIs are protected.
    
    :return: None, prints WAF configuration analysis
    """
    waf = boto3.client('wafv2')
    
    try:
        print(colored("\n## ========== WAF Configuration Analysis ==========", 'blue'))
        
        # Get the Web ACL
        web_acl = waf.get_web_acl(
            Name='First-Web-ACL',
            Scope='REGIONAL',
            Id='a0c4f3b2-e278-4ee7-8561-2bf0728f88d8'
        )
        
        if not web_acl:
            print("No WAF Web ACL found")
            return
            
        acl = web_acl['WebACL']
        print(f"Web ACL: {acl['Name']}")
        print(f"Default Action: {list(acl['DefaultAction'].keys())[0]}")
        
        # Show rules
        print("\nRules:")
        for rule in acl['Rules']:
            print(f"  Rule: {rule['Name']}")
            print(f"  Priority: {rule['Priority']}")
            print(f"  Action: {list(rule['Action'].keys())[0]}")
            
            # Show rate limit details if it's a rate-based rule
            if 'RateBasedStatement' in rule['Statement']:
                rate = rule['Statement']['RateBasedStatement']
                print(f"  Rate Limit: {rate['Limit']} requests per {rate['EvaluationWindowSec']} seconds")
                print(f"  Tracked by: {rate['AggregateKeyType']}")
            print()
        
        # Get associated resources
        resources = waf.list_resources_for_web_acl(
            WebACLArn=acl['ARN'],
            ResourceType='API_GATEWAY'
        )['ResourceArns']
        
        print("\nProtected API Gateways:")
        if resources:
            for resource in resources:
                # Extract API ID from ARN
                api_id = resource.split('/')[-1]
                # Find matching Lambda function name
                lambda_name = next(
                    (name for name, id in LAMBDA_APIS_MAPPING.items() if id == api_id),
                    'Unknown'
                )
                print(f"  • {lambda_name} (API ID: {api_id})")
        else:
            print("  No API Gateways associated with this WAF")
            
        # Show metrics configuration
        print("\nMonitoring:")
        print(f"CloudWatch Metrics: {'Enabled' if acl['VisibilityConfig']['CloudWatchMetricsEnabled'] else 'Disabled'}")
        print(f"Request Sampling: {'Enabled' if acl['VisibilityConfig']['SampledRequestsEnabled'] else 'Disabled'}")
        print(f"Metric Name: {acl['VisibilityConfig']['MetricName']}")
        
    except Exception as e:
        print(colored(f"Error checking WAF configuration: {e}", 'red'))
def aws_checks_with_clipboard():
    """
    Run all AWS checks and print colored output to terminal.
    Also copies plain text version to clipboard.
    """
    # First capture the output in a buffer
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        now_datetime = get_current_datetime_humanfriendly()
        print(f"# AWS CHECKS - run {now_datetime}")
        check_waf_configuration()
        check_budget_actions()
        check_security_alarm_subscriptions()
        check_cloudwatch_alarm_configuration()
        check_cloudwatch_alarm_status()
    
    # Get the plain text for clipboard
    plain_text = buffer.getvalue()
    
    # Run the checks again to display colored output
    now_datetime = get_current_datetime_humanfriendly()
    print(f"# AWS CHECKS - run {now_datetime}")
    check_waf_configuration()
    check_budget_actions()
    check_security_alarm_subscriptions()
    check_cloudwatch_alarm_configuration()
    check_cloudwatch_alarm_status()
    
    # Copy plain text to clipboard
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(plain_text.encode('utf-8'))
        print("\n✓ Output copied to clipboard")
    except Exception as e:
        print(f"\n⚠️ Failed to copy to clipboard: {e}")
def mrun_aws_checks():
    pass
#if __name__ == "__main__":
    aws_checks_with_clipboard()


# aws apigateway delete-model --rest-api-id [API-GATEWAY-ID] --model-name hmachashModel

# ===== END OF FILE core/aws-valid.py =====
