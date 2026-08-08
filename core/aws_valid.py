# ===== START OF FILE core/aws-valid.py =====
# Library for setup and testing AWS API Gateway validation

import os
import sys
import re
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
from time import sleep
import requests
import io
import subprocess
from termcolor import colored
from contextlib import redirect_stdout
import tempfile
import zipfile
import urllib.request
import glob
    
from core.fileops import *
from core.aws import *

# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
JWT_TEST = os.environ['JWT_2026-03-21']

### MRUN GUARD
def _guard_multiple_mrun_blocks():
    """
    Checks for multiple uncommented 'if __name__ == "__main__":' blocks.
    Warns and prompts user if more than one is found. Only runs when file is executed directly.
    """
    if __name__ != "__main__":
        return
    with open(__file__, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    active_blocks = []
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        # Only match 'if __name__ == "__main__":' (not != checks)
        if stripped.startswith('if __name__') and '==' in stripped and '__main__' in stripped and stripped.rstrip().endswith(':'):
            active_blocks.append((i, line.rstrip()))
    if len(active_blocks) > 1:
        print(f"\n⚠️  WARNING: {len(active_blocks)} uncommented 'if __name__' blocks found!")
        for line_num, line_text in active_blocks:
            print(f"  Line {line_num}: {line_text}")
        response = input("\nPress N to abort, any other key to continue: ")
        if response in ('n', 'N'):
            import sys
            sys.exit(0)
_guard_multiple_mrun_blocks()

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

### AWS API GATEWAY VALIDATION
''' Categories of test requests:
clean_requests: Well-formed inputs that meet all schema and functional requirements.
schema_invalid_requests: Inputs that violate schema constraints but would still be acceptable by the function's logic if not for API Gateway validation (e.g., too long, but not empty).
function_invalid_requests: Inputs that break the function's own basic logic checks (e.g., missing or empty required fields).
'''
''' API GATEWAY IDs
deepgram-callback    [API-GATEWAY-ID]
hash-store           [API-GATEWAY-ID]
hmac-hash            [API-GATEWAY-ID]
qrag-llm             [API-GATEWAY-ID]
qrag-routing         [API-GATEWAY-ID]
send-email           [API-GATEWAY-ID]
testapp              [API-GATEWAY-ID]
vrag-llm             [API-GATEWAY-ID]
'''
MAX_USER_NAME_LENGTH = 64  # sync with webflow-fof-site-body.js var maxUserNameLength
MAX_QUESTION_LENGTH = 500  # sync with webflow-fof-site-body.js var maxQuestionLength
MAX_FILE_NAME_LENGTH = 255  # sync with webflow-fof-site-body.js var maxFileNameLength
MAX_EMAIL_ADDRESS_LENGTH = 254  # sync with webflow-fof-site-body.js var maxEmailLength
MAX_PARAMETER_LENGTH = 50  # use as a default for internal parameters and variable names
MIN_NUM_CHUNKS = 2  # sync with min num-chunks-options in webflow-qrag-input-component-embed.html
MAX_NUM_CHUNKS = 50  # sync with max num-chunks-options in webflow-qrag-input-component-embed.html, think pinecone_retriever can go higher
LLM_MODEL_OPTIONS = ["gpt-5.4", "gpt-4o", "gpt-4o-mini", "o3-mini", "deepseek-reasoner", "o3", "o1"]
REMOVE_FIELD = "__REMOVE_FIELD__"  # # Define a sentinel value for field removal

# SKIPPED IMPLEMENTING THIS SCHEMA FOR API GATEWAY VALIDATION 12-16-24 RT
API_ENDPOINT_DEEPGRAM_CALLBACK = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription"
SCHEMA_DEEPGRAM_CALLBACK = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "DeepgramCallbackRequest",
    "type": "object",
    "properties": {
        "metadata": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string"
                }
            }
        }
    },
    "additionalProperties": True
}
TEST_REQUESTS_DEEPGRAM_CALLBACK = {
    "clean_requests": [
        {   
            "description": "Valid request with request_id",
            "request": {
                "metadata": {
                    "request_id": "test-request-123"
                }
            }
        }
    ],
    
    "schema_invalid_requests": [
        {   
            "description": "Invalid metadata type",
            "request": {
                "metadata": "not_an_object"
            }
        }
    ],
    
    "function_invalid_requests": [
        {   
            "description": "Missing metadata",
            "request": {
                "some_other_field": "value"
            }
        }
    ]
}

API_ENDPOINT_HMAC_HASH_PROD = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/generate-hash"
API_ENDPOINT_HMAC_HASH = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/generate-hash"
SCHEMA_HMAC_HASH = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "HMACHashRequest", 
    "type": "object",
    "required": ["input_text"],
    "properties": {
        "input_text": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_EMAIL_ADDRESS_LENGTH  # max lenth of userInputEmail
        }
    },
    "additionalProperties": False
}
TEST_REQUESTS_HMAC_HASH = {
    "clean_requests": [
        {   
            "description": "Basic valid email",
            "request": {
                "input_text": "test@example.com"
            }
        },
        {   
            "description": "Complex but valid email",
            "request": {
                "input_text": "user.name+tag@domain.co.uk"
            }
        }
    ],

    "schema_invalid_requests": [
        {   
            "description": "Additional field added",
            "request": {
                "other_field": "some value"
            }
        },
        {   
            "description": "Too long (255 chars, exceeds maxLength)",
            "request": {
                "input_text": "a" * 255
            }
        }
    ],

    "function_invalid_requests": [
        {   
            "description": "Wrong type",
            "request": {
                "input_text": 12345
            }
        },
        {   
            "description": "Null value",
            "request": {
                "input_text": None
            }
        },
        {   
            "description": "Empty string (fails minLength)",
            "request": {
                "input_text": ""
            }
        }
    ]
}

API_ENDPOINT_HASH_STORE = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/hash-store"
API_ENDPOINT_HASH_STORE_PROD = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/hash-store"
SCHEMA_HASH_STORE = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "HashStoreRequest",
    "type": "object",
    "required": [
        "key",
        "userNiceName",
        "userIPAddress",
        "eventType"
    ],
    "properties": {
        "key": {
            "type": "string",
            "pattern": "^pii_user_hash_log_[0-9]{4}-[0-9]{2}-[0-9]{2}\\.csv$"
        },
        "s3_path": {
            "type": "string"
        },
        "userNiceName": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_USER_NAME_LENGTH
        },
        "userIPAddress": {
            "type": "string",
            "minLength": 7,
            "maxLength": 45  # Accommodates both IPv4 and IPv6
        },
        "inputUserEmail": {
            "type": "string",
            "maxLength": MAX_EMAIL_ADDRESS_LENGTH
        },
        "emailListSignupChecked": {
            "type": ["boolean", "null"]
        },
        "eventType": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_PARAMETER_LENGTH
        },
        "privacyConsent": {
            "type": "string",  # allow to be any string and do not enforce date format at this point
            "minLength": 1,
            "maxLength": MAX_PARAMETER_LENGTH
        }
    },
    "additionalProperties": False
}
TEST_REQUESTS_HASH_STORE = {
    "clean_requests": [
        {   
            "description": "Full valid request",
            "request": {
                "key": "pii_user_hash_log_2024-12-17.csv",
                "s3_path": "",
                "userNiceName": "TEST aws-valid", 
                "userIPAddress": "192.168.1.1",
                "inputUserEmail": "test@example.com",
                "emailListSignupChecked": True,
                "eventType": "test",
                "privacyConsent": "2024-12-17"
            }
        },
        {   
            "description": "No email address or signup checkbox",
            "request": {
                "key": "pii_user_hash_log_2024-12-17.csv",
                "s3_path": "",
                "userNiceName": "TEST aws-valid", 
                "userIPAddress": "192.168.1.1",
                "inputUserEmail": "",
                "emailListSignupChecked": None,  # should be set to 'null' in the request
                "eventType": "test",
                "privacyConsent": "2024-12-17"
            }
        },
        {   
            "description": "All fields with maximum complexity",
            "request": {
                "userNiceName": "A" * MAX_USER_NAME_LENGTH,
                "userIPAddress": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                "inputUserEmail": "very.long.email+tag@really.long.domain.co.uk"
            }
        }
    ],
    
    "schema_invalid_requests": [
        {   
            "description": "Additional field added",
            "request": {
                "other_field": "some value"
            }
        },
        {   
            "description": "userNiceName too long",
            "request": {
                "userNiceName": "A" * (MAX_USER_NAME_LENGTH + 1)
            }
        },
        {   
            "description": "Invalid IP format",
            "request": {
                "userIPAddress": "bad.ip"
            }
        },
        {   
            "description": "Wrong type",
            "request": {
                "eventType": ["not", "a", "string"]
            }
        }
    ],
    
    "function_invalid_requests": [
        {   
            "description": "Missing required field",
            "request": {
                "userNiceName": REMOVE_FIELD
            }
        },
        {   
            "description": "Invalid key",
            "request": {
                "key": "invalid_filename.csv"
            }
        }
    ]
}

API_ENDPOINT_QRAG_ROUTING = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing"
API_ENDPOINT_QRAG_ROUTING_PROD = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/qrag-routing"
SCHEMA_QRAG_ROUTING = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "QRAGRoutingRequest", 
    "description": "Schema for validating QRAG routing requests",
    "type": "object",
    "required": [
        "user_question",
        "vector_index_name",
        "route_dict_name"
    ],
    "properties": {
        "user_question": {
            "type": "string",
            "description": "The user's question to be answered",
            "minLength": 1,
            "maxLength": MAX_QUESTION_LENGTH
        },
        "vector_index_name": {
            "type": "string", 
            "description": "Name of the vector index to search against"
        },
        "route_dict_name": {
            "type": "string",
            "description": "Name of the routing dictionary to use, must start with ROUTES_DICT_",
            "pattern": "^ROUTES_DICT_.*$"
        },
        "routes_bounds": {
            "type": "array",
            "description": "Array of two numbers between 0 and 1 defining the routing bounds",
            "items": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "minItems": 2,
            "maxItems": 2
        },
        "user_id": {
            "type": "string",
            "description": "Unique identifier for the user making the request",
            "minLength": 1,
            "maxLength": MAX_USER_NAME_LENGTH
        },
        "qrag_version": {
            "type": "string",
            "description": "Version of the QRAG system being used"
        },
        "num_chunks": {
            "type": "integer",
            "description": "Number of text chunks to retrieve from the vector store",
            "minimum": MIN_NUM_CHUNKS,
            "maximum": MAX_NUM_CHUNKS
        },
        "start_date": {
            "type": "string",
            "pattern": "^(?:\\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\\d|3[01]))$"
        },
        "end_date": {
            "type": "string",
            "pattern": "^(?:\\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\\d|3[01]))$"
        },
        "hashedUserNiceName": {
            "type": "string",
            "description": "Hashed version of user's display name",
            "maxLength": 128
        },
        "hashedUserIPAddress": {
            "type": "string",
            "description": "Hashed version of user's IP address",
            "maxLength": 128
        },
        "hashedInputUserEmail": {
            "type": "string",
            "description": "Hashed version of user's email address",
            "maxLength": 128
        }
    },
    "additionalProperties": False
}
TEST_REQUESTS_QRAG_ROUTING = {
    "clean_requests": [
        {   
            "description": "Complete template request with all fields including hashed user data",
            "request": {
                "user_question": "What is the meaning of the good life?",
                "vector_index_name": "deutsch-transcript-qrag-83f-20250202",
                "num_chunks": 2,
                "route_dict_name": "ROUTES_DICT_DEUTSCH_M1",
                "routes_bounds": [0.3, 0.9],
                "user_id": "test_user",
                "qrag_version": "2.0",
                "hashedUserNiceName": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                "hashedUserIPAddress": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1",
                "hashedInputUserEmail": "c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0v1w2"
            }
        },
        {   
            "description": "Add start_date and end_date",
            "request": {
                "start_date": "1995-01-01",
                "end_date": "2024-12-23"
            }
        }
    ],

    "schema_invalid_requests": [
        {   
            "description": "Out of range - Values must be between 0 and 1",
            "request": {
                "routes_bounds": [-1, 2]
            }
        },
        {   
            "description": "Out of range num_chunks - Exceeds MAX_NUM_CHUNKS",
            "request": {
                "num_chunks": MAX_NUM_CHUNKS + 1
            }
        },
        {   
            "description": "Invalid hashedUserNiceName - Exceeds maxLength",
            "request": {
                "hashedUserNiceName": "a" * 129  # 129 characters, max is 128
            }
        },
        {   
            "description": "Invalid hashedUserIPAddress - Wrong type",
            "request": {
                "hashedUserIPAddress": ["not-a-string"]
            }
        },
        {   
            "description": "Invalid hashedInputUserEmail - Wrong type",
            "request": {
                "hashedInputUserEmail": 12345
            }
        }
    ],

    "function_invalid_requests": [
        {   
            "description": "Missing required field",
            "request": {
                "user_question": REMOVE_FIELD
            }
        },
        {   
            "description": "Invalid data types - Should be string",
            "request": {
                "user_question": 12345
            }
        },
        {   
            "description": "Empty required field - Function will not accept empty string",
            "request": {
                "user_question": ""
            }
        },
        {   
            "description": "Invalid data types - Should be string",
            "request": {
                "vector_index_name": ["invalid-type"]
            }
        },
        {   
            "description": "Invalid data types - Should be integer",
            "request": {
                "num_chunks": "3"
            }
        },
        {   
            "description": "Invalid routes_bounds array length - Should be exactly 2 items",
            "request": {
                "routes_bounds": [0.3, 0.5, 0.8]
            }
        },
    ]
}

API_ENDPOINT_QRAG_LLM = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-llm"
API_ENDPOINT_QRAG_LLM_PROD = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/qrag-llm"
SCHEMA_QRAG_LLM = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "QRAGLLMRequest", 
    "type": "object",
    "required": ["metadata", "content"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["routes_info", "vector_index_name"],
            "properties": {
                "vector_index_name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_PARAMETER_LENGTH
                },
                "user_id": {
                    "type": "string",
                    "maxLength": MAX_USER_NAME_LENGTH
                },
                "bot_version": {
                    "type": "string",
                    "maxLength": MAX_PARAMETER_LENGTH
                },
                "timestamp": {
                    "type": "string",
                    "maxLength": MAX_PARAMETER_LENGTH
                },
                "large_context_filename": {
                    "type": ["string", "null"],  # Allow either string or null
                    "maxLength": MAX_FILE_NAME_LENGTH
                },
                "routes_info": {
                    "type": "object",
                    "properties": {
                        "routes_flow_name": {"type": "string"},
                        "upper_sim_bound": {"type": "number"},
                        "lower_sim_bound": {"type": "number"},
                        "max_sim": {"type": "string"},
                        "max_stars": {"type": "integer"},
                        "routes_dict_content": {"type": "object"}
                    },
                    "additionalProperties": True
                },
                "is_retry": {
                    "type": "boolean"
                }
            },
            "additionalProperties": True
        },
        "content": {
            "type": "object",
            "required": ["user_question", "prompt_initial", "quoted_qa"],
            "properties": {
                "user_question": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_QUESTION_LENGTH
                },
                "route_preamble": {"type": "string"},
                "prompt_initial": {"type": "string"},
                "quoted_qa": {"type": "string"},
                "ai_answer": {"type": "string"},
                "retrieved_content": {
                    "type": "object",
                    "properties": {
                        "max_sim": {"type": "string"},
                        "max_stars": {"type": "integer"},
                        "chunks": {"type": "array"}
                    }
                }
            },
            "additionalProperties": False
        }
    }
}
TEST_REQUESTS_QRAG_LLM = {
    "clean_requests": [
        {   
            "description": "Complete matching Portal API Gateway test",
            "request": {
                "metadata": {
                    "timestamp": "2024-06-13T11:46:33.651753",
                    "user_id": "default", 
                    "vector_index_name": "deutsch-transcript-qrag-83f-20250202",
                    "bot_version": "2.0",
                    "routes_info": {
                        "routes_flow_name": "3 routes, separate route prompts",
                        "upper_sim_bound": 0.9,
                        "lower_sim_bound": 0.3,
                        "max_sim": "0.216",
                        "max_stars": 5,
                        "routes_dict_content": {
                            "routes_dict_name": "ROUTES_DICT_DEUTSCH_M1"
                        }
                    }
                },
                "content": {
                    "user_question": "What should I eat for lunch?",
                    "route_preamble": "Your question is not addressed in David Deutsch's interviews.",
                    "prompt_initial": "Given your knowledge of David Deutsch and his philosophy...",
                    "quoted_qa": "",
                    "ai_answer": "WAITING FOR AI ANSWER - USING HIGH QUALITY REASONING MODEL SO IT MAY TAKE 30-60 SECONDS...",
                    "retrieved_content": {
                        "max_sim": "0.216",
                        "max_stars": 5,
                        "chunks": []
                    }
                }
            }
        },
        {
            "description": "Complete matching Portal API Gateway test with large context filename",
            "request": {
                "metadata": {
                    "large_context_filename": "deutsch_large_context_v1.md"
                }
            }
        },
        {   
            "description": "Test retry flag",
            "request": {
                "metadata": {
                    "is_retry": True
                }
            }
        }
    ],
    "schema_invalid_requests": [
        {
            "description": "Exceeds maxLength",
            "request": {
                "metadata": {
                    "timestamp": "A"*(MAX_PARAMETER_LENGTH + 1)
                }
            }
        },
        {   
            "description": "Empty required field",
            "request": {
                "content": {
                    "user_question": ""
                }
            }
        },
        {   
            "description": "Invalid data types in content",
            "request": {
                "content": {
                    "user_question": 12345
                }
            }
        }
    ],

    "function_invalid_requests": [
        {   
            "description": "Missing required top-level field", 
            "request": {
                "metadata": REMOVE_FIELD
            }
        },
        {   
            "description": "Missing required content field",
            "request": {
                "content": {
                    "user_question": REMOVE_FIELD
                }
            }
        },
        {   
            "description": "Invalid data types in metadata",
            "request": {
                "metadata": {
                    "vector_index_name": ["invalid-type"]
                }
            }
        },
        {
            "description": "Large context filename not in S3 folder",
            "request": {
                "metadata": {
                    "large_context_filename": "not-present-filename.md"
                }
            }
        }
    ]
}

API_ENDPOINT_SEND_EMAIL = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/send-email"
API_ENDPOINT_SEND_EMAIL_PROD = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/send-email"
SCHEMA_SEND_EMAIL = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "SendEmailRequest",
    "type": "object",
    "required": ["to_address", "email_subject", "from_address"],
    "properties": {
        "to_address": {
            "type": "string",
            "format": "email",
            "maxLength": 254  # RFC 5321
        },
        "from_address": {
            "type": "string",
            "format": "email",
            "maxLength": 254
        },
        "email_subject": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200
        },
        "email_body_plain": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200000 # 4-14 updated from 10000
        },
        "email_body_html": {
            "type": "string",
            "maxLength": 200000 # 4-14 updated from 50000
        },
        "attachments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["filename", "content"],
                "properties": {
                    "filename": {
                        "type": "string",
                        "pattern": "^[\\w\\-. ]+$",
                        "maxLength": 255
                    },
                    "content": {
                        "type": "string",
                        "pattern": "^[A-Za-z0-9+/=]+$"  # Base64 pattern
                    }
                }
            },
            "maxItems": 10
        }
    },
    "additionalProperties": False
}
TEST_REQUESTS_SEND_EMAIL = {
    "clean_requests": [
        {   
            "description": "Basic email without HTML or attachments",
            "request": {
                "to_address": "recipient@example.com",
                "from_address": "contact@focusonfoundations.org", 
                "email_subject": "Test Subject",
                "email_body_plain": "Hello, this is a test email."
            }
        },
        {   
            "description": "Full featured email with HTML and attachment",
            "request": {
                "email_subject": "Test with Attachments",
                "email_body_plain": "Please see attached file.",
                "email_body_html": "<p>Please see attached file.</p>",
                "attachments": [{
                    "filename": "test.txt",
                    "content": "SGVsbG8gV29ybGQ="  # Base64 encoded "Hello World"
                }]
            }
        }
    ],
    "schema_invalid_requests": [
        {   
            "description": "Subject too long (>200 chars)",
            "request": {
                "email_subject": "A" * 201
            }
        }
    ],
    "function_invalid_requests": [
        {   
            "description": "Missing required field",
            "request": {
                "to_address": REMOVE_FIELD
            }
        },
        {   
            "description": "Missing required field", 
            "request": {
                "from_address": REMOVE_FIELD
            }
        },
        {   
            "description": "Empty required field",
            "request": {
                "to_address": ""
            }
        },
        {   
            "description": "Invalid email format",
            "request": {
                "to_address": "not-an-email"
            }
        }
    ]
}

API_ENDPOINT_VRAG_LLM = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/vrag-llm"
API_ENDPOINT_VRAG_LLM_PROD = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/vrag-llm"
SCHEMA_VRAG_LLM = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "VRAGLLMRequest",
    "type": "object",
    "required": [
        "user_question",
        "vector_index_name"
    ],
    "properties": {
        "user_question": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_QUESTION_LENGTH
        },
        "vector_index_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_PARAMETER_LENGTH
        },
        "vrag_preamble": {
            "type": "string",
            "maxLength": 1000
        },
        "llm_model": {
            "type": "string",
            "enum": ["gpt-4o", "gpt-4o-mini"]
        },
        "user_id": {
            "type": "string",
            "maxLength": MAX_USER_NAME_LENGTH
        },
        "vrag_version": {
            "type": "string",
            "maxLength": MAX_PARAMETER_LENGTH
        },
        "num_chunks": {
            "type": "integer",
            "maximum": MAX_NUM_CHUNKS  # don't apply min number of chunks
        }
    },
    "additionalProperties": False
}
TEST_REQUESTS_VRAG_LLM = {
    "clean_requests": [
        {   
            "description": "Complete request with all optional fields",
            "request": {
                "user_question": "What is David Deutsch's view on artificial intelligence?",
                "vector_index_name": "dd-transcripts-vrag-80f-20240727",
                "vrag_preamble": "Given your knowledge of David Deutsch and his philosophy of deep optimism, as well as the QUOTED TEXT from Deutsch below, answer the USER QUESTION.",
                "num_chunks": 5,
                "llm_model": "gpt-4o-mini",
                "user_id": "test_user",
                "vrag_version": "1.0"
            }
        },
        # {   
        #     "description": "Test with minimum required fields",
        #     "request": {
        #         "user_question": "What is David Deutsch's view on artificial intelligence?",
        #         "vector_index_name": "dd-transcripts-vrag-80f-20240727"
        #     }
        # }
    ],

    "schema_invalid_requests": [
        {   
            "description": "Invalid llm_model value not in enum list",
            "request": {
                "llm_model": "gpt-3"
            }
        },
        # {   
        #     "description": "User question exceeds maximum length",
        #     "request": {
        #         "user_question": "A" * (MAX_QUESTION_LENGTH + 1)
        #     }
        # },
        # {   
        #     "description": "Invalid num_chunks value exceeding maximum",
        #     "request": {
        #         "num_chunks": MAX_NUM_CHUNKS + 1
        #     }
        # },
        # {   
        #     "description": "Empty required field",
        #     "request": {
        #         "user_question": ""
        #     }
        # },
        # {   
        #     "description": "Invalid data type for num_chunks - should be integer",
        #     "request": {
        #         "num_chunks": "5"
        #     }
        # }
    ],

    "function_invalid_requests": [
        {   
            "description": "Missing required user_question field",
            "request": {
                "user_question": REMOVE_FIELD
            }
        },
        # {   
        #     "description": "Missing required vector_index_name field",
        #     "request": {
        #         "vector_index_name": REMOVE_FIELD
        #     }
        # },
        # {   
        #     "description": "Invalid data type for user_question",
        #     "request": {
        #         "user_question": ["not", "a", "string"]
        #     }
        # }
    ]
}


# ===== MAIN SECTION OF FILE core/aws-valid.py =====

# Define the mapping of Lambda functions to their suffix names
API_NAME_GLOBALS_MAPPING = {
    'deepgram-callback': 'DEEPGRAM_CALLBACK',  # No API Gateway Validation 12-21 RT
    'hash-store': 'HASH_STORE',
    'hash-store-prod': 'HASH_STORE_PROD',
    'hmac-hash': 'HMAC_HASH',
    'hmac-hash-prod': 'HMAC_HASH_PROD',
    'qrag-llm': 'QRAG_LLM',
    'qrag-llm-prod': 'QRAG_LLM_PROD',
    'qrag-routing': 'QRAG_ROUTING',
    'qrag-routing-prod': 'QRAG_ROUTING_PROD',
    'send-email': 'SEND_EMAIL',
    'send-email-prod': 'SEND_EMAIL_PROD',
    'vrag-llm': 'VRAG_LLM',
    'vrag-llm-prod': 'VRAG_LLM_PROD'
}
LAMBDA_JWT_REQUIRED = {
    'deepgram-callback': False,
    'hash-store': False,
    'hmac-hash': False,
    'qrag-llm': True,
    'qrag-routing': True,
    'send-email': True,
    'vrag-llm': True
}

APIS_VALIDATION_ENABLED = {
    'deepgram-callback': False,
    'hash-store': True,
    'hash-store-prod': True,
    'hmac-hash': True,
    'hmac-hash-prod': True,
    'qrag-llm': True,
    'qrag-llm-prod': True,
    'qrag-routing': True,
    'qrag-routing-prod': True,
    'send-email': True,
    'send-email-prod': True,
    'vrag-llm': True,
    'vrag-llm-prod': True
}

#cur_app_name = 'dummy_for_safety'
#cur_app_name='deepgram-callback'  
#cur_app_name='hmac-hash'
#cur_app_name='hash-store'
#cur_app_name='qrag-routing'
cur_app_name='qrag-llm'
#cur_app_name='send-email'
#cur_app_name='vrag-llm'
all_app_names = ['deepgram-callback', 'hmac-hash', 'hash-store', 'qrag-routing', 'qrag-llm', 'send-email', 'vrag-llm']

CHALICE_FOLDER = "web-shared/aws_chalice/"
# Per-app Chalice deploy logs (local-only via root logs/ symlink + .gitignore)
DEPLOY_LOGS_FOLDER = "logs/aws_chalice_deploys/"
ROOT_FOLDER = "/Users/randytrue/Documents/Code/corpus-tools/"
def get_deploy_logs_dir(app_name, env):
    """Repo-relative dir for an app's deployed_dev_logs or deployed_prod_logs."""
    if env == "dev":
        sub = "deployed_dev_logs"
    elif env == "prod":
        sub = "deployed_prod_logs"
    else:
        raise ValueError(f"env must be 'dev' or 'prod', got: {env!r}")
    return f"{DEPLOY_LOGS_FOLDER}{app_name}/{sub}"
def get_api_endpoint_url(api_gateway_name):
    """
    Get the API endpoint URL for an API gateway.
    
    :param api_gateway_name: string, name of the API gateway (e.g., 'hmac-hash')
    :return endpoint_url: string, the complete API endpoint URL
    """
    # Look up the corresponding API endpoint global variable
    suffix = API_NAME_GLOBALS_MAPPING.get(api_gateway_name)
    if not suffix:
        raise ValueError(f"No API mapping found for API gateway: {api_gateway_name}")
    
    endpoint_var_name = f"API_ENDPOINT_{suffix}"
    all_globals = globals()
    
    if endpoint_var_name not in all_globals:
        raise ValueError(f"API endpoint not defined for {api_gateway_name} (expected {endpoint_var_name})")
    
    # Return the endpoint URL directly
    return all_globals[endpoint_var_name]
def mtest_get_api_endpoint_url():
    pass
#if __name__ == "__main__":
    api_gateway_name = 'hmac-hash'
    endpoint_url = get_api_endpoint_url(api_gateway_name)
    print(f"API Endpoint URL for api_gateway_name: {api_gateway_name}\n{endpoint_url}")
def get_test_requests(app_name):
    """
    Get the test requests for a specific Lambda function.
    
    :param app_name: string, application name which is base name of the Lambda function (e.g., 'hmac-hash')
    :return test_requests: dict, dictionary containing the test requests for the Lambda
    """
    # Look up the corresponding suffix in the mapping
    suffix = API_NAME_GLOBALS_MAPPING.get(app_name)
    if not suffix:
        raise ValueError(f"No API mapping found for application: {app_name}")
    
    # Construct the test requests variable name
    test_requests_var_name = f"TEST_REQUESTS_{suffix}"
    all_globals = globals()
    
    if test_requests_var_name not in all_globals:
        raise ValueError(f"Test requests not defined for {app_name} (expected {test_requests_var_name})")
    
    # Return the test requests
    return all_globals[test_requests_var_name]
def mtest_get_test_requests():
    pass
#if __name__ == "__main__":
    test_requests = get_test_requests(cur_app_name)
    print(f"Test requests for {cur_app_name}:")
    print(f"Categories: {list(test_requests.keys())}")
    for category, requests in test_requests.items():
        print(f"  {category}: {len(requests)} requests")
def create_complete_request(partial_request, template_request):
    """
    Create a complete request by filling in missing fields from a template.
    Special handling: If a field's value is REMOVE_FIELD, remove it from the final request.
    
    :param partial_request: dict, the request with some fields specified.
    :param template_request: dict, complete request to use as a template for missing fields.
    :return complete_request: dict, complete request with all fields, using template values for missing fields.
    """
    def update_dict(template, partial):
        """Recursively update template dict with partial dict values."""
        result = template.copy()
        for key, value in partial.items():
            if value == REMOVE_FIELD:
                result.pop(key, None)
            elif isinstance(value, dict) and key in template and isinstance(template[key], dict):
                # Recursively update nested dictionaries
                result[key] = update_dict(template[key], value)
            else:
                result[key] = value
        return result

    # Check if either has description/request structure
    partial_has_structure = isinstance(partial_request, dict) and set(partial_request.keys()) == {"description", "request"}
    template_has_structure = isinstance(template_request, dict) and set(template_request.keys()) == {"description", "request"}
    
    # If one has structure and other doesn't, that's an error
    if partial_has_structure != template_has_structure:
        raise ValueError("Both partial_request and template_request must have the same structure (either both with description/request or both without)")
    
    if partial_has_structure:
        # Process only the request portion
        complete_request_data = update_dict(template_request["request"], partial_request["request"])
        return {
            "description": partial_request["description"],
            "request": complete_request_data
        }
    else:
        # Original behavior for non-structured requests
        return update_dict(template_request, partial_request)
def mtest_create_complete_request():
    pass
#if __name__ == "__main__":
    template_request = TEST_REQUESTS_QRAG_LLM['clean_requests'][0]
    partial_request = TEST_REQUESTS_QRAG_LLM['schema_invalid_requests'][0]
    complete_request = create_complete_request(partial_request, template_request)
    expected_request = {   
            "description": "Invalid llm_model value - Not in enum list",  # Use partial request's description
            "request": {
                "metadata": {
                    "timestamp": "2024-06-13T11:46:33.651753",
                    "user_id": "default", 
                    "vector_index_name": "deutsch-transcript-qrag-78f-20240926",
                    "bot_version": "1.0",
                    "llm_model": "gpt-3",
                    "routes_info": {
                        "routes_flow_name": "3 routes, sim-star double, separate prompts",
                        "upper_sim_bound": 0.9,
                        "lower_sim_bound": 0.3,
                        "max_sim": "0.216",
                        "max_stars": 5,
                        "routes_dict_content": {
                            "routes_dict_name": "ROUTES_DICT_DEUTSCH_V3"
                        }
                    }
                },
                "content": {
                    "user_question": "What should I eat for lunch?",
                    "route_preamble": "Your question is not addressed in David Deutsch's interviews.",
                    "quoted_qa": "",
                    "ai_answer": "WAITING FOR AI ANSWER - USING HIGH QUALITY REASONING MODEL SO IT MAY TAKE 30-60 SECONDS...",
                    "retrieved_content": {
                        "max_sim": "0.216",
                        "max_stars": 5,
                        "chunks": []
                    }
                }
            }
    }
    if complete_request == expected_request:
        print("Complete request matches expected request - TEST PASSES!!")
    else:
        print("Complete request does not match expected request - TEST FAILS!!")
        print("Complete Request:")
        print(json.dumps(complete_request, indent=4))
        print("Expected Request:")
        print(json.dumps(expected_request, indent=4))
def map_names_env_stages(app_name, env):
    """
    Map application name to environment and stage.
    
    :param app_name: str, application name (e.g., 'hmac-hash').
    :param env: str, deployment environment ('dev' or 'prod').
    :return: tuple, (api_gateway_name, stage, aws_lambda_name)
    """
    if env == 'dev':
        api_gateway_name = app_name
        stage = 'api'
        aws_lambda_name = f"{app_name}-dev"
    elif env == 'prod':
        api_gateway_name = f"{app_name}-prod"
        stage = 'prod'
        aws_lambda_name = f"{app_name}-prod"
    else:
        raise ValueError(f"Invalid environment (only 'dev' or 'prod' allowed): {env}")
    return api_gateway_name, stage, aws_lambda_name
def test_lambda_requests(app_name, env, first_request_only=False, direct_lambda=True, with_gateway=True, debug_prompt=False, output_file="apps/qrag/web/test_back-end_validation.md", jwt_token=None):
    """
    Test requests for any Lambda function both directly and through API Gateway.

    :param app_name: str, app_name which is base name of the Lambda function (e.g., 'hmac-hash').
    :param env: str, deployment environment ('dev' or 'prod').
    :param first_request_only: bool, whether to run only the first clean request.
    :param direct_lambda: bool, whether to test direct Lambda invocation.
    :param with_gateway: bool, whether to test through API Gateway.
    :param debug_prompt: bool, whether to prompt user to continue after each request.
    :param output_file: str, path to the output markdown file.
    :param jwt_token: str, optional JWT token for authenticated endpoints.
    :return: dict, test results.
    """
    # Create StringIO object to capture output
    from io import StringIO
    import sys
    output_buffer = StringIO()
    original_stdout = sys.stdout
    sys.stdout = output_buffer

    def write_to_both(message):
        """Helper function to write to both file and terminal"""
        output_buffer.write(message + "\n")
        sys.stdout = original_stdout
        print(message)
        sys.stdout = output_buffer

    # Validate that at least one testing path is enabled
    if not (direct_lambda or with_gateway):
        raise ValueError("At least one testing path must be enabled. "
                       "Set either direct_lambda=True or with_gateway=True")
    
    # Map application name to environment and stage
    api_gateway_name, stage, aws_lambda_name = map_names_env_stages(app_name, env)
    
    # Get API endpoint URL for this Lambda function
    try:
        api_endpoint = get_api_endpoint_url(api_gateway_name)
    except ValueError as e:
        raise ValueError(f"Failed to get API endpoint url for api_gateway_name: {api_gateway_name}: {str(e)}")
    
    # Get test requests for this Lambda function
    try:
        test_requests = get_test_requests(app_name)
    except ValueError as e:
        raise ValueError(f"Failed to get test requests for {app_name}: {str(e)}")
    
    # Get template request from first clean request
    if not test_requests.get('clean_requests'):
        raise ValueError(f"No clean requests found for {app_name}")
    template_request = test_requests['clean_requests'][0]
    
    lambda_client = boto3.client('lambda')
    
    def invoke_lambda(request_data):
        """Direct Lambda invocation that simulates API Gateway event."""
        try:
            # Extract route from API endpoint URL
            api_endpoint_parts = api_endpoint.split('/')
            route = '/' + api_endpoint_parts[-1]  # Get the last part of the URL
            
            # Build headers with optional JWT
            headers = {
                "Content-Type": "application/json",
                "origin": "https://www.focusonfoundations.org"
            }
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            # Build a mock API Gateway event
            lambda_payload = {
                "resource": route,
                "path": route,
                "httpMethod": "POST",
                "headers": headers,
                "multiValueHeaders": {
                    "Content-Type": ["application/json"]
                },
                "queryStringParameters": None,
                "multiValueQueryStringParameters": None,
                "pathParameters": None,
                "stageVariables": None,
                "requestContext": {
                    "resourcePath": route,
                    "httpMethod": "POST",
                    "stage": stage,
                    "identity": {
                        "sourceIp": "127.0.0.1",
                        "userAgent": "custom-agent"
                    }
                },
                "body": json.dumps(request_data),
                "isBase64Encoded": False
            }

            response = lambda_client.invoke(
                FunctionName=aws_lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(lambda_payload)
            )

            # Parse and debug the response
            response_payload = json.loads(response['Payload'].read())
            print("Lambda response payload:", json.dumps(response_payload, indent=2))
            
            return response_payload

        except Exception as e:
            print(f"Error invoking Lambda: {e}")
            return {"error": str(e)}

    def invoke_gateway(request_data):
        """API Gateway invocation"""
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            # Debug print
            print("Request being sent to API Gateway:")
            print(json.dumps(request_data, indent=2))
            
            if jwt_token:
                headers['Authorization'] = f'Bearer {jwt_token}'

            response = requests.post(
                api_endpoint,
                json=request_data,
                headers=headers,
                timeout=180  # Changed from 10 to 180 seconds
            )
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON response: {response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    def check_lambda_success(lambda_result):
        """Check if Lambda invocation was successful"""
        try:
            # Check if it's a direct Lambda response (contains statusCode and body)
            if "statusCode" in lambda_result:
                if lambda_result["statusCode"] != 200:
                    return False
                # Parse the body if it's a string
                body = (json.loads(lambda_result["body"]) 
                       if isinstance(lambda_result["body"], str) 
                       else lambda_result["body"])
                return body.get("status") == "Success"
            # Otherwise check if it's already parsed response
            return lambda_result.get("status") == "Success"
        except Exception as e:
            print(f"Error checking Lambda success: {e}")
            return False

    def check_gateway_success(gateway_result):
        """Check if Gateway invocation was successful"""
        try:
            return gateway_result.get("status") == "Success"
        except Exception as e:
            print(f"Error checking Gateway success: {e}")
            return False

    # Initialize results dictionary with only the categories present in test_requests
    results = {}
    for category in test_requests.keys():
        results[category] = []

    # Test each category that exists in test_requests
    now_datetime = get_current_datetime_filefriendly()
    write_to_both(f"\n\n## ====== Testing {app_name}  {now_datetime} ======")
    
    # If first_request_only is True, only process the first clean request
    if first_request_only:
        write_to_both(f"\n\n## ====== clean_requests for {app_name} (first request only) ======")
        # Get the first clean request
        partial_request = test_requests['clean_requests'][0]
        complete_request = partial_request
        
        # Extract description if present, otherwise empty string
        description = ""
        if isinstance(partial_request, dict) and "description" in partial_request:
            description = partial_request["description"]
        
        write_to_both(f"\n## clean_requests Request 1: {description}")
        write_to_both("Original: " + json.dumps(partial_request, indent=2))
        write_to_both("Complete: " + json.dumps(complete_request, indent=2))
        
        # Extract just the request data for the API calls
        request_data = complete_request.get("request", complete_request)
        
        lambda_result = None
        gateway_result = None
        
        if direct_lambda:
            write_to_both("\n### DIRECT LAMBDA INVOCATION")
            lambda_result = invoke_lambda(request_data)
            write_to_both("Result:")
            write_to_both(json.dumps(lambda_result, indent=2))
        
        if with_gateway:
            write_to_both("\n### API GATEWAY INVOCATION")
            gateway_result = invoke_gateway(request_data)
            write_to_both("Result:")
            write_to_both(json.dumps(gateway_result, indent=2))
        
        # Store results with success/error status
        results['clean_requests'].append({
            "request": complete_request,
            "lambda_result": {
                "response": lambda_result,
                "success": check_lambda_success(lambda_result) if lambda_result else None
            } if direct_lambda else None,
            "gateway_result": {
                "response": gateway_result,
                "success": check_gateway_success(gateway_result) if gateway_result else None
            } if with_gateway else None
        })
    else:
        # Process all requests
        for category, request_list in test_requests.items():
            write_to_both(f"\n\n## ====== {category} for {app_name} ======")
            for i, partial_request in enumerate(request_list, 1):
                # Skip first clean request since it's our template
                if category == 'clean_requests' and i == 1:
                    complete_request = partial_request
                else:
                    complete_request = create_complete_request(partial_request, template_request)
                
                # Extract description if present, otherwise empty string
                description = ""
                if isinstance(partial_request, dict) and "description" in partial_request:
                    description = partial_request["description"]
                elif isinstance(complete_request, dict) and "description" in complete_request:
                    description = complete_request["description"]
                    
                write_to_both(f"\n## {category:<25}Request {i}: {description}")
                write_to_both("Original: " + json.dumps(partial_request, indent=2))
                write_to_both("Complete: " + json.dumps(complete_request, indent=2))
                
                # Extract just the request data for the API calls
                request_data = complete_request.get("request", complete_request)
                
                lambda_result = None
                gateway_result = None
                
                if direct_lambda:
                    write_to_both("\n### DIRECT LAMBDA INVOCATION")
                    lambda_result = invoke_lambda(request_data)
                    write_to_both("Result:")
                    write_to_both(json.dumps(lambda_result, indent=2))
                
                if with_gateway:
                    write_to_both("\n### API GATEWAY INVOCATION")
                    gateway_result = invoke_gateway(request_data)
                    write_to_both("Result:")
                    write_to_both(json.dumps(gateway_result, indent=2))
                
                # Store results with success/error status
                results[category].append({
                    "request": create_complete_request(partial_request, template_request),
                    "lambda_result": {
                        "response": lambda_result,
                        "success": check_lambda_success(lambda_result) if lambda_result else None
                    } if direct_lambda else None,
                    "gateway_result": {
                        "response": gateway_result,
                        "success": check_gateway_success(gateway_result) if gateway_result else None
                    } if with_gateway else None
                })
                
                if debug_prompt:
                    user_continue_response = input("Press any key to continue or 'x' to exit...").strip().lower()
                    if user_continue_response == 'x':
                        return results
                else:
                    sleep(0.5)  # Rate limiting

    def summarize_results(results):
        """Summarize test results and expectations"""
        # Initialize summary
        summary = {category: {
            "total": 0,
            "lambda": {"success": 0, "error": 0},
            "gateway": {"success": 0, "error": 0}
        } for category in results.keys()}
        
        total_tests = 0
        failed_tests = 0
        
        write_to_both(f"\n## ===== API Gateway Validation Test Summary {app_name} =====")
        write_to_both(f"API Gateway name: {api_gateway_name}\nAPI endpoint URL: {api_endpoint}")

        for category, requests in results.items():
            summary[category]["total"] = len(requests)
            total_tests += len(requests) * 2
            
            write_to_both(f"\n{category} ({summary[category]['total']} tests):")
            
            # Define expected behavior for each category
            expected_behaviors = {
                "clean_requests": {"lambda": "SUCCESS", "gateway": "SUCCESS"},
                "schema_invalid_requests": {"lambda": "SUCCESS", "gateway": "ERROR"},
                "function_invalid_requests": {"lambda": "ERROR", "gateway": "ERROR"}
            }
            
            # Get expected behavior for this category
            expected = expected_behaviors[category]
            
            # Lambda Results
            expected_lambda = "SUCCESS" if "clean" in category else "ERROR" if "function_invalid" in category else "SUCCESS"
            lambda_stats = summary[category]["lambda"]
            
            # Track successes/errors for summary stats
            for i, result in enumerate(requests, 1):
                if result["lambda_result"]:
                    if result["lambda_result"]["success"]:
                        lambda_stats["success"] += 1
                    else:
                        lambda_stats["error"] += 1
                    
                    # Compare against expected behavior for failure count
                    if ((result["lambda_result"]["success"] and expected["lambda"] == "ERROR") or 
                        (not result["lambda_result"]["success"] and expected["lambda"] == "SUCCESS")):
                        failed_tests += 1
                
                if result["gateway_result"]:
                    if result["gateway_result"]["success"]:
                        summary[category]["gateway"]["success"] += 1
                    else:
                        summary[category]["gateway"]["error"] += 1
                    
                    # Compare against expected behavior for failure count
                    if ((result["gateway_result"]["success"] and expected["gateway"] == "ERROR") or 
                        (not result["gateway_result"]["success"] and expected["gateway"] == "SUCCESS")):
                        failed_tests += 1
            
            # Display Lambda results
            lambda_passed = (
                (expected_lambda == "SUCCESS" and lambda_stats["success"] == summary[category]["total"]) or
                (expected_lambda == "ERROR" and lambda_stats["error"] == summary[category]["total"])
            )
            write_to_both(f"  Lambda Results: (expected {expected_lambda})  {'✓' if lambda_passed else '✗'}")
            for i, result in enumerate(requests, 1):
                if result["lambda_result"]:
                    status = "SUCCESS" if result["lambda_result"]["success"] else "ERROR"
                    write_to_both(f"    test {i}:  {status}")
                else:
                    write_to_both(f"    test {i}:  SKIPPED")
            
            # Display Gateway results
            expected_gateway = "SUCCESS" if "clean" in category else "ERROR"
            gateway_stats = summary[category]["gateway"]
            gateway_passed = (
                (expected_gateway == "SUCCESS" and gateway_stats["success"] == summary[category]["total"]) or
                (expected_gateway == "ERROR" and gateway_stats["error"] == summary[category]["total"])
            )
            write_to_both(f"  Gateway Results: (expected {expected_gateway})  {'✓' if gateway_passed else '✗'}")
            for i, result in enumerate(requests, 1):
                if result["gateway_result"]:
                    status = "SUCCESS" if result["gateway_result"]["success"] else "ERROR"
                    write_to_both(f"    test {i}:  {status}")
                else:
                    write_to_both(f"    test {i}:  SKIPPED")
        
        # Print final summary
        passed_tests = total_tests - failed_tests
        write_to_both(f"\nTest Results: {passed_tests} passed, {failed_tests} failed  {'✓' if failed_tests == 0 else '✗'}")

        return summary

    try:
        # Run tests and get summary
        summary = summarize_results(results)

        # Write captured output to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("## API Gateway Validation Test Results\n\n")
            f.write(output_buffer.getvalue())
        
        return results

    finally:
        sys.stdout = original_stdout
        output_buffer.close()
def mrun_test_lambda_requests():
    pass
#if __name__ == "__main__":
    env = 'dev'
    if LAMBDA_JWT_REQUIRED.get(cur_app_name, False):  # defaults to False
        jwt_token = JWT_TEST
        print(f"JWT token is required, using JWT_TEST: {jwt_token}")
    else:
        jwt_token = None
        print("JWT token is NOT required")

    results = test_lambda_requests(cur_app_name, env, first_request_only=False, direct_lambda=True, with_gateway=True, jwt_token=jwt_token)

def confirm_lambda_jwt_required(app_name, env):
    """
    Confirm whether a Lambda function requires JWT by testing through API Gateway with and without JWT token.
    
    :param app_name: str, base name of the Lambda function (e.g., 'qrag-routing').
    :param env: str, deployment environment ('dev', 'prod', etc.).
    :return: bool, True if the LAMBDA_JWT_REQUIRED setting is confirmed correct, False otherwise.
    """
    print(f"\n===== Testing JWT requirement for {app_name} =====")
    
    # Get expected JWT requirement from global dictionary
    expected_jwt_required = LAMBDA_JWT_REQUIRED.get(app_name, False)
    print(f"Global LAMBDA_JWT_REQUIRED setting: {expected_jwt_required}")
    
    # Map application name to environment and stage
    api_gateway_name, stage, aws_lambda_name = map_names_env_stages(app_name, env)
    
    # Get API endpoint URL for this Lambda function
    try:
        api_endpoint = get_api_endpoint_url(api_gateway_name)
    except ValueError as e:
        print(f"ERROR: Failed to get API endpoint url for api_gateway_name: {api_gateway_name}: {str(e)}")
        return False
    
    # Get test requests for this Lambda function
    try:
        test_requests = get_test_requests(app_name)
    except ValueError as e:
        print(f"ERROR: Failed to get test requests for {app_name}: {str(e)}")
        return False
    
    # Get template request from first clean request
    if not test_requests.get('clean_requests'):
        print(f"ERROR: No clean requests found for {app_name}")
        return False
    
    template_request = test_requests['clean_requests'][0]
    request_data = template_request.get("request", template_request)
    
    def invoke_gateway_with_jwt(jwt_token=None):
        """Invoke API Gateway with optional JWT token"""
        try:
            headers = {'Content-Type': 'application/json'}
            if jwt_token:
                headers['Authorization'] = f'Bearer {jwt_token}'

            response = requests.post(
                api_endpoint,
                json=request_data,
                headers=headers,
                timeout=30
            )
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON response: {response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    # Check if response indicates success
    def check_success(result):
        """Check if request was successful"""
        return result.get("status") == "Success" or "error" not in result

    # Test with JWT token
    print("\n1. Testing with JWT token using API Gateway:")
    with_jwt_result = invoke_gateway_with_jwt(JWT_TEST)
    with_jwt_success = check_success(with_jwt_result)
    print(f"  Result: {'SUCCESS' if with_jwt_success else 'FAILED'}")
    
    # Test without JWT token
    print("\n2. Testing without JWT token using API Gateway:")
    without_jwt_result = invoke_gateway_with_jwt()
    without_jwt_success = check_success(without_jwt_result)
    print(f"  Result: {'SUCCESS' if without_jwt_success else 'FAILED'}")
    
    # Determine actual JWT requirement based on test results
    actual_jwt_required = (with_jwt_success and not without_jwt_success)
    
    # Compare expected vs actual
    jwt_setting_correct = (expected_jwt_required == actual_jwt_required)
    
    # Import termcolor for colored output
    from termcolor import colored
    
    print(f"\nCONCLUSION:")
    print(f"  Expected JWT required: {expected_jwt_required}")
    print(f"  Actual JWT required: {actual_jwt_required}")
    
    # Print colored output based on whether the setting is correct
    if jwt_setting_correct:
        print(f"  {colored('✓ LAMBDA_JWT_REQUIRED setting is CORRECT', 'green')}")
    else:
        print(f"  {colored('✗ LAMBDA_JWT_REQUIRED setting is INCORRECT', 'red')}")
    
    return jwt_setting_correct
def mrun_confirm_lambda_jwt_required():
    pass
#if __name__ == "__main__":
    env = 'dev'
    # Test a specific Lambda
    confirm_lambda_jwt_required(cur_app_name, stage)
    
    # OR test all Lambdas
    # for app_name in all_app_names:
    #     confirm_lambda_jwt_required(app_name, stage)
    #     print("\n" + "-"*80 + "\n")

def set_options_method_to_reflect_requesting_origin(api_gateway_name):  # NOT USED
    """
    Fix CORS headers after Chalice deployment to properly handle origin restrictions.
    Sets OPTIONS method integration response to reflect the requesting origin rather than using '*'.
    
    :param api_gateway_name: str, name of the API Gateway
    :param allowed_origins: list, list of allowed origins (used in docstring only, enforced by Lambda)
    :return: bool, True if successful, False otherwise
    """
    # Get API ID and resource ID
    api_client = boto3.client('apigateway')
    apis = api_client.get_rest_apis()['items']
    api = next((a for a in apis if a['name'] == api_gateway_name), None)
    if not api:
        print(f"API {api_gateway_name} not found")
        return False
    
    rest_api_id = api['id']
    resources = api_client.get_resources(restApiId=rest_api_id)['items']
    
    # Find resources with OPTIONS method
    for resource in resources:
        if 'resourceMethods' in resource and 'OPTIONS' in resource['resourceMethods']:
            resource_id = resource['id']
            
            # Fix OPTIONS method for CORS
            try:
                # Get method configuration
                options_method = api_client.get_method(
                    restApiId=rest_api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS'
                )
                
                # Get integration responses
                integration = options_method.get('methodIntegration', {})
                if 'integrationResponses' in integration and '200' in integration['integrationResponses']:
                    # Update the integration response
                    api_client.update_integration_response(
                        restApiId=rest_api_id,
                        resourceId=resource_id,
                        httpMethod='OPTIONS',
                        statusCode='200',
                        patchOperations=[
                            {
                                'op': 'replace',
                                'path': '/responseParameters/method.response.header.Access-Control-Allow-Origin',
                                'value': "'${method.request.header.Origin}'"
                            }
                        ]
                    )
                    print(f"Updated CORS headers for resource {resource_id}")
            except Exception as e:
                print(f"Error updating CORS headers: {str(e)}")
    
    # Deploy the API to apply changes
    try:
        api_client.create_deployment(
            restApiId=rest_api_id,
            stageName='dev',
            description='Fixed CORS headers'
        )
        print("Deployed API with CORS fixes")
        return True
    except Exception as e:
        print(f"Error deploying API: {str(e)}")
        return False
def mrun_set_options_method_to_reflect_requesting_origin():
    pass
#if __name__ == "__main__":
    set_options_method_to_reflect_requesting_origin('hmac-hash')

# Define allowed origins as a list
ALLOWED_ORIGINS = [
    'https://www.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:3000'
]

def get_api_gateway_cors_configuration(rest_api_id, resource_id=None):
    """
    Get CORS configuration for an API Gateway.
    
    :param rest_api_id: str, the REST API ID
    :param resource_id: str, optional resource ID to check specific resource
    :return: dict, CORS configuration information
    """
    api_client = boto3.client('apigateway')
    result = {
        'enabled': False,
        'configuration': {}
    }
    print(colored(f"\n===== Getting CORS configuration for rest_api_id: {rest_api_id} resource_id: {resource_id} =====", "blue"))
    
    try:
        # Get all resources if resource_id is not provided
        if not resource_id:
            resources = api_client.get_resources(restApiId=rest_api_id)
            resources = resources.get('items', [])
        else:
            # Get specific resource
            resources = [api_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)]
        
        # Check each resource for CORS configuration
        for resource in resources:
            # Check for OPTIONS method which indicates CORS is probably configured
            if 'resourceMethods' in resource and 'OPTIONS' in resource['resourceMethods']:
                result['enabled'] = True
                
                # Get the OPTIONS method integration
                try:
                    options_method = api_client.get_method(
                        restApiId=rest_api_id,
                        resourceId=resource['id'],
                        httpMethod='OPTIONS'
                    )
                    
                    # Get integration responses which contain CORS headers
                    integration_responses = options_method.get('methodIntegration', {}).get('integrationResponses', {})
                    
                    # Extract CORS headers from the 200 response
                    if '200' in integration_responses:
                        cors_headers = integration_responses['200'].get('responseParameters', {})
                        
                        # Transform the response parameters to more readable format
                        for param, value in cors_headers.items():
                            if 'method.response.header' in param:
                                header_name = param.split('method.response.header.')[1]
                                result['configuration'][header_name] = value
                        
                        # Already found CORS config, no need to check other resources
                        if result['configuration']:
                            break
                except Exception as e:
                    print(f"Error getting OPTIONS method: {str(e)}")
            
            # Check for CORS enabled in resource properties
            if 'corsConfiguration' in resource:
                result['enabled'] = True
                result['configuration'] = resource['corsConfiguration']
                break
                
        # If we haven't found CORS config yet, try to get it from the API export
        if result['enabled'] and not result['configuration']:
            try:
                # Export the API definition
                export = api_client.get_export(
                    restApiId=rest_api_id,
                    stageName='dev',  # Use dev stage as default
                    exportType='swagger',
                    accepts='application/json'
                )
                
                # Parse the exported definition
                api_def = json.loads(export['body'].read().decode('utf-8'))
                
                # Check for CORS in the API definition
                if 'x-amazon-apigateway-cors' in api_def:
                    result['configuration'] = api_def['x-amazon-apigateway-cors']
            except Exception as e:
                print(f"Error getting API export for CORS check: {str(e)}")
        
        return result
    except Exception as e:
        print(f"Error getting CORS configuration: {str(e)}")
        return result
def mrun_get_api_gateway_cors_configuration():
    pass
#if __name__ == "__main__":
    rest_api_id, _ = get_api_gateway_and_resource_ids("hmac-hash-prod")
    resource_id = None
    print(get_api_gateway_cors_configuration(rest_api_id, resource_id))
def test_cors_configuration(app_name, env, allowed_origins):
    """
    Test CORS configuration for a Lambda function's API Gateway endpoint.
    
    :param app_name: str, base name of the Lambda function
    :param env: str, deployment environment ('dev' or 'prod')
    :param allowed_origins: list, list of allowed origins to test
    :return: bool, True if CORS configuration is working as expected
    """
    print(colored(f"\n===== Testing CORS configuration for {app_name} stage: {env} =====", "blue"))
    
    # Map application name to environment and stage
    api_gateway_name, stage, aws_lambda_name = map_names_env_stages(app_name, env)
     
    # Get API endpoint URL
    try:
        api_endpoint = get_api_endpoint_url(api_gateway_name)
        print(f"API endpoint: {api_endpoint}")
    except ValueError as e:
        print(colored(f"ERROR: Failed to get API endpoint url for api_gateway_name: {api_gateway_name}: {str(e)}", "red"))
        return False
    
    # Get test request data (first clean request)
    try:
        test_requests = get_test_requests(app_name)
        if not test_requests.get('clean_requests'):
            print(colored("ERROR: No clean requests found", "red"))
            return False
        request_data = test_requests['clean_requests'][0].get("request", test_requests['clean_requests'][0])
    except Exception as e:
        print(colored(f"ERROR: Failed to get test data: {str(e)}", "red"))
        return False
    
    # Validate allowed origins
    if not allowed_origins:
        print(colored("ERROR: No allowed origins provided for testing", "red"))
        return False
    
    # Add disallowed origins for testing
    disallowed_origins = ['https://example.com', 'http://invalid-domain.com']
    
    all_tests_passed = True
    
    # Test OPTIONS request (preflight) first
    print(colored("\n1. Testing OPTIONS preflight requests:", "blue"))
    print(colored("  Expected: Allowed origins should receive CORS headers, disallowed origins should not.", "blue"))
    
    print(colored("\n  Allowed Origins:", "cyan"))
    for origin in allowed_origins:
        try:
            headers = {
                'Origin': origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(api_endpoint, headers=headers, timeout=10)
            
            # Check for CORS headers in response
            has_cors_headers = 'access-control-allow-origin' in response.headers.keys()
            response_origin = response.headers.get('access-control-allow-origin')
            
            if has_cors_headers:
                if response_origin == origin or response_origin == '*':
                    print(colored(f"    ✓ {origin}: Successfully received CORS headers", "green"))
                else:
                    print(colored(f"    ✓ {origin}: Received CORS header with value: {response_origin}", "green"))
            else:
                print(colored(f"    ✗ {origin}: Did not receive expected CORS headers", "red"))
                all_tests_passed = False
                
        except Exception as e:
            print(colored(f"    ! {origin}: Error during test: {str(e)}", "red"))
            all_tests_passed = False
    
    print(colored("\n  Disallowed Origins:", "cyan"))
    for origin in disallowed_origins:
        try:
            headers = {
                'Origin': origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(api_endpoint, headers=headers, timeout=10)
            
            # Check for CORS headers in response
            has_cors_headers = 'access-control-allow-origin' in response.headers.keys()
            response_origin = response.headers.get('access-control-allow-origin')
            
            if not has_cors_headers:
                print(colored(f"    ✓ {origin}: Correctly did not receive CORS headers", "green"))
            else:
                # If we get CORS headers for disallowed origins, that's a security issue
                print(colored(f"    ✗ {origin}: Incorrectly received CORS header: {response_origin}", "red"))
                all_tests_passed = False
                
        except Exception as e:
            print(colored(f"    ! {origin}: Error during test: {str(e)}", "red"))
            all_tests_passed = False
    
    # Test actual POST request
    print(colored("\n2. Testing POST requests with different origins:", "blue"))
    print(colored("  Expected: Allowed origins should receive CORS headers, disallowed origins should not.", "blue"))
    
    print(colored("\n  Allowed Origins:", "cyan"))
    for origin in allowed_origins:
        try:
            headers = {
                'Origin': origin,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                api_endpoint,
                json=request_data,
                headers=headers,
                timeout=10
            )
            
            # Check for CORS headers in response
            has_cors_headers = 'access-control-allow-origin' in response.headers.keys()
            response_origin = response.headers.get('access-control-allow-origin')
            
            if has_cors_headers:
                if response_origin == origin or response_origin == '*':
                    print(colored(f"    ✓ {origin}: Successfully received CORS headers", "green"))
                else:
                    print(colored(f"    ✓ {origin}: Received CORS header with value: {response_origin}", "green"))
            else:
                print(colored(f"    ✗ {origin}: Did not receive expected CORS headers", "red"))
                all_tests_passed = False
                
        except Exception as e:
            print(colored(f"    ! {origin}: Error during test: {str(e)}", "red"))
            all_tests_passed = False
    
    print(colored("\n  Disallowed Origins:", "cyan"))
    for origin in disallowed_origins:
        try:
            headers = {
                'Origin': origin,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                api_endpoint,
                json=request_data,
                headers=headers,
                timeout=10
            )
            
            # Check for CORS headers in response
            has_cors_headers = 'access-control-allow-origin' in response.headers.keys()
            response_origin = response.headers.get('access-control-allow-origin')
            
            if not has_cors_headers:
                print(colored(f"    ✓ {origin}: Correctly did not receive CORS headers", "green"))
            else:
                # If we get CORS headers for disallowed origins, that's a security issue
                print(colored(f"    ✗ {origin}: Incorrectly received CORS header: {response_origin}", "red"))
                all_tests_passed = False
                
        except Exception as e:
            print(colored(f"    ! {origin}: Error during test: {str(e)}", "red"))
            all_tests_passed = False
    
    # Final result
    if all_tests_passed:
        print(colored("\n✓ CORS configuration is working correctly! All origins behaved as expected.", "green"))
    else:
        print(colored("\n✗ CORS configuration has issues. Check the results above.", "red"))
    
    return all_tests_passed
def mrun_test_cors_configuration():
    pass
#if __name__ == "__main__":
    app_name = 'hmac-hash'
    env = 'dev'
    test_cors_configuration(app_name, env, ALLOWED_ORIGINS)
# '${method.request.header.Origin}' put this for API → Resources → /generate-hash → OPTIONS → Integration Response → method.response.header.Access-Control-Allow-Origin

def is_validation_setup(api_gateway_name, http_method='POST', verbose=False, print_method_config=False):
    """
    Check if API Gateway validation is set up.

    :param api_gateway_name: str, name of the API Gateway
    :param http_method: str, HTTP method to check
    :param verbose: bool, if True prints entire method configuration
    :return validation_exists: bool, True if validation is set up, False otherwise
    """
    api_client = boto3.client('apigateway')
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method, verbose=verbose)
    
    # Get method configuration
    method = api_client.get_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod='POST'
    )
    
    if print_method_config:
        print("Method configuration:")
        print(json.dumps(method, indent=2))
    
    validator_id = method.get('requestValidatorId', 'None')
    model_name = method.get('requestModels', {}).get('application/json', 'None')
    
    if verbose:
        print(f"\nAPI Gateway validation setup for {api_gateway_name}:")
        print(f"  Validator ID: {validator_id}")
        print(f"  Request Model: {model_name}")
    
    # Return True if both validator ID and model name exist and are not 'None'
    return validator_id != 'None' and model_name != 'None'
def mrun_is_validation_setup():
    pass
#if __name__ == "__main__":
    api_gateway_name = 'hmac-hash-prod'
    validation_exists = is_validation_setup(api_gateway_name, verbose=True)
    print(f"API Gateway is_validation_setup for {api_gateway_name}: {validation_exists}")
    
    # OR TO CHECK ALL LAMBDAS:
    # for app_name in all_app_names:
    #     validation_exists = is_validation_setup(app_name)
    #     print(f"API Gateway is_validation_setup for {app_name}: {validation_exists}")
def create_request_model(rest_api_id, model_name, schema, description=None, prompt_overwrite=False):
    """
    Create or update a request model in API Gateway for request validation.
    
    :param rest_api_id: ID of the REST API
    :param model_name: Name for the model (e.g., 'QRAGRoutingRequest')
    :param schema: JSON schema as a dictionary
    :param description: Optional description of the model
    :param prompt_overwrite: If True, prompts user when model exists; if False, skips update
    :return: Model ID if successful, None otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Check if model already exists
        try:
            existing_model = api_client.get_model(
                restApiId=rest_api_id,
                modelName=model_name
            )
            if prompt_overwrite:
                response = input(f"\nModel '{model_name}' already exists. Update it? (y/n): ")
                if response.lower() != 'y':
                    print("Skipping model update.")
                    return existing_model['id']
                    
                # Update existing model
                try:
                    api_client.update_model(
                        restApiId=rest_api_id,
                        modelName=model_name,
                        patchOperations=[
                            {
                                'op': 'replace',
                                'path': '/schema',
                                'value': json.dumps(schema)
                            },
                            {
                                'op': 'replace',
                                'path': '/description',
                                'value': description or f'Request validation model for {model_name}'
                            }
                        ]
                    )
                    print(f"Updated existing model '{model_name}'")
                    return existing_model['id']
                except ClientError as e:
                    print(f"Error updating existing model: {e}")
                    return None
            else:
                # Compare existing schema with new schema
                existing_schema = json.loads(existing_model.get('schema', '{}'))
                if existing_schema != schema:
                    print(f"Model '{model_name}' schema has changed, updating...")
                    api_client.update_model(
                        restApiId=rest_api_id,
                        modelName=model_name,
                        patchOperations=[
                            {
                                'op': 'replace',
                                'path': '/schema',
                                'value': json.dumps(schema)
                            }
                        ]
                    )
                    print(f"Updated existing model '{model_name}'")
                else:
                    print(f"Model '{model_name}' already exists with same schema, skipping update.")
                return existing_model['id']
                
        except ClientError as e:
            if not 'NotFoundException' in str(e):
                raise
        
        # Create new model if it doesn't exist
        response = api_client.create_model(
            restApiId=rest_api_id,
            name=model_name,
            description=description or f'Request validation model for {model_name}',
            contentType='application/json',
            schema=json.dumps(schema)
        )
        print(f"Created model '{model_name}' for API {rest_api_id}")
        return response['id']
        
    except ClientError as e:
        print(f"Error creating model: {e}")
        return None
def update_method_validation(rest_api_id, resource_id, http_method, model_name):
    """
    Update an API method to enable request validation with the specified model.
    
    :param rest_api_id: ID of the REST API
    :param resource_id: ID of the API resource
    :param http_method: HTTP method (e.g., 'POST')
    :param model_name: Name of the request model to use
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        # First try to get existing validator
        validator_id = None
        try:
            validators = api_client.get_request_validators(restApiId=rest_api_id)
            for validator in validators.get('items', []):
                if validator['validateRequestBody']:
                    validator_id = validator['id']
                    print(f"Found existing request validator: {validator['name']}")
                    break
        except ClientError:
            pass

        # Create validator only if none exists
        if not validator_id:
            try:
                validator = api_client.create_request_validator(
                    restApiId=rest_api_id,
                    name='validate-body',
                    validateRequestBody=True,
                    validateRequestParameters=False
                )
                validator_id = validator['id']
                print("Created new request validator")
            except ClientError as e:
                print(f"Error creating validator: {e}")
                return False

        # First, update the method to ensure Content-Type is set up
        try:
            api_client.update_method(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                patchOperations=[
                    {
                        'op': 'add',
                        'path': '/requestParameters/method.request.header.Content-Type',
                        'value': 'false'  # false means optional
                    }
                ]
            )
            print("Added Content-Type header parameter")
        except ClientError as e:
            if 'ConflictException' in str(e):
                print("Content-Type header parameter already exists")
            else:
                print(f"⚠️ Warning: Could not update Content-Type header: {e}")

        # Now update the method with validator and model
        api_client.update_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/requestValidatorId',
                    'value': validator_id
                },
                {
                    'op': 'add',
                    'path': '/requestModels/application~1json',
                    'value': model_name
                }
            ]
        )
        print(f"Enabled request validation for {http_method} method using model '{model_name}'")
        return True
    except ClientError as e:
        print(f"Error updating method validation: {e}")
        return False
def get_existing_model_id(rest_api_id, model_name):
    """
    Get the ID of an existing model in API Gateway.
    
    :param rest_api_id: ID of the REST API
    :param model_name: Name of the model to find
    :return: Model ID if found, None otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        existing_model = api_client.get_model(
            restApiId=rest_api_id,
            modelName=model_name
        )
        return existing_model['id']
    except ClientError as e:
        if 'NotFoundException' in str(e):
            return None
        print(f"Error getting model: {e}")
        return None
def mrun_get_existing_model_id():
    pass
#if __name__ == "__main__":
    api_gateway_name = 'hmac-hash-prod'
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name)
    model_name = 'SchemaHmacHashModel'
    model_id = get_existing_model_id(rest_api_id, model_name)
    print(f"API Gateway get_existing_model_id for {api_gateway_name} and model_name: {model_name} is: {model_id}")
def get_method_config(rest_api_id, resource_id, http_method='POST'):
    """
    Get current method configuration from API Gateway.
    
    :param rest_api_id: ID of the REST API
    :param resource_id: ID of the API resource
    :param http_method: HTTP method (e.g., 'POST')
    :return: Method configuration dictionary or None if error
    """
    api_client = boto3.client('apigateway')
    
    try:
        method = api_client.get_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod=http_method
        )
        
        # Return a simplified version with only the elements we care about
        # This makes comparison easier and more stable
        return {
            'requestValidatorId': method.get('requestValidatorId', None),
            'requestModels': method.get('requestModels', {}),
            'requestParameters': method.get('requestParameters', {})
        }
    except ClientError as e:
        print(f"Error getting method configuration: {e}")
        return None
def mrun_get_method_config():
    pass
#if __name__ == "__main__":
    rest_api_id, resource_id = get_api_gateway_and_resource_ids("hmac-hash-prod")
    print(get_method_config(rest_api_id, resource_id))
def get_api_gateway_active_deployment_info(api_gateway_name, stage_name):
    """
    Get validation model info for a specific deployed stage without changing anything.
    
    :param api_gateway_name: Name of the API Gateway
    :param stage_name: Stage name (e.g., 'dev', 'prod')
    :return: Dictionary with api_gateway_name, stage_name, datetime_of_retrieval, deployment_id, api_swagger_json
    """
    api_client = boto3.client('apigateway')
    
    # Get REST API ID using the existing function
    rest_api_id, _ = get_api_gateway_and_resource_ids(api_gateway_name, verbose=False)
    
    if not rest_api_id:
        print(f"API Gateway '{api_gateway_name}' not found")
        return None
    
    # Get stage to find deployment ID
    try:
        stage = api_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
        deployment_id = stage['deploymentId']
        
        # Export the API definition for this deployment
        export = api_client.get_export(
            restApiId=rest_api_id,
            stageName=stage_name,
            exportType='swagger',
            accepts='application/json'
        )
        
        # Parse the exported definition
        api_def = json.loads(export['body'].read().decode('utf-8'))
        
        return {
            'api_gateway_name': api_gateway_name,
            'stage_name': stage_name,
            'datetime_of_retrieval': get_current_datetime_filefriendly(),
            'deployment_id': deployment_id,
            'api_swagger_json': api_def
        }
    except Exception as e:
        print(f"Error getting deployment info: {str(e)}")
        return None
def save_api_gateway_active_deployment_info(deployment_info, pretty_print=False):
    """
    Save the active deployment info to a json file in the logs/aws_api_swagger_jsons directory.
    
    :param deployment_info: Dictionary with api_gateway_name, stage_name, datetime_of_retrieval, deployment_id, api_swagger_json
    :return: file path of the save
    """
    api_gateway_name = deployment_info['api_gateway_name']
    stage_name = deployment_info['stage_name']
    datetime_of_retrieval = deployment_info['datetime_of_retrieval']
    deployment_id = deployment_info['deployment_id']

    file_path = f"logs/aws_api_swagger_jsons/api_swagger_{api_gateway_name}_{datetime_of_retrieval}_{stage_name}_{deployment_id}.json"
    with open(file_path, "w") as f:
        json.dump(deployment_info, f, indent=4)
    if pretty_print:
        pretty_print_json_data(deployment_info, print_values=True)
    return file_path
def mrun_save_api_gateway_active_deployment_info():
    pass
#if __name__ == "__main__":
    api_gateway_name = "hmac-hash"
    stage_name = 'api'
    # api_gateway_name = "hmac-hash-prod"
    # stage_name = 'prod'
    deployment_info = get_api_gateway_active_deployment_info(api_gateway_name, stage_name)
    file_path = save_api_gateway_active_deployment_info(deployment_info, pretty_print=True)
    print(f"Ran save_api_gateway_active_deployment_info - return file: {file_path}")
def get_api_validation_model_name_and_schema(api_gateway_name, stage_name):
    """
    Get validation model info for a specific deployed stage without changing anything.
    Calls get_api_gateway_active_deployment_info and parses the swagger json to get the validation model name and schema.
    
    :param api_gateway_name: Name of the API Gateway
    :param stage_name: Stage name (e.g., 'dev', 'prod')
    :return: Dictionary with validation model name and schema
    """
    # Get deployment info
    deployment_info = get_api_gateway_active_deployment_info(api_gateway_name, stage_name)
    if not deployment_info:
        print(f"Error in get_api_validation_model_name_and_schemagetting deployment info for {api_gateway_name} for stage: {stage_name}")
        return None
    
    api_def = deployment_info['api_swagger_json']
    
    # Extract models and their schemas
    models = {}
    if 'definitions' in api_def:
        models = api_def['definitions']
    
    # Find which models are used by which methods
    paths = api_def.get('paths', {})
    method_models = {}
    
    for path, methods in paths.items():
        for method, config in methods.items():
            if method.lower() == 'post':
                if 'x-amazon-apigateway-request-validator' in config:
                    validator = config['x-amazon-apigateway-request-validator']
                    schema_ref = None
                    if 'requestBody' in config:
                        content = config['requestBody'].get('content', {})
                        if 'application/json' in content:
                            schema_ref = content['application/json'].get('schema', {}).get('$ref')
                    
                    if schema_ref and schema_ref.startswith('#/definitions/'):
                        model_name = schema_ref.split('/')[-1]
                        method_models[f"{path} {method}"] = {
                            'validator': validator,
                            'model_name': model_name,
                            'schema': models.get(model_name)
                        }
    
    return {
        'deployment_id': deployment_info['deployment_id'],
        'models': models,
        'method_models': method_models
    }
def mrun_get_validation_model_name_and_schema():
    pass
#if __name__ == "__main__":
    api_gateway_name = "hmac-hash"
    stage_name = 'api'
    deployed_model_info = get_api_validation_model_name_and_schema(api_gateway_name, stage_name)
    print(f"API Gateway get_validation_model_name_and_schema for {api_gateway_name} for stage: {stage_name}\n{deployed_model_info}")
    
    api_gateway_name = "hmac-hash-prod"
    stage_name = 'prod'
    deployed_model_info = get_api_validation_model_name_and_schema(api_gateway_name, stage_name)
    print(f"API Gateway get_validation_model_name_and_schema for {api_gateway_name} for stage: {stage_name}\n{deployed_model_info}")

class UnifiedLogger:
    """
    Unified logger for tracking deployment and validation operations.
    """
    def __init__(self, log_file_path=None):
        self.messages = []
        self.log_file_path = log_file_path
        self.changes_detected = False
        
    def log(self, message, is_change=False, print_to_console=True, add_to_log=True, prepend=False):
        """
        Log a message and optionally mark it as a change.
        
        :param message: str, message to log
        :param is_change: bool, whether this log indicates a change was made
        :param print_to_console: bool, whether to print to console (default: True)
        :param add_to_log: bool, whether to add to stored messages (default: True)
        :param prepend: bool, whether to add message to beginning of list (default: False)
        """
        # Print to console if requested
        if print_to_console:
            print(message)
            
        # Store in log object if requested
        if add_to_log:
            if prepend:
                self.messages.insert(0, message)
            else:
                self.messages.append(message)
            
        # Update changes flag if this is a change
        if is_change:
            self.changes_detected = True
            
    def add_header(self, header_text):
        """
        Add a header to the beginning of the log without printing to console.
        
        :param header_text: str, header text to add
        """
        self.log(header_text, print_to_console=False, prepend=True)
        
    def log_to_file_only(self, message, is_change=False, prepend=False):
        """
        Log a message only to the file, not to the console.
        
        :param message: str, message to log
        :param is_change: bool, whether this log indicates a change
        :param prepend: bool, whether to add to beginning of list
        """
        self.log(message, is_change=is_change, print_to_console=False, add_to_log=True, prepend=prepend)
        
    def log_to_console_only(self, message):
        """
        Print a message to the console without storing in the log.
        
        :param message: str, message to print
        """
        self.log(message, print_to_console=True, add_to_log=False)
    def get_summary(self):
        """
        Get a summary of all logged messages.
        
        :return: str, all messages joined with newlines
        """
        return "\n".join(self.messages)
        
    def save(self):
        """
        Write all logged messages to the specified file if log_file_path is set.
        """
        if not self.log_file_path:
            return
            
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            for msg in self.messages:
                f.write(f"{msg}\n")

def set_request_validation(api_gateway_name, stage, http_method='POST', force_deployment=False, skip_deployment=False, logger=None):
    """
    Set up request validation for an API Gateway endpoint if enabled.
    Only creates a new deployment if changes were made or forced and not explicitly skipped.
    To enable or disable validation for an API gateway, check the global APIS_VALIDATION_ENABLED dictionary.
    
    :param api_gateway_name: str, name of the API Gateway
    :param stage: str, deployment stage ('dev' or 'prod') 
    :param http_method: str, HTTP method to validate
    :param force_deployment: bool, if True forces a new deployment even if no changes
    :param skip_deployment: bool, if True skips creating a deployment even if changes are detected
    :param logger: UnifiedLogger, optional external logger to use instead of creating a new one
    :return: bool, True if successful, False otherwise
    """
    # Initialize logger or use provided one
    if logger is None:
        logger = UnifiedLogger()
    
    # Check if validation is enabled for this API
    validation_enabled = APIS_VALIDATION_ENABLED.get(api_gateway_name, False)
    if not validation_enabled:
        logger.log(f"Request validation is disabled for API: {api_gateway_name}")
        return True
        
    # Get schema for this API using the API_NAME_GLOBALS_MAPPING
    global_api_name = API_NAME_GLOBALS_MAPPING.get(api_gateway_name)
    print(f"DEBUG: Mapped global name: {global_api_name}")
    schema = None

    if global_api_name:
        global_schema_name = f"SCHEMA_{global_api_name}"
        schema = globals().get(global_schema_name)
        print(f"DEBUG: Attempting to find schema with name: {global_schema_name}")
        print(f"DEBUG: Schema found: {schema is not None}")

        # If schema not found and global_api_name ends with _PROD, try without _PROD
        if not schema and global_api_name.endswith("_PROD"):
            print(f"DEBUG: Normal Schema not found and global_api_name ends with _PROD: {global_api_name}")
            global_schema_name = f"{global_schema_name[:-5]}"  # Remove _PROD
            print(f"DEBUG: Trying _PROD schema name: {global_schema_name}")
            schema = globals().get(global_schema_name)
            print(f"DEBUG: _PROD schema found: {schema is not None}")

        if schema:
            logger.log(f"Using schema {global_schema_name} for {api_gateway_name}")
    
    if not schema:
        logger.log(f"No schema defined for API: {api_gateway_name}")
        print(f"DEBUG: Failed to find any schema for {api_gateway_name}")
        return False
    
    # Create model name based on global schema used
    camel_case_global_schema_name = ''.join(word.capitalize() for word in global_schema_name.split('_'))
    print(f"DEBUG: camel_case_global_schema_name: {camel_case_global_schema_name}")
    model_name = f"{camel_case_global_schema_name}Model"  # e.g., SchemaHmacHashModel and if separate prod schema, SchemaHmacHashProdModel
    
    logger.log(f"Using model name: {model_name} for stage: {stage}")
    
    # Get existing model ID and method configuration
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method)
    if not rest_api_id or not resource_id:
        logger.log(f"Failed to get API Gateway IDs for {api_gateway_name}")
        raise ValueError(f"Failed to get API Gateway IDs for {api_gateway_name}")
    old_model_id = get_existing_model_id(rest_api_id, model_name)
    method_before = get_method_config(rest_api_id, resource_id, http_method)
    
    # Create or update request model
    model_id = create_request_model(rest_api_id, model_name, schema)
    if not model_id:
        logger.log(f"Failed to create request model for {api_gateway_name}")
        raise ValueError(f"Failed to create request model for {api_gateway_name}")
    
    # Check if model changed
    if old_model_id != model_id:
        logger.log(f"Model changed from {old_model_id} to {model_id}", is_change=True)
    
    # Update method to use validation
    if not update_method_validation(rest_api_id, resource_id, http_method, model_name):
        return False
    
    # Check if method configuration changed
    method_after = get_method_config(rest_api_id, resource_id, http_method)
    if method_before != method_after:
        logger.log(f"Method configuration changed:", is_change=True)
        
        # Add detailed change tracking
        if method_before.get('requestValidatorId') != method_after.get('requestValidatorId'):
            logger.log(f"  - Validator ID: {method_before.get('requestValidatorId')} -> {method_after.get('requestValidatorId')}")
        
        if method_before.get('requestModels') != method_after.get('requestModels'):
            logger.log(f"  - Request Models: {method_before.get('requestModels')} -> {method_after.get('requestModels')}")
        
        # Check for changes in request parameters
        before_params = method_before.get('requestParameters', {})
        after_params = method_after.get('requestParameters', {})
        if before_params != after_params:
            logger.log(f"  - Request Parameters changed:")
            # Show added parameters
            for param, value in after_params.items():
                if param not in before_params:
                    logger.log(f"    - Added: {param} = {value}")
            # Show removed parameters
            for param in before_params:
                if param not in after_params:
                    logger.log(f"    - Removed: {param}")
            # Show changed parameters
            for param in before_params:
                if param in after_params and before_params[param] != after_params[param]:
                    logger.log(f"    - Changed: {param}: {before_params[param]} -> {after_params[param]}")
    
    # Create deployment if changes were made or forced and not skipping deployment
    if (logger.changes_detected or force_deployment) and not skip_deployment:
        action = "Forced deployment" if force_deployment and not logger.changes_detected else "Changes detected"
        logger.log(f"{action}, creating new deployment for {api_gateway_name} stage {stage}")
        if not create_api_gateway_deployment(rest_api_id, stage):
            return False
    elif skip_deployment and (logger.changes_detected or force_deployment):
        logger.log(f"Changes detected, but skipping deployment as requested")
    else:
        logger.log(f"No changes detected, skipping deployment for {api_gateway_name}")
    
    logger.log(f"Successfully completed validation setup for {api_gateway_name}")
    
    # Write a detailed log to a file for reference
    if logger is None:
        # Only create a log file if we created the logger internally
        log_dir = "logs/aws_api_swagger_jsons"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = get_current_datetime_filefriendly()
        log_file = f"{log_dir}/api_validation_{api_gateway_name}_{stage}_{timestamp}.log"
        try:
            with open(log_file, 'w') as f:
                f.write(f"API Gateway Validation Setup: {api_gateway_name} - {stage}\n")
                f.write(f"Timestamp: {timestamp}\n\n")
                f.write(logger.get_summary())
            print(f"Detailed log written to {log_file}")
        except Exception as e:
            print(f"⚠️ Warning: Could not write log file: {e}")
    
    return True
def mrun_set_request_validation():
    pass
#if __name__ == "__main__":
    # api_gateway_name = cur_app_name
    # stage = "api"
    api_gateway_name = cur_app_name + "-prod"
    stage = "prod"
    # is_validation_setup(api_gateway_name)
    logger = UnifiedLogger()
    setup_result = set_request_validation(api_gateway_name, stage, force_deployment=True, logger=logger)
    
    # Print summary of all logged messages
    print("\n=== Validation Setup Summary ===")
    print(logger.get_summary())
    print("===============================\n")
    
    if setup_result:
        user_continue_response = input("\n*** WAIT 30 SECONDS FOR CHANGE TO TAKE EFFECT *** - Then Press any key to continue and RUN REQUEST TESTS or 'x' to exit...").strip().lower()
        if user_continue_response != 'x':
            # Use the same JWT logic as mrun_test_lambda_requests
            jwt_token = None
            if LAMBDA_JWT_REQUIRED.get(cur_app_name, False):
                jwt_token = JWT_TEST
                
            test_lambda_requests(
                cur_app_name, 
                direct_lambda=True, 
                with_gateway=True, 
                jwt_token=jwt_token
            )

# aws apigateway delete-model --rest-api-id [API-GATEWAY-ID] --model-name hmachashModel


### PROD STAGE
PROMOTE_TO_PROD_ZIP_PATH = "web-shared/aws_chalice/qrag-llm/.chalice/deployments/prod-init-promote_2025-02-27_070200_b043a92fd1d38a85e9db0e99138d3633-python3.11.zip"
def rename_api_gateway(rest_api_id, new_name):
    """
    Rename an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :param new_name: str, New name for the API Gateway
    """
    api_client = boto3.client('apigateway')
    api_client.update_rest_api(
        restApiId=rest_api_id,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/name',
                'value': new_name
            }
        ]
    )
    
    # Lookup the name after rename to confirm the change
    response = api_client.get_rest_api(restApiId=rest_api_id)
    current_name = response.get('name', 'unknown')
    print(f"API Gateway renamed: ID {rest_api_id} is now named '{current_name}'")
def mrun_rename_api_gateway():
    pass
#if __name__ == "__main__":
    rename_api_gateway("[API-GATEWAY-ID]", "qrag-llm-prod")
def rename_api_gateway_stage(rest_api_id, old_stage_name, new_stage_name):
    """
    Rename a stage of an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :param old_stage_name: str, Current name of the stage
    :param new_stage_name: str, New name for the stage
    :return: bool, True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Get the current stage to copy its configuration
        response = api_client.get_stage(
            restApiId=rest_api_id,
            stageName=old_stage_name
        )
        
        # Extract the current deployment ID and other settings
        deployment_id = response.get('deploymentId')
        
        # Build parameters for create_stage
        params = {
            'restApiId': rest_api_id,
            'stageName': new_stage_name,
            'deploymentId': deployment_id,
            'description': response.get('description', f'Renamed from {old_stage_name}'),
            'variables': response.get('variables', {})
        }
        
        # Only include cache parameters if caching is enabled
        if response.get('cacheClusterEnabled', False):
            params['cacheClusterEnabled'] = True
            params['cacheClusterSize'] = response.get('cacheClusterSize', '0.5')
        else:
            params['cacheClusterEnabled'] = False
        
        # Create a new stage with the same deployment ID and settings
        api_client.create_stage(**params)
        
        # Delete the old stage
        api_client.delete_stage(
            restApiId=rest_api_id,
            stageName=old_stage_name
        )
        
        print(f"API Gateway stage renamed: '{old_stage_name}' to '{new_stage_name}' for API {rest_api_id}")
        return True
        
    except Exception as e:
        print(f"Error renaming API Gateway stage: {e}")
        return False
def mrun_rename_api_gateway_stage():
    pass
#if __name__ == "__main__":
    rename_api_gateway_stage("[API-GATEWAY-ID]", "api", "prod")
def copy_lambda_dev_role_to_prod(app_name):
    """
    Create a copy of a Lambda dev role, naming it with a prod suffix.
    
    :param app_name: str, application name (e.g., 'hmac-hash').
    :return success: bool, True if successful, False otherwise.
    """
    iam = boto3.client('iam')
    lambda_client = boto3.client('lambda')
    
    # Get the Lambda function name
    dev_function_name = f"{app_name}-dev"
    
    print(f"Copying role from dev to prod for: {app_name}")
    print(f"  Source dev function: {dev_function_name}")
    
    try:
        # Discover the role assigned to dev function
        try:
            dev_function = lambda_client.get_function(FunctionName=dev_function_name)
            dev_role_arn = dev_function['Configuration']['Role']
            dev_role_name = dev_role_arn.split('/')[-1]
            print(f"  ✅ Discovered IAM role for {dev_function_name}: {dev_role_name}")
        except ClientError as e:
            print(f"  ❌ Error: Dev function {dev_function_name} not found: {str(e)}")
            return False
        
        # Define the prod role name based on the dev role pattern
        prod_role_name = f"{app_name}-prod"
        print(f"  Target prod role to create: {prod_role_name}")
        
        # Check if prod role already exists
        try:
            iam.get_role(RoleName=prod_role_name)
            print(f"  ⚠️ Role {prod_role_name} already exists. Will update policies.")
        except ClientError:
            # Role doesn't exist, we'll create it
            pass
        
        # Get all inline policies from dev role
        inline_policies = []
        try:
            list_policies_response = iam.list_role_policies(RoleName=dev_role_name)
            for policy_name in list_policies_response['PolicyNames']:
                # Skip the app_name-dev policy
                if policy_name == f"{app_name}-dev":
                    print(f"  ⚠️ Skipping policy: {policy_name} (dev-specific policy)")
                    continue
                    
                policy_response = iam.get_role_policy(
                    RoleName=dev_role_name,
                    PolicyName=policy_name
                )
                inline_policies.append({
                    'PolicyName': policy_name,
                    'PolicyDocument': policy_response['PolicyDocument']
                })
            print(f"  Found {len(inline_policies)} inline policies to copy")
        except ClientError as e:
            print(f"  ❌ Error getting inline policies: {str(e)}")
            return False
        
        # Get all attached managed policies
        managed_policies = []
        try:
            attached_policies_response = iam.list_attached_role_policies(RoleName=dev_role_name)
            for policy in attached_policies_response['AttachedPolicies']:
                managed_policies.append(policy['PolicyArn'])
            print(f"  Found {len(managed_policies)} managed policies")
        except ClientError as e:
            print(f"  ❌ Error getting managed policies: {str(e)}")
            return False
        
        # Get assume role policy document
        try:
            role_response = iam.get_role(RoleName=dev_role_name)
            assume_role_policy = role_response['Role']['AssumeRolePolicyDocument']
            print(f"  Retrieved assume role policy document")
        except ClientError as e:
            print(f"  ❌ Error getting assume role policy: {str(e)}")
            return False
        
        # Create the prod role
        try:
            try:
                iam.get_role(RoleName=prod_role_name)
                print(f"  Updating existing role: {prod_role_name}")
                iam.update_assume_role_policy(
                    RoleName=prod_role_name,
                    PolicyDocument=json.dumps(assume_role_policy)
                )
            except ClientError:
                print(f"  Creating new role: {prod_role_name}")
                create_response = iam.create_role(
                    RoleName=prod_role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                    Description=f"Prod role for {app_name} Lambda function"
                )
            
            # Get the new/updated role ARN
            role_response = iam.get_role(RoleName=prod_role_name)
            prod_role_arn = role_response['Role']['Arn']
            print(f"  ✅ Role ARN: {prod_role_arn}")
        except ClientError as e:
            print(f"  ❌ Error creating/updating role: {str(e)}")
            return False
        
        # Wait for role creation/update to propagate
        print("  Waiting for role changes to propagate...")
        sleep(5)
        
        # Attach all managed policies to the prod role
        for policy_arn in managed_policies:
            try:
                iam.attach_role_policy(
                    RoleName=prod_role_name,
                    PolicyArn=policy_arn
                )
                print(f"  ✅ Attached managed policy: {policy_arn.split('/')[-1]}")
            except ClientError as e:
                print(f"  ⚠️ Warning attaching policy {policy_arn}: {str(e)}")
        
        # Add all inline policies to the prod role
        for policy in inline_policies:
            try:
                iam.put_role_policy(
                    RoleName=prod_role_name,
                    PolicyName=policy['PolicyName'],
                    PolicyDocument=json.dumps(policy['PolicyDocument'])
                )
                print(f"  ✅ Added inline policy: {policy['PolicyName']}")
            except ClientError as e:
                print(f"  ⚠️ Warning adding policy {policy['PolicyName']}: {str(e)}")
        
        print(f"\n✅ Successfully created prod role {prod_role_name} copied from {dev_role_name}")
        print(f"  Prod role ARN: {prod_role_arn}")
        print("  This role is automatically assigned to your Lambda function when the -prod lambda is created.")
        return True
        
    except Exception as e:
        print(f"  ❌ Unexpected error: {str(e)}")
        return False
def mrun_copy_lambda_dev_role_to_prod():
    pass
#if __name__ == "__main__":
    copy_lambda_dev_role_to_prod(cur_app_name)
'''
Copying role from dev to prod for: send-email
  Source dev function: send-email-dev
  ✅ Discovered IAM role for send-email-dev: send-email-dev
  Target prod role to create: send-email-prod
  ⚠️ Role send-email-prod already exists. Will update policies.
  ⚠️ Skipping policy: send-email-dev (dev-specific policy)
  Found 0 inline policies to copy
  Found 2 managed policies
  Retrieved assume role policy document
  Updating existing role: send-email-prod
  ✅ Role ARN: arn:aws:iam::[AWS-ACCOUNT-ID]:role/send-email-prod
  Waiting for role changes to propagate...
  ✅ Attached managed policy: jwt-secret-access-policy
  ✅ Attached managed policy: LambdaSESSendEmailPolicy

✅ Successfully created prod role send-email-prod copied from send-email-dev
  Prod role ARN: arn:aws:iam::[AWS-ACCOUNT-ID]:role/send-email-prod
  This role is automatically assigned to your Lambda function when the -prod lambda is created.
  '''

def create_shared_role_for_lambda(app_name, env='dev', configure_api_gateway=True):  # DEPRECATED
    """
    Create a shared IAM role for a specific Lambda function's dev and prod versions.
    
    This function takes a dev Lambda, copies its permissions to a new role without
    the -dev/-prod suffix, and updates both dev and prod Lambdas to use this role.
    It also configures API Gateway permissions with stage-specific controls.
    
    :param app_name: str, application name (e.g., 'hmac-hash').
    :param env: str, deployment environment ('dev' or 'prod').
    :param configure_api_gateway: bool, whether to add API Gateway invoke permissions.
    :return success: bool, True if successful, False otherwise.
    """
    iam = boto3.client('iam')
    lambda_client = boto3.client('lambda')
    
    # Get the Lambda function names
    dev_function_name = f"{app_name}-dev"
    prod_function_name = f"{app_name}-prod"
    new_role_name = f"{app_name}-role"
    
    print(f"Creating shared role for: {app_name}")
    print(f"  Dev function: {dev_function_name}")
    print(f"  Prod function: {prod_function_name}")
    print(f"  Target role: {new_role_name}")
    
    try:
        # -----------------------------------------------------------------------------
        # 1) VERIFY API GATEWAY - Ensure no duplicates exist
        # -----------------------------------------------------------------------------
        # First check if we should configure API Gateway
        api_id = None
        resource_id = None
        
        if configure_api_gateway:
            try:
                from core.aws import get_api_gateway_and_resource_ids
                api_id, resource_id = get_api_gateway_and_resource_ids(
                    api_gateway_name=app_name,
                    http_method='POST',
                    verbose=True
                )
                
                if not api_id or not resource_id:
                    print(f"  ⚠️ Warning: Could not find API Gateway for {app_name}")
                    print(f"  API Gateway permissions will not be configured")
                    configure_api_gateway = False
                else:
                    print(f"  ✅ Found API Gateway for {app_name}: {api_id}")
            except ValueError as e:
                print(f"  ❌ Error: {str(e)}")
                print(f"  You must resolve duplicate API Gateway issues before configuring permissions")
                configure_api_gateway = False
            except Exception as e:
                print(f"  ⚠️ Error checking API Gateway: {str(e)}")
                configure_api_gateway = False
        
        # -----------------------------------------------------------------------------
        # 2) CHECK DEV FUNCTION - Validate it exists
        # -----------------------------------------------------------------------------
        try:
            dev_function = lambda_client.get_function(FunctionName=dev_function_name)
            dev_role_arn = dev_function['Configuration']['Role']
            dev_role_name = dev_role_arn.split('/')[-1]
            print(f"  Found dev function with role: {dev_role_name}")
        except ClientError as e:
            print(f"  ❌ Error: Dev function {dev_function_name} not found: {str(e)}")
            return False
        
        # -----------------------------------------------------------------------------
        # 3) CHECK PROD FUNCTION - Validate if it exists
        # -----------------------------------------------------------------------------
        prod_function_exists = True
        try:
            prod_function = lambda_client.get_function(FunctionName=prod_function_name)
            prod_role_arn = prod_function['Configuration']['Role']
            print(f"  Found prod function with role: {prod_role_arn.split('/')[-1]}")
        except ClientError:
            print(f"  ℹ️ Note: Prod function {prod_function_name} not found")
            prod_function_exists = False
        
        # -----------------------------------------------------------------------------
        # 4) GET POLICIES FROM DEV ROLE - Copy inline and managed policies
        # -----------------------------------------------------------------------------
        # Get all inline policies
        inline_policies = []
        try:
            list_policies_response = iam.list_role_policies(RoleName=dev_role_name)
            for policy_name in list_policies_response['PolicyNames']:
                policy_response = iam.get_role_policy(
                    RoleName=dev_role_name,
                    PolicyName=policy_name
                )
                inline_policies.append({
                    'PolicyName': policy_name,
                    'PolicyDocument': policy_response['PolicyDocument']
                })
            print(f"  Found {len(inline_policies)} inline policies")
        except ClientError as e:
            print(f"  ❌ Error getting inline policies: {str(e)}")
            return False
        
        # Get all attached managed policies
        managed_policies = []
        try:
            attached_policies_response = iam.list_attached_role_policies(RoleName=dev_role_name)
            for policy in attached_policies_response['AttachedPolicies']:
                managed_policies.append(policy['PolicyArn'])
            print(f"  Found {len(managed_policies)} managed policies")
        except ClientError as e:
            print(f"  ❌ Error getting managed policies: {str(e)}")
            return False
        
        # Get assume role policy document
        try:
            role_response = iam.get_role(RoleName=dev_role_name)
            assume_role_policy = role_response['Role']['AssumeRolePolicyDocument']
            print(f"  Retrieved assume role policy document")
        except ClientError as e:
            print(f"  ❌ Error getting assume role policy: {str(e)}")
            return False
        
        # -----------------------------------------------------------------------------
        # 5) CREATE OR UPDATE THE SHARED ROLE
        # -----------------------------------------------------------------------------
        role_exists = False
        try:
            iam.get_role(RoleName=new_role_name)
            print(f"  Role {new_role_name} already exists. Will update policies.")
            role_exists = True
        except ClientError:
            role_exists = False
        
        # Create the new role or update the existing one
        if not role_exists:
            try:
                print(f"  Creating new role: {new_role_name}")
                create_response = iam.create_role(
                    RoleName=new_role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                    Description=f"Shared role for {app_name} Lambda functions"
                )
                new_role_arn = create_response['Role']['Arn']
                print(f"  ✅ Created new role with ARN: {new_role_arn}")
            except ClientError as e:
                print(f"  ❌ Error creating role: {str(e)}")
                return False
        else:
            try:
                print(f"  Updating assume role policy for: {new_role_name}")
                iam.update_assume_role_policy(
                    RoleName=new_role_name,
                    PolicyDocument=json.dumps(assume_role_policy)
                )
                role_response = iam.get_role(RoleName=new_role_name)
                new_role_arn = role_response['Role']['Arn']
                print(f"  ✅ Updated existing role with ARN: {new_role_arn}")
            except ClientError as e:
                print(f"  ❌ Error updating role: {str(e)}")
                return False
        
        # Wait for role creation/update to propagate
        print("  Waiting for role changes to propagate...")
        sleep(5)
        
        # -----------------------------------------------------------------------------
        # 6) APPLY POLICIES TO THE SHARED ROLE
        # -----------------------------------------------------------------------------
        # Get existing policies on the new role
        existing_policies = []
        try:
            if role_exists:
                attached_policies_response = iam.list_attached_role_policies(RoleName=new_role_name)
                existing_policies = [p['PolicyArn'] for p in attached_policies_response.get('AttachedPolicies', [])]
                print(f"  Found {len(existing_policies)} policies already attached to role")
        except ClientError as e:
            print(f"  ⚠️ Warning checking existing policies: {str(e)}")
        
        # Attach all managed policies
        for policy_arn in managed_policies:
            try:
                # Skip if policy is already attached
                if policy_arn in existing_policies:
                    print(f"  Policy {policy_arn.split('/')[-1]} already attached")
                    continue
                
                iam.attach_role_policy(
                    RoleName=new_role_name,
                    PolicyArn=policy_arn
                )
                print(f"  ✅ Attached managed policy: {policy_arn.split('/')[-1]}")
            except ClientError as e:
                print(f"  ⚠️ Warning attaching policy {policy_arn}: {str(e)}")
        
        # Add all inline policies
        for policy in inline_policies:
            try:
                iam.put_role_policy(
                    RoleName=new_role_name,
                    PolicyName=policy['PolicyName'],
                    PolicyDocument=json.dumps(policy['PolicyDocument'])
                )
                print(f"  ✅ Added inline policy: {policy['PolicyName']}")
            except ClientError as e:
                print(f"  ⚠️ Warning adding policy {policy['PolicyName']}: {str(e)}")
        
        # Short pause to let AWS propagate the role changes
        print("  Waiting for role changes to propagate...")
        sleep(5)
        
        # -----------------------------------------------------------------------------
        # 7) UPDATE LAMBDA FUNCTIONS TO USE THE SHARED ROLE
        # -----------------------------------------------------------------------------
        # Update the dev function
        try:
            print(f"  Updating dev function {dev_function_name} to use the shared role")
            lambda_client.update_function_configuration(
                FunctionName=dev_function_name,
                Role=new_role_arn
            )
            print(f"  ✅ Updated dev function to use shared role")
            # Allow time for Lambda configuration update to propagate
            sleep(2)
        except ClientError as e:
            print(f"  ❌ Error updating dev function: {str(e)}")
            return False
        
        # Update the prod function if it exists
        if prod_function_exists:
            try:
                print(f"  Updating prod function {prod_function_name} to use the shared role")
                lambda_client.update_function_configuration(
                    FunctionName=prod_function_name,
                    Role=new_role_arn
                )
                print(f"  ✅ Updated prod function to use shared role")
                # Allow time for Lambda configuration update to propagate
                sleep(2)
            except ClientError as e:
                print(f"  ❌ Error updating prod function: {str(e)}")
                return False
        
        # -----------------------------------------------------------------------------
        # 8) CONFIGURE API GATEWAY PERMISSIONS WITH STAGE ISOLATION
        # -----------------------------------------------------------------------------
        if configure_api_gateway and api_id:
            print("\nConfiguring API Gateway permissions for Lambda functions...")
            
            # Get account ID and region for ARN formation
            account_id = boto3.client('sts').get_caller_identity().get('Account')
            region = boto3.session.Session().region_name
            
            # Find the resource path 
            api_client = boto3.client('apigateway')
            resources = api_client.get_resources(restApiId=api_id)
            resource_path = ""
            for resource in resources['items']:
                if resource.get('id') == resource_id:
                    resource_path = resource.get('path', '')
                    break
            
            # Create stage-specific ARNs for better security isolation
            dev_stage_arn = f"arn:aws:execute-api:{region}:{account_id}:{api_id}/dev/POST{resource_path}"
            prod_stage_arn = f"arn:aws:execute-api:{region}:{account_id}:{api_id}/prod/POST{resource_path}"
            
            # Generate statement IDs based on function name
            dev_statement_id = f"{app_name}-dev-allow-apigateway"
            prod_statement_id = f"{app_name}-prod-allow-apigateway"
            
            # Add permission for dev function (only allow dev stage to invoke it)
            try:
                print(f"  Adding permission for {dev_function_name} (dev stage only)")
                lambda_client.add_permission(
                    FunctionName=dev_function_name,
                    StatementId=dev_statement_id,
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=dev_stage_arn
                )
                print(f"  ✅ Added API Gateway invoke permission for {dev_function_name} (dev stage only)")
            except ClientError as e:
                if 'ResourceConflictException' in str(e):
                    print(f"  ℹ️ Permission already exists for {dev_function_name}")
                else:
                    print(f"  ⚠️ Error adding permission for {dev_function_name}: {str(e)}")
            
            # Add permission for prod function if it exists (only allow prod stage to invoke it)
            if prod_function_exists:
                try:
                    print(f"  Adding permission for {prod_function_name} (prod stage only)")
                    lambda_client.add_permission(
                        FunctionName=prod_function_name,
                        StatementId=prod_statement_id,
                        Action='lambda:InvokeFunction',
                        Principal='apigateway.amazonaws.com',
                        SourceArn=prod_stage_arn
                    )
                    print(f"  ✅ Added API Gateway invoke permission for {prod_function_name} (prod stage only)")
                except ClientError as e:
                    if 'ResourceConflictException' in str(e):
                        print(f"  ℹ️ Permission already exists for {prod_function_name}")
                    else:
                        print(f"  ⚠️ Error adding permission for {prod_function_name}: {str(e)}")
            
            print("\n  ℹ️ Don't forget to set up stage variables in API Gateway:")
            print("    1. Go to Stages → Select stage → Stage Variables")
            print("    2. Add variable 'LambdaFunctionName'")
            print(f"    3. Set to '{dev_function_name}' for dev stage")
            print(f"    4. Set to '{prod_function_name}' for prod stage")
            print("    5. Update Lambda Integration to: ${stageVariables.LambdaFunctionName}")
        
        print(f"\n✅ Successfully created shared role {new_role_name} for {app_name}")
        print("Don't forget to do these followup steps:")
        print("1. Check permission policies for the new -role role compared to the old -dev role")
        print("2. Check that each Lambda function is using the new shared role")
        print("3. Update the chalice config.json file with manage_iam_role: false and iam_role_arn: <new_role_arn>")
        return True
    
    except Exception as e:
        print(f"  ❌ Unexpected error: {str(e)}")
        return False
def mrun_create_shared_role_for_lambda():
    pass
#if __name__ == "__main__":
    app_name = 'hmac-hash'  # Default Lambda to process
    create_shared_role_for_lambda(app_name)

### API STATE REPORT
def get_api_stage_active_deployment_id(rest_api_id, stage_name):
    """
    Get the active deployment for a specific stage of an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :param stage_name: str, name of the stage
    :return: tuple (deployment_id, deployment_date, deployment_description)
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Get stage details to find the active deployment ID
        stage = api_client.get_stage(
            restApiId=rest_api_id,
            stageName=stage_name
        )
        
        deployment_id = stage.get('deploymentId', None)
        if not deployment_id:
            return None, None, None
            
        # Get deployment details
        deployment = api_client.get_deployment(
            restApiId=rest_api_id,
            deploymentId=deployment_id
        )
        
        # Extract date and description
        deployment_date = deployment.get('createdDate', None)
        deployment_description = deployment.get('description', 'No description')
        
        return deployment_id, deployment_date, deployment_description
        
    except Exception as e:
        print(f"Error getting active deployment ID: {str(e)}")
        return None, None, None
def mrun_get_api_stage_active_deployment_id():
    pass
#if __name__ == "__main__":
    rest_api_id, _ = get_api_gateway_and_resource_ids('hmac-hash')
    stage_name = 'prod'
    print(get_api_stage_active_deployment_id(rest_api_id, stage_name))
def get_api_validation_models(rest_api_id):
    """
    Get all validation models defined for an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :return: list of tuples, each containing (model_name, model_schema, content_type)
    """
    api_client = boto3.client('apigateway')
    models_info = []
    method_model_associations = {}  # To track which methods use which models
    
    try:
        # Get all models for this API
        models_response = api_client.get_models(restApiId=rest_api_id)
        all_models = {}
        
        # First, collect all available models
        for model in models_response.get('items', []):
            model_name = model.get('name', '')
            if model_name and model_name != 'Empty':
                try:
                    # Get full model details including schema
                    model_detail = api_client.get_model(
                        restApiId=rest_api_id,
                        modelName=model_name
                    )
                    
                    schema = model_detail.get('schema')
                    if schema:
                        # Parse schema if it's a string
                        if isinstance(schema, str):
                            try:
                                schema_dict = json.loads(schema)
                            except json.JSONDecodeError:
                                schema_dict = schema  # Keep as string if parsing fails
                        else:
                            schema_dict = schema
                        
                        all_models[model_name] = {
                            'schema': schema_dict,
                            'content_type': None  # Will be updated if found in a method
                        }
                except Exception as e:
                    print(f"Error getting model details for {model_name}: {str(e)}")
        
        # Now check which models are actually used in methods
        try:
            resources = api_client.get_resources(restApiId=rest_api_id)
            
            for resource in resources.get('items', []):
                if 'resourceMethods' not in resource:
                    continue
                    
                resource_id = resource['id']
                resource_path = resource.get('path', '')
                
                for method_name, method_info in resource['resourceMethods'].items():
                    try:
                        # Get method details
                        method_details = api_client.get_method(
                            restApiId=rest_api_id,
                            resourceId=resource_id,
                            httpMethod=method_name
                        )
                        
                        # Check request models defined for this method
                        request_models = method_details.get('requestModels', {})
                        for content_type, model_name in request_models.items():
                            if model_name and model_name != 'Empty' and model_name in all_models:
                                # Update the content_type if not already set
                                if not all_models[model_name]['content_type']:
                                    all_models[model_name]['content_type'] = content_type
                                
                                # Track which methods use this model
                                if model_name not in method_model_associations:
                                    method_model_associations[model_name] = []
                                
                                method_model_associations[model_name].append(f"{method_name} {resource_path}")
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"Error checking method associations: {str(e)}")
        
        # Convert to the required format
        for model_name, model_info in all_models.items():
            # Default content_type to 'application/json' if not found in methods
            content_type = model_info['content_type'] or 'application/json'
            
            # Add usage information if available
            used_by = method_model_associations.get(model_name, [])
            
            models_info.append((model_name, model_info['schema'], content_type, used_by))
        
        return models_info
        
    except Exception as e:
        print(f"Error getting validation models: {str(e)}")
        return []
STANDARD_ACCESS_LOG_SCHEMA_122024 = {
    "requestId": "$context.requestId",
    "ip": "$context.identity.sourceIp",
    "userAgent": "$context.identity.userAgent",
    "requestTimeUtc": "$context.requestTime",
    "requestTimeEpoch": "$context.requestTimeEpoch", 
    "httpMethod": "$context.httpMethod",
    "resourcePath": "$context.resourcePath",
    "status": "$context.status",
    "responseLength": "$context.responseLength",
    "errorMessage": "$context.error.messageString",
    "integrationError": "$context.integrationErrorMessage",
    "responseBodySnippet": "$context.integration.response.body"
}
def get_cloudwatch_log_groups_for_api(api_gateway_name, stage_name):
    """
    Get CloudWatch log groups associated with an API Gateway and its Lambda function.
    
    :param api_gateway_name: str, name of the API Gateway
    :param stage_name: str, name of the stage
    :return: list of log group names
    """
    # Use the correct service name for CloudWatch Logs
    logs_client = boto3.client('logs')
    log_groups = []
    
    rest_api_id, _ = get_api_gateway_and_resource_ids(api_gateway_name)

    try:
        # More specific log group patterns for API Gateway
        api_access_log_prefix = f"API-Gateway-Access-Logs_{api_gateway_name}_"
        # For execution logs, keep the original pattern as it includes the specific API ID
        api_execution_log_prefix = f"API-Gateway-Execution-Logs_{rest_api_id}"
        
        # Get lambda name variations to check
        lambda_names = [
            f"{api_gateway_name}",
            f"{api_gateway_name}-{stage_name}",
            f"{api_gateway_name}-dev"
        ]
        
        # Get all log groups with pagination
        paginator = logs_client.get_paginator('describe_log_groups')
        
        for page in paginator.paginate():
            for log_group in page.get('logGroups', []):
                log_group_name = log_group.get('logGroupName', '')
                
                # Check for API Gateway access logs with more specific matching
                if api_access_log_prefix in log_group_name:
                    # Additional check to ensure we don't match "hmac-hash-prod" when looking for "hmac-hash"
                    if api_gateway_name != "hmac-hash" or "hmac-hash-prod" not in log_group_name:
                        log_groups.append(log_group_name)
                
                # Check for API Gateway execution logs with stage
                if api_execution_log_prefix in log_group_name and f"/{stage_name}" in log_group_name:
                    log_groups.append(log_group_name)
                
                # Check for Lambda logs with various name patterns
                for lambda_name in lambda_names:
                    if log_group_name == f"/aws/lambda/{lambda_name}":
                        log_groups.append(log_group_name)
        
        return log_groups
    
    except Exception as e:
        print(f"Error getting CloudWatch log groups: {str(e)}")
        return []
def mtest_get_cloudwatch_log_groups_for_api():
    pass
#if __name__ == "__main__":
    print(get_cloudwatch_log_groups_for_api("hmac-hash", "api"))
    print(get_cloudwatch_log_groups_for_api("hmac-hash-prod", "prod"))
def get_api_stage_current_config(rest_api_id, stage_name):
    """
    Get information about an API Gateway stage, including current working configuration
    and active deployment details.
    
    IMPORTANT: This function returns the current working configuration, which may include
    undeployed changes that are not yet live in the active deployment.
    
    :param rest_api_id: str, ID of the REST API
    :param stage_name: str, name of the stage
    :return: dict with stage and configuration information
    """
    api_client = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    waf_client = boto3.client('wafv2')
    
    result = {
        'rest_api_id': rest_api_id,  # Basic identifier (neutral)
        'stage_name': stage_name,  # Basic identifier (neutral)
        'deployment': {},  # DEPLOYED - Contains active deployment ID, date, and description of what's currently live
        'lambda': {},  # MIXED - Contains function name and config, but integrations may include undeployed changes
        'api_keys': {},  # UNDEPLOYED - Based on current method configurations which may not be deployed
        'waf': {},  # DEPLOYED - Shows current WAF association with the API
        # Validation models removed - now handled separately
        'logging': {},  # UNDEPLOYED - Based on current stage settings which may not be deployed
        'integration': {},  # UNDEPLOYED - Based on current integration settings which may not be deployed
        'resources': [],  # UNDEPLOYED - Lists all current resources/methods which may include undeployed changes
        'deployment_history': []  # Empty in this function (not populated)
    }
    
    try:
        # Get active deployment information
        deployment_id, deployment_date, deployment_description = get_api_stage_active_deployment_id(rest_api_id, stage_name)
        
        if not deployment_id:
            result['deployment'] = {
                'id': None,
                'date': None,
                'description': 'No active deployment'
            }
            return result
            
        # Format deployment date
        formatted_date = None
        if deployment_date:
            formatted_date = deployment_date.strftime('%Y-%m-%d %H:%M')
            # Add timezone info
            formatted_date += f" ({datetime.now().astimezone().strftime('UTC%z')})"
            
        result['deployment'] = {
            'id': deployment_id,
            'date': formatted_date,
            'description': deployment_description
        }
        
        # Get stage details
        stage = api_client.get_stage(
            restApiId=rest_api_id,
            stageName=stage_name
        )
        
        # Get resources and their methods to find Lambda integrations
        try:
            resources = api_client.get_resources(restApiId=rest_api_id)
            lambda_integrations = []
            
            # Iterate through all resources and methods to find Lambda integrations
            for resource in resources.get('items', []):
                if 'resourceMethods' not in resource:
                    continue
                    
                for method_name, method_details in resource['resourceMethods'].items():
                    try:
                        # Get the integration for this method
                        integration = api_client.get_integration(
                            restApiId=rest_api_id,
                            resourceId=resource['id'],
                            httpMethod=method_name
                        )
                        
                        # Check if this is a Lambda integration
                        if integration.get('type') == 'AWS' or integration.get('type') == 'AWS_PROXY':
                            integration_uri = integration.get('uri', '')
                            
                            # Extract Lambda function name from the URI
                            # URI format: arn:aws:apigateway:REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:REGION:ACCOUNT:function:FUNCTION_NAME[:ALIAS or :VERSION]/invocations
                            if 'lambda' in integration_uri and ':function:' in integration_uri:
                                uri_parts = integration_uri.split(':function:')
                                if len(uri_parts) == 2:
                                    # Get the function name part (may include alias/version)
                                    function_part = uri_parts[1].split('/invocations')[0]
                                    
                                    # Check if there's an alias or version
                                    if ':' in function_part:
                                        base_name, qualifier = function_part.rsplit(':', 1)
                                        lambda_integrations.append({
                                            'function_name': base_name,
                                            'qualifier': qualifier,  # This will be the alias or version
                                            'resource_path': resource.get('path'),
                                            'method': method_name
                                        })
                                    else:
                                        # This is pointing to $LATEST
                                        lambda_integrations.append({
                                            'function_name': function_part,
                                            'qualifier': '$LATEST',
                                            'resource_path': resource.get('path'),
                                            'method': method_name
                                        })
                    except Exception as e:
                        # Log error but continue processing other methods
                        print(f"Error getting integration for {resource.get('path')} {method_name}: {str(e)}")
            
            # Process the found Lambda integrations
            if lambda_integrations:
                # Use the first Lambda integration found as the primary one
                primary_integration = lambda_integrations[0]
                lambda_function_name = primary_integration['function_name']
                lambda_source = "integration"
                
                # Include additional information about the Lambda target
                result['lambda'] = {
                    'name': lambda_function_name,
                    'source': lambda_source,
                    'qualifier': primary_integration['qualifier'],
                    'integrations': lambda_integrations
                }
                
                # Get Lambda configuration details if available
                try:
                    # Fix for the get_function call
                    if primary_integration['qualifier'] == '$LATEST':
                        # Don't include Qualifier parameter for $LATEST
                        lambda_response = lambda_client.get_function(
                            FunctionName=lambda_function_name
                        )
                    else:
                        # Include Qualifier for specific versions or aliases
                        lambda_response = lambda_client.get_function(
                            FunctionName=lambda_function_name,
                            Qualifier=primary_integration['qualifier']
                        )
                    config = lambda_response['Configuration']
                    
                    # Add configuration details to result
                    result['lambda'].update({
                        'runtime': config.get('Runtime'),
                        'memory': config.get('MemorySize'),
                        'timeout': config.get('Timeout'),
                        'env_vars_count': len(config.get('Environment', {}).get('Variables', {}))
                    })
                    
                    # Get last modified date
                    if 'LastModified' in config:
                        modified_date = config['LastModified']
                        # Convert to just date if it's a full timestamp
                        if 'T' in modified_date:
                            modified_date = modified_date.split('T')[0]
                        result['lambda']['last_modified'] = modified_date
                except Exception as e:
                    result['lambda']['error'] = f"Error getting Lambda details: {str(e)}"
            else:
                # No Lambda integrations found
                result['lambda'] = {
                    'name': None,
                    'not_found': True,
                    'error': "No Lambda integrations found in API Gateway resource methods"
                }
        except Exception as e:
            result['lambda'] = {
                'error': f"Error finding Lambda integrations: {str(e)}"
            }
        
        # Check for API keys
        api_key_required = False
        for resource in resources.get('items', []):
            if 'resourceMethods' not in resource:
                continue
                
            for method_name, method_info in resource['resourceMethods'].items():
                try:
                    method_details = api_client.get_method(
                        restApiId=rest_api_id,
                        resourceId=resource['id'],
                        httpMethod=method_name
                    )
                    if method_details.get('apiKeyRequired', False):
                        api_key_required = True
                        break
                except:
                    continue
                    
            if api_key_required:
                break
                
        result['api_keys']['required'] = api_key_required
        
        if api_key_required:
            # Find associated usage plans and API keys
            usage_plans = []
            try:
                plans_response = api_client.get_usage_plans()
                
                for plan in plans_response.get('items', []):
                    for api_stage in plan.get('apiStages', []):
                        if api_stage.get('apiId') == rest_api_id and api_stage.get('stage') == stage_name:
                            plan_keys = []
                            
                            try:
                                keys_response = api_client.get_usage_plan_keys(usagePlanId=plan['id'])
                                
                                for key_item in keys_response.get('items', []):
                                    key_id = key_item['id']
                                    key_detail = api_client.get_api_key(apiKey=key_id, includeValue=True)
                                    
                                    plan_keys.append({
                                        'id': key_id,
                                        'name': key_detail.get('name'),
                                        'truncated_value': key_detail.get('value', 'N/A')[:5] + '...' if key_detail.get('value') else 'N/A'
                                    })
                            except:
                                pass
                                
                            usage_plans.append({
                                'id': plan['id'],
                                'name': plan['name'],
                                'keys': plan_keys
                            })
                            
                result['api_keys']['usage_plans'] = usage_plans
            except Exception as e:
                result['api_keys']['error'] = f"Error getting usage plans: {str(e)}"
        
        # Check WAF association
        try:
            web_acls = waf_client.list_web_acls(Scope='REGIONAL')
            
            for web_acl in web_acls.get('WebACLs', []):
                resources_response = waf_client.list_resources_for_web_acl(
                    WebACLArn=web_acl['ARN'],
                    ResourceType='API_GATEWAY'
                )
                
                for resource_arn in resources_response.get('ResourceArns', []):
                    if rest_api_id in resource_arn:
                        result['waf'] = {
                            'enabled': True,
                            'name': web_acl['Name'],
                            'id': web_acl['Id']
                        }
                        break
                        
                if result['waf'].get('enabled'):
                    break
                    
            if not result['waf']:
                result['waf'] = {'enabled': False}
                
        except Exception as e:
            result['waf'] = {
                'enabled': False,
                'error': f"Error checking WAF: {str(e)}"
            }
        
        # Validation models section removed - now handled separately at the API level
        
        # Get logging configuration
        try:
            logging_level = stage.get('methodSettings', {}).get('*/*', {}).get('loggingLevel', 'OFF')
            metrics_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('metricsEnabled', False)
            data_trace_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('dataTraceEnabled', False)
            xray_enabled = stage.get('tracingEnabled', False)
            
            # Check for custom access logging
            custom_access_logging_enabled = False
            access_log_settings = stage.get('accessLogSettings', {})
            custom_log_format = None
            log_group_arn = None
            
            if access_log_settings:
                custom_access_logging_enabled = True
                log_group_arn = access_log_settings.get('destinationArn')
                custom_log_format = access_log_settings.get('format')
            
            # Get CloudWatch log groups
            api_details = api_client.get_rest_api(restApiId=rest_api_id)
            api_name = api_details.get('name', '')
            log_groups = get_cloudwatch_log_groups_for_api(api_name, stage_name)
            
            # Determine if custom log format matches standard schema
            uses_standard_schema = False
            if custom_log_format:
                try:
                    # Compare with standard schema
                    custom_format_dict = json.loads(custom_log_format)
                    std_schema_dict = STANDARD_ACCESS_LOG_SCHEMA_122024
                    uses_standard_schema = custom_format_dict == std_schema_dict
                except (json.JSONDecodeError, TypeError):
                    # If it can't be parsed as JSON, it's not matching standard schema
                    uses_standard_schema = False
            
            result['logging'] = {
                'level': logging_level,
                'cloudwatch_logs_enabled': logging_level != 'OFF',
                'detailed_metrics': metrics_enabled,
                'data_tracing': data_trace_enabled,
                'xray_tracing': xray_enabled,
                'custom_access_logging': {
                    'enabled': custom_access_logging_enabled,
                    'log_group_arn': log_group_arn,
                    'format': custom_log_format,
                    'uses_standard_schema': uses_standard_schema
                },
                'log_groups': log_groups
            }
        except Exception as e:
            result['logging'] = {
                'error': f"Error getting logging config: {str(e)}"
            }
        
        # Get integration configuration (for POST method)
        try:
            for resource in resources.get('items', []):
                if 'resourceMethods' not in resource or 'POST' not in resource['resourceMethods']:
                    continue
                    
                integration = api_client.get_integration(
                    restApiId=rest_api_id,
                    resourceId=resource['id'],
                    httpMethod='POST'
                )
                
                result['integration'] = {
                    'type': integration.get('type'),
                    'timeout_seconds': integration.get('timeoutInMillis', 0) / 1000 if 'timeoutInMillis' in integration else None
                }
                break
        except Exception as e:
            result['integration'] = {
                'error': f"Error getting integration config: {str(e)}"
            }
        
        # Get resources and methods
        try:
            for resource in resources.get('items', []):
                if 'resourceMethods' in resource:
                    result['resources'].append({
                        'path': resource.get('path'),
                        'methods': list(resource['resourceMethods'].keys())
                    })
        except Exception as e:
            result['resources'] = [{
                'error': f"Error getting resources: {str(e)}"
            }]
        
        return result
        
    except Exception as e:
        print(f"Error getting deployment info: {str(e)}")
        return result
def get_lambda_role_policies(role_name):
    """
    Get the policies attached to a Lambda IAM role.
    
    :param role_name: str, name or ARN of the IAM role
    :return: dict, containing role name and list of policy information
    """
    iam_client = boto3.client('iam')
    result = {
        'role_name': role_name.split('/')[-1] if '/' in role_name else role_name,
        'policies': []
    }
    
    try:
        # Extract just the role name if an ARN is provided
        if role_name.startswith('arn:aws:iam::'):
            role_name = role_name.split('/')[-1]
            
        # Get managed policies attached to the role
        managed_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        
        for policy in managed_policies.get('AttachedPolicies', []):
            policy_arn = policy.get('PolicyArn', '')
            policy_name = policy.get('PolicyName', '')
            
            # Determine if it's AWS managed or customer managed
            policy_type = 'AWS managed' if 'iam::aws' in policy_arn else 'Customer managed'
            
            result['policies'].append({
                'name': policy_name,
                'type': policy_type
            })
            
        # Get inline policies
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        
        for policy_name in inline_policies.get('PolicyNames', []):
            result['policies'].append({
                'name': policy_name,
                'type': 'Inline'
            })
            
        return result
    except Exception as e:
        print(f"Error getting role policies: {str(e)}")
        return result
def get_lambda_resource_policies(function_name):
    """
    Get the resource-based policies attached to a Lambda function.
    
    :param function_name: str, name or ARN of the Lambda function
    :return: dict, containing function name and list of resource-based policy statements
    """
    lambda_client = boto3.client('lambda')
    result = {
        'function_name': function_name.split(':')[-1] if ':' in function_name else function_name,
        'policy_statements': []
    }
    
    try:
        # Extract just the function name if an ARN is provided
        if function_name.startswith('arn:aws:lambda:'):
            function_name = function_name.split(':')[-1]
            
        # Get the resource policy
        response = lambda_client.get_policy(FunctionName=function_name)
        
        if 'Policy' in response:
            policy_json = json.loads(response['Policy'])
            
            if 'Statement' in policy_json:
                for statement in policy_json['Statement']:
                    result['policy_statements'].append({
                        'sid': statement.get('Sid', 'No ID'),
                        'effect': statement.get('Effect', 'Unknown'),
                        'principal': statement.get('Principal', {}),
                        'action': statement.get('Action', 'Unknown'),
                        'resource': statement.get('Resource', 'Unknown'),
                        'condition': statement.get('Condition', {})
                    })
        
        return result
    except Exception as e:
        if 'ResourceNotFoundException' in str(e):
            # No resource-based policy exists
            return result
        else:
            print(f"Error getting resource policies: {str(e)}")
            return result
def get_lambda_code_from_zip_file(zip_path, verbose=False):
    """
    Extract Python code files from a Lambda deployment zip file.
    
    :param zip_path: str, path to the zip file on local filesystem
    :param verbose: bool, whether to print verbose debug information
    :return: dict, containing file paths as keys and content as values, or None if error
    """
    try:
        # Extract all files from the zip
        lambda_code = {}
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List all files in the zip and print them for debugging
            file_list = zip_ref.namelist()
            verbose_print(verbose, f"Files in deployment package: {[f for f in file_list if f.endswith('.py') and not 'site-packages' in f]}")
            
            # Extract all Python files (excluding site-packages and other library files)
            for file_path in file_list:
                if (file_path.endswith('.py') and 
                    'site-packages' not in file_path and
                    not file_path.startswith('urllib') and
                    not file_path.startswith('boto') and
                    not file_path.startswith('pydantic')):
                    
                    try:
                        with zip_ref.open(file_path) as f:
                            lambda_code[file_path] = f.read().decode('utf-8')
                    except Exception as e:
                        verbose_print(verbose, f"Error reading {file_path}: {str(e)}")
            
            if not lambda_code:
                print(f"⚠️ Warning: No Python files found in the deployment package at {zip_path}")
                return None
            
            return lambda_code
    except Exception as e:
        print(f"Error extracting code from zip file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
def get_app_dot_py_code_from_zip(zip_path, verbose=False):
    """
    Extract the app.py code from a Chalice deployment .zip file.
    
    :param zip_path: Path to the Chalice deployment .zip file on local filesystem.
    :param verbose: bool, whether to print verbose debug information
    :return: str, app.py code from the zip file or None if not found
    """
    # Get all code files from the zip
    lambda_code = get_lambda_code_from_zip_file(zip_path, verbose)
    
    if not lambda_code:
        return None
    
    # First look for app.py at the root level
    if 'app.py' in lambda_code:
        return lambda_code['app.py']
    
    # Then look for app.py in any subdirectory
    app_py_keys = [k for k in lambda_code.keys() if k.endswith('/app.py')]
    if app_py_keys:
        return lambda_code[app_py_keys[0]]
    
    # Finally look for a Python file mentioning Chalice
    for file_path, content in lambda_code.items():
        if ('app = Chalice' in content or 
            '@app.route' in content or 
            'from chalice import Chalice' in content):
            return content
    
    print(f"⚠️ Warning: app.py not found in the deployment package at {zip_path}")
    return None
def mtest_get_app_dot_py_code_from_zip():
    pass
#if __name__ == "__main__":
    zip_path = "web-shared/aws_chalice/vrag-llm/.chalice/deployments/prod-init-promote_f115601e24db7e859c605b4178f8cd1c-python3.11.zip"
    app_code = get_app_dot_py_code_from_zip(zip_path)
    print(f"App.py code from zip:\n{app_code}")

def get_lambda_code_from_deployment_info(deployment_info, verbose=False):
    """
    Retrieves the full source code of a deployed Lambda function using API Gateway deployment info.
    
    :param deployment_info: dict, deployment information from get_api_stage_current_config
    :param verbose: bool, whether to print verbose debug information
    :return: dict, containing the full Lambda deployment package with file paths as keys and content as values,
             or None if error
    """
    lambda_client = boto3.client('lambda')
    
    try:
        # Extract Lambda info from deployment_info
        lambda_info = deployment_info.get('lambda', {})
        
        if not lambda_info.get('name'):
            print("No Lambda function found in deployment info")
            return None
        
        lambda_function_name = lambda_info.get('name')
        lambda_qualifier = lambda_info.get('qualifier', '$LATEST')
        
        # Get the function details with the appropriate qualifier
        get_function_args = {'FunctionName': lambda_function_name}
        if lambda_qualifier != '$LATEST':
            get_function_args['Qualifier'] = lambda_qualifier
            
        function_info = lambda_client.get_function(**get_function_args)
        
        # Get the S3 location or the URL for the code
        code_location = function_info['Code']['Location']
        
        # Create a temp directory to store the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'lambda_function.zip')
            
            # Download the deployment package
            urllib.request.urlretrieve(code_location, zip_path)
            
            # Use the helper function to extract code from the zip file
            lambda_code = get_lambda_code_from_zip_file(zip_path, verbose)
            
            if not lambda_code:
                print(f"⚠️ Warning: No Python files found in the Lambda deployment package for {lambda_function_name}")
                return None
            
            return lambda_code
    except Exception as e:
        print(f"Error getting Lambda code: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
def extract_last_updated_comment(lambda_code):
    """
    Extract the "last updated" comment from the app.py file within lambda code.
    
    :param lambda_code: dict or str, the Lambda function source code files or direct app.py content
    :return: str, the extracted last updated comment or Warning if not found
    :raises ValueError: if the lambda_code is empty or doesn't contain app.py
    """
    if not lambda_code:
        raise ValueError("No code provided to extract last updated comment from")
    
    # Handle different input types
    if isinstance(lambda_code, dict):
        # First find the app.py file
        app_py_content = None
        
        # Look for app.py at the root level
        if 'app.py' in lambda_code:
            app_py_content = lambda_code['app.py']
        else:
            # Look for app.py in any subdirectory
            app_py_keys = [k for k in lambda_code.keys() if k.endswith('/app.py')]
            if app_py_keys:
                app_py_content = lambda_code[app_py_keys[0]]
            else:
                # Look for a Python file mentioning Chalice
                for file_path, content in lambda_code.items():
                    if ('app = Chalice' in content or 
                        '@app.route' in content or 
                        'from chalice import Chalice' in content):
                        app_py_content = content
                        break
        
        if not app_py_content:
            return "⚠️ Warning: No app.py or Chalice app file found in the Lambda code"
    else:
        # Assume the input is a string containing app.py content directly
        app_py_content = lambda_code
    
    # More flexible pattern that handles single or double quotes, with or without colon, and extra whitespace
    # Also handles f-strings where there may be a character (f) before the first quote
    pattern = re.compile(r'print\s*\(\s*f?[\'"].*?last updated\s*:?\s*([^\'"]*)[\'"]', re.IGNORECASE)
    
    # Check for multiple occurrences
    matches = []
    for line in app_py_content.splitlines():
        match = pattern.search(line)
        if match:
            matches.append(match.group(1).strip())
    
    if len(matches) > 1:
        return f"⚠️ Warning: Multiple 'last updated' comments found. Using first one: {matches[0]}"
    elif matches:
        return matches[0]
    
    for line in app_py_content.splitlines():
        match = pattern.search(line)
        if match:
            return match.group(1).strip()
    
    return "⚠️ Warning: No 'last updated' comment found in the expected format"
def get_last_updated_comment_in_lambda_code(app_name, env):
    api_gateway_name, stage, aws_lambda_name = map_names_env_stages(app_name, env)
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method='POST')
    deployment_info = get_api_stage_current_config(rest_api_id, stage)
    lambda_code = get_lambda_code_from_deployment_info(deployment_info)
    return extract_last_updated_comment(lambda_code)
def mtest_get_last_updated_comment_in_lambda_code():
    pass
#if __name__ == "__main__":
    app_name = cur_app_name
    env = 'dev'
    last_updated_comment = get_last_updated_comment_in_lambda_code(app_name, env)
    print(f"Last updated comment in app.py lambda code for {app_name} env={env}: {last_updated_comment}")

    env = 'prod'
    last_updated_comment = get_last_updated_comment_in_lambda_code(app_name, env)
    print(f"Last updated comment in app.py lambda code for {app_name} env={env}: {last_updated_comment}")
def get_deployed_lambda_code(app_name, env):
    """
    Retrieves the full Lambda deployment package code for a deployed application.
    
    :param app_name: str, name of the application
    :param env: str, environment ('dev' or 'prod')
    :return: dict, containing file paths as keys and content as values, or None if error
    """
    api_gateway_name, stage, aws_lambda_name = map_names_env_stages(app_name, env)
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method='POST')
    deployment_info = get_api_stage_current_config(rest_api_id, stage)
    return get_lambda_code_from_deployment_info(deployment_info)
def get_app_dot_py_code_from_deployed_lambda(app_name, env):
    """
    Gets the app.py code from a deployed Lambda function.
    
    :param app_name: str, name of the application
    :param env: str, environment ('dev' or 'prod')
    :return: str, the app.py code from the deployed Lambda function, or None if not found
    """
    lambda_code = get_deployed_lambda_code(app_name, env)
    
    if not lambda_code:
        return None
    
    # First look for app.py at the root level
    if 'app.py' in lambda_code:
        return lambda_code['app.py']
    
    # Then look for app.py in any subdirectory
    app_py_keys = [k for k in lambda_code.keys() if k.endswith('/app.py')]
    if app_py_keys:
        return lambda_code[app_py_keys[0]]
    
    # Finally look for a Python file mentioning Chalice
    for file_path, content in lambda_code.items():
        if ('app = Chalice' in content or 
            '@app.route' in content or 
            'from chalice import Chalice' in content):
            return content
    
    return None
def mtest_get_app_dot_py_code_from_deployed_lambda():
    pass
#if __name__ == "__main__":
    app_name = cur_app_name
    env = 'dev'
    app_code = get_app_dot_py_code_from_deployed_lambda(app_name, env)
    print(f"Deployed App.py lambda code for {app_name} env={env}:\n{app_code}")
def get_last_updated_comment_in_local_app_code(app_name):
    chalice_app_folder = f"{CHALICE_FOLDER}{app_name}"
    app_py_path = os.path.join(chalice_app_folder, 'app.py')
    with open(app_py_path, 'r') as f:
        full_app_code = f.read()
    #print(f"DEBUG: First line of app.py code: {full_app_code.splitlines()[0]}")
    return extract_last_updated_comment(full_app_code)
def mtest_get_last_updated_comment_in_local_app_code():
    pass
#if __name__ == "__main__":
    app_name = cur_app_name
    last_updated_comment = get_last_updated_comment_in_local_app_code(app_name)
    print(f"Last updated comment in app.py code for {app_name}: {last_updated_comment}")
def is_same_lambda_code_zip_vs_deployed(zip_path, app_name, env, verbose=False):
    """
    Compare the code in a local zip file with the code deployed in a Lambda function.
    
    :param zip_path: str, path to the local zip file
    :param app_name: str, name of the application
    :param env: str, environment ('dev' or 'prod')
    :param verbose: bool, whether to print verbose debug information
    :return: bool, True if the code is identical, False otherwise
    """
    # Get the code from the zip file
    zip_code = get_lambda_code_from_zip_file(zip_path, verbose)
    if not zip_code:
        print(f"⚠️ Error: Could not extract code from zip file: {zip_path}")
        return False
    
    # Get the deployed Lambda code
    deployed_code = get_deployed_lambda_code(app_name, env)
    if not deployed_code:
        print(f"⚠️ Error: Could not retrieve deployed code for app: {app_name}, env: {env}")
        return False
    
    # Check if the sets of files are the same
    zip_files = set(zip_code.keys())
    deployed_files = set(deployed_code.keys())
    
    # Files in zip but not in deployed
    missing_from_deployed = zip_files - deployed_files
    if missing_from_deployed:
        if verbose:
            print(f"Files in zip but missing from deployed Lambda:")
            for file in sorted(missing_from_deployed):
                print(f"  - {file}")
        else:
            print(f"Files in zip but missing from deployed Lambda: {len(missing_from_deployed)}")
    
    # Files in deployed but not in zip
    missing_from_zip = deployed_files - zip_files
    if missing_from_zip:
        if verbose:
            print(f"Files in deployed Lambda but missing from zip:")
            for file in sorted(missing_from_zip):
                print(f"  - {file}")
        else:
            print(f"Files in deployed Lambda but missing from zip: {len(missing_from_zip)}")
    
    # Files that exist in both but with different content
    different_content = []
    common_files = zip_files.intersection(deployed_files)
    for file in common_files:
        if zip_code[file] != deployed_code[file]:
            different_content.append(file)
    
    if different_content:
        if verbose:
            print(f"Files with different content:")
            for file in sorted(different_content):
                print(f"  - {file}")
        else:
            print(f"Files with different content: {len(different_content)}")
    
    # Return True only if no differences were found
    is_same = not (missing_from_deployed or missing_from_zip or different_content)
    
    if is_same:
        print(f"✅ Lambda code in zip and deployed version are identical ({len(common_files)} files) for {app_name}-{env}")
    else:
        print(f"❌ Lambda code in zip and deployed version are different for {app_name}-{env}")
    
    return is_same
def mtest_is_same_lambda_code_zip_vs_deployed():
    pass
#if __name__ == "__main__":
    zip_path = PROMOTE_TO_PROD_ZIP_PATH
    app_name = cur_app_name
    env = "dev"
    result = is_same_lambda_code_zip_vs_deployed(zip_path, app_name, env)
    print(f"is_same_lambda_code_zip_vs_deployed for {app_name}-{env}: {result}")
    
    print("--------------------------------")
    env = "prod"
    result = is_same_lambda_code_zip_vs_deployed(zip_path, app_name, env)
    print(f"is_same_lambda_code_zip_vs_deployed for {app_name}-{env}: {result}")


def get_last_file_in_folder(folder_path, pattern=None):
    """
    Find the most recent file in a folder by sorting filenames.
    
    :param folder_path: str, path to the folder to search
    :param pattern: str, glob pattern to match files
    :return last_file: str, path to the most recent file or None if no files found
    """
    if not os.path.exists(folder_path):
        return None
    
    files = glob.glob(f"{folder_path}/{pattern}" if pattern else f"{folder_path}/*")
    if not files:
        return None
    
    # Sort files by name which effectively sorts by timestamp if date is in filename
    files.sort(reverse=True)
    return files[0]
def get_last_deployed_log_file_paths(app_name):
    """
    Find the most recent deployment log files for both dev and prod environments.

    :param app_name: str, name of the application (e.g., 'hmac-hash')
    :return: tuple, (dev_log_path, prod_log_path) with the most recent log file for each or None if not found
    """
    dev_logs_dir = get_deploy_logs_dir(app_name, "dev")
    prod_logs_dir = get_deploy_logs_dir(app_name, "prod")
    # Find the most recent log files using the helper function
    dev_log_path = get_last_file_in_folder(dev_logs_dir, "deployed_dev_log_*.md")
    prod_log_path = get_last_file_in_folder(prod_logs_dir, "deployed_prod_log_*.md")
    return (dev_log_path, prod_log_path)
def mtest_get_last_deployed_log_file_paths():
    pass
#if __name__ == "__main__":
    app_name = "hmac-hash"
    dev_log_path, prod_log_path = get_last_deployed_log_file_paths(app_name)
    print(f"Last deployed log file paths for {app_name}:\ndev: {dev_log_path}\nprod: {prod_log_path}")

def parse_api_state_report_section(api_name, section, debug=False):
    """
    Parse an API section from the report to extract relevant information.
    
    :param api_name: str, name of the API Gateway
    :param section: str, section content
    :param debug: bool, whether to print debug information
    :return: dict, structured information from the section
    """
    info = {
        'lambda': {},
        'iam_roles': [],
        'resource_policies': [],
        'api_keys': {},
        'waf': {},
        'logging': {
            'config': {},
            'log_groups': []
        },
        'integration': {},
        'resources': [],
        'validation_models': []
    }
    
    verbose_print(debug, f"\n--- Parsing section for {api_name} ---")
    
    # Extract Lambda configuration
    lambda_match = re.search(r'### Lambda config: ([^\n]+)(.*?)(?=###|\Z)', section, re.DOTALL)
    if lambda_match:
        info['lambda']['name'] = lambda_match.group(1).strip()
        verbose_print(debug, f"Found Lambda name: {info['lambda']['name']}")
        lambda_details = lambda_match.group(2)
        
        # Skip the '(Found via...)' line if present
        if '(Found via' in lambda_details.split('\n')[0]:
            lambda_details = '\n'.join(lambda_details.split('\n')[1:])
            verbose_print(debug, "Skipped 'Found via' line in Lambda details")
        
        # Runtime
        runtime_match = re.search(r'Runtime: ([^\n]+)', lambda_details)
        if runtime_match:
            info['lambda']['runtime'] = runtime_match.group(1).strip()
            verbose_print(debug, f"Found Lambda runtime: {info['lambda']['runtime']}")
        else:
            verbose_print(debug, "Lambda runtime not found")
        
        # Memory
        memory_match = re.search(r'Memory: ([^\n]+)', lambda_details)
        if memory_match:
            info['lambda']['memory'] = memory_match.group(1).strip()
            verbose_print(debug, f"Found Lambda memory: {info['lambda']['memory']}")
        else:
            verbose_print(debug, "Lambda memory not found")
        
        # Timeout
        timeout_match = re.search(r'Timeout: ([^\n]+)', lambda_details)
        if timeout_match:
            info['lambda']['timeout'] = timeout_match.group(1).strip()
            verbose_print(debug, f"Found Lambda timeout: {info['lambda']['timeout']}")
        else:
            verbose_print(debug, "Lambda timeout not found")
        
        # Env Vars Count
        env_vars_match = re.search(r'Environment Variables: ([^\n]+)', lambda_details)
        if env_vars_match:
            info['lambda']['env_vars_count'] = env_vars_match.group(1).strip()
            verbose_print(debug, f"Found Lambda env vars count: {info['lambda']['env_vars_count']}")
        else:
            verbose_print(debug, "Lambda env vars count not found")
    else:
        verbose_print(debug, "Lambda config section not found")
    
    # Extract IAM Role
    role_match = re.search(r'### Lambda IAM Role: ([^\n]+)(.*?)(?=###|\Z)', section, re.DOTALL)
    if role_match:
        role_name = role_match.group(1).strip()
        info['lambda']['role_name'] = role_name
        role_section = role_match.group(2)
        
        # Simply split by lines and keep non-empty ones
        policy_lines = [line.strip() for line in role_section.split('\n') if line.strip()]
        info['iam_roles'] = policy_lines
        
        verbose_print(debug, f"Found role: {role_name} with policies: {policy_lines}")
    else:
        verbose_print(debug, "IAM Role section not found")
    
    # Extract Resource-Based Policies
    resource_policies_match = re.search(r'### Lambda Resource-Based Policies: ([^\n]+)(.*?)(?=###|\Z)', section, re.DOTALL)
    if resource_policies_match:
        policy_count = resource_policies_match.group(1).strip()
        if policy_count != "0":
            policy_section = resource_policies_match.group(2)
            
            # Parse each policy statement
            policy_statements = []
            # Match each policy line with the format: 
            # SID - Principal: xxx, Action: xxx, Condition: xxx
            policy_pattern = r'([^\n-]+) - Principal: ([^,]+), Action: ([^,]+), Condition: ([^\n]+)'
            for match in re.finditer(policy_pattern, policy_section):
                sid = match.group(1).strip()
                principal = match.group(2).strip()
                action = match.group(3).strip()
                condition = match.group(4).strip()
                
                policy_statements.append({
                    'sid': sid,
                    'principal': principal,
                    'action': action,
                    'condition': condition
                })
            
            info['resource_policies'] = policy_statements
            verbose_print(debug, f"Found {len(policy_statements)} resource policies")
        else:
            verbose_print(debug, "No resource policies found")
    else:
        verbose_print(debug, "Resource policies section not found")
    
    # Extract API Keys
    api_keys_match = re.search(r'### API keys: ([^\n]+)(.*?)(?=###|\Z)', section, re.DOTALL)
    if api_keys_match:
        info['api_keys']['required'] = api_keys_match.group(1).strip().lower() == 'true'
        if info['api_keys']['required']:
            # Extract key details if they exist
            key_matches = re.findall(r'#### API key: ([^\n]+)  usage plan: ([^\n]+)', api_keys_match.group(2))
            info['api_keys']['keys'] = [{'key': k.strip(), 'plan': p.strip()} for k, p in key_matches]
    
    # Extract WAF info
    waf_match = re.search(r'### WAF: ([^\n]+)(.*?)(?=###|\Z)', section, re.DOTALL)
    if waf_match:
        info['waf']['enabled'] = waf_match.group(1).strip().lower() == 'enabled'
        if info['waf']['enabled']:
            acl_match = re.search(r'#### ACL: ([^\n]+)', waf_match.group(2))
            if acl_match:
                info['waf']['acl'] = acl_match.group(1).strip()
    
    # Extract Logging section
    # Fix the Logging section regex to correctly get everything until the next level 3 heading
    verbose_print(debug, f"Searching for logging section in section of length {len(section)}")
    verbose_print(debug, f"Section preview: {section[:100]}...")

    # Improved regex that only stops at level 3 headings, not level 4
    logging_match = re.search(r'### Logging(.*?)(?=\n### |\Z)', section, re.DOTALL)
    if logging_match:
        logging_section = logging_match.group(1)
        verbose_print(debug, f"Found logging section, length: {len(logging_section)}")
        verbose_print(debug, f"Logging section preview: {logging_section[:100]}...")
    
    # Extract basic config from "API Gateway > Logs and Tracing" section
    tracing_section_match = re.search(r'#### API Gateway > Logs and Tracing\n(.*?)(?=####|\Z)', logging_section, re.DOTALL)
    if tracing_section_match:
        tracing_section = tracing_section_match.group(1)
        verbose_print(debug, f"Found tracing section: {tracing_section}")
        
        # Extract key-value pairs
        level_match = re.search(r'loggingLevel:\s+([^\n]+)', tracing_section)
        if level_match:
            info['logging']['config']['level'] = level_match.group(1).strip()
            verbose_print(debug, f"Found logging level: {info['logging']['config']['level']}")
        
        cloudwatch_match = re.search(r'CloudWatch logs:\s+([^\n]+)', tracing_section)
        if cloudwatch_match:
            info['logging']['config']['cloudwatch'] = cloudwatch_match.group(1).strip()
            verbose_print(debug, f"Found CloudWatch logs: {info['logging']['config']['cloudwatch']}")
        
        metrics_match = re.search(r'Detailed metrics:\s+([^\n]+)', tracing_section)
        if metrics_match:
            info['logging']['config']['metrics'] = metrics_match.group(1).strip()
            verbose_print(debug, f"Found metrics: {info['logging']['config']['metrics']}")
        
        tracing_match = re.search(r'Data tracing:\s+([^\n]+)', tracing_section)
        if tracing_match:
            info['logging']['config']['tracing'] = tracing_match.group(1).strip()
            verbose_print(debug, f"Found data tracing: {info['logging']['config']['tracing']}")
        
        xray_match = re.search(r'X-Ray tracing:\s+([^\n]+)', tracing_section)
        if xray_match:
            info['logging']['config']['xray'] = xray_match.group(1).strip()
            verbose_print(debug, f"Found X-Ray tracing: {info['logging']['config']['xray']}")
    
    # Extract custom access logging info
    custom_logging_match = re.search(r'#### API Gateway > Custom access logging: ([^\n]+)', logging_section)
    if custom_logging_match:
        custom_status = custom_logging_match.group(1).strip()
        info['logging']['custom_enabled'] = custom_status.lower() == 'active'
        verbose_print(debug, f"Found custom access logging: {custom_status}")
        
        # Get the ARN line that follows
        arn_match = re.search(r'arn:[^\n]+', logging_section)
        if arn_match:
            info['logging']['custom_arn'] = arn_match.group(0).strip()
            verbose_print(debug, f"Found custom ARN: {info['logging']['custom_arn']}")
        
        # Get the schema line
        schema_match = re.search(r'standard custom access logging schema[^\n]*', logging_section)
        if schema_match:
            info['logging']['custom_schema'] = schema_match.group(0).strip()
            verbose_print(debug, f"Found custom schema: {info['logging']['custom_schema']}")
    
    # Get CloudWatch log groups - using direct string search
    cloudwatch_heading = '#### Cloudwatch Log Groups'
    heading_pos = logging_section.find(cloudwatch_heading)
    
    if heading_pos >= 0:
        # Get everything after the heading
        log_section = logging_section[heading_pos + len(cloudwatch_heading):].strip()
        verbose_print(debug, f"Found log group section: '{log_section}'")
        
        # Extract each non-empty, non-heading line as a log group
        log_groups = []
        for line in log_section.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                log_groups.append(line)
                verbose_print(debug, f"Added log group: '{line}'")
        
        info['logging']['log_groups'] = log_groups
        verbose_print(debug, f"Total log groups found: {len(log_groups)}")
    else:
        verbose_print(debug, "Cloudwatch Log Groups section not found")

    # Extract Integration Configuration
    integration_match = re.search(r'### Integration Configuration(.*?)(?=###|\Z)', section, re.DOTALL)
    if integration_match:
        integration_section = integration_match.group(1)
        
        type_match = re.search(r'Type: ([^\n]+)', integration_section)
        if type_match:
            info['integration']['type'] = type_match.group(1).strip()
        
        timeout_match = re.search(r'Timeout: ([^\n]+)', integration_section)
        if timeout_match:
            info['integration']['timeout'] = timeout_match.group(1).strip()
    
    # Extract Resources
    resources_match = re.search(r'### Resources(.*?)(?=##|###|\Z)', section, re.DOTALL)
    if resources_match:
        resources_section = resources_match.group(1).strip()
        verbose_print(debug, f"Found resources section, length: {len(resources_section)}")
        
        # Store the raw text for exact comparison
        info['raw_resources'] = resources_section
    else:
        verbose_print(debug, "Resources section not found")
    
    # Extract Validation Models - store the raw text
    models_section_match = re.search(r'## Request Validation Models:(.*?)(?=\n## |\Z)', section, re.DOTALL)
    if models_section_match:
        models_section = models_section_match.group(1).strip()
        verbose_print(debug, f"Found validation models section, length: {len(models_section)}")
        
        # Store the raw text for exact comparison
        info['raw_validation_models'] = models_section
    else:
        verbose_print(debug, "Validation models section not found")
    
    return info
def generate_api_report_env_comparison(api_name, dev_info, prod_info, debug=False):
    """
    Generate a comparison section between dev and prod environments.
    
    :param api_name: str, name of the API Gateway
    :param dev_info: dict, dev environment information
    :param prod_info: dict, prod environment information
    :param debug: bool, whether to print debug information
    :return: str, formatted comparison section
    """
    # Track if everything is the same
    all_same = True
    
    # For debugging: Print the raw IAM roles
    verbose_print(debug, f"Dev IAM roles: {dev_info['iam_roles']}")
    verbose_print(debug, f"Prod IAM roles: {prod_info['iam_roles']}")
    
    # Compare Lambda configuration (excluding 'Last Updated')
    lambda_same = True
    if 'lambda' in dev_info and 'lambda' in prod_info:
        for key in ['runtime', 'memory', 'timeout', 'env_vars_count']:
            if key in dev_info['lambda'] and key in prod_info['lambda']:
                if dev_info['lambda'][key] != prod_info['lambda'][key]:
                    lambda_same = False
                    all_same = False
                    break
            elif key in dev_info['lambda'] or key in prod_info['lambda']:
                lambda_same = False
                all_same = False
                break
    else:
        lambda_same = False
        all_same = False
    
    # SIMPLIFIED: Compare IAM Role policies with direct string matching
    iam_same = True
    
    # Filter out dev-specific policies
    dev_policies = []
    for policy in dev_info['iam_roles']:
        # Skip policies that start with the API name + "-dev"
        verbose_print(debug, f"Checking policy: {policy}")
        if not policy.startswith(f"{api_name}-dev") and not policy.startswith(f"{api_name}-prod"):
            dev_policies.append(policy)
        else:
            verbose_print(debug, f"Filtering out dev-specific policy: {policy}")
    
    # Filter out prod-specific policies
    prod_policies = []
    for policy in prod_info['iam_roles']:
        # Skip policies that start with the API name + "-dev" or "-prod"
        if not policy.startswith(f"{api_name}-dev") and not policy.startswith(f"{api_name}-prod"):
            prod_policies.append(policy)
        else:
            verbose_print(debug, f"Filtering out prod-specific policy: {policy}")
    
    # Convert to sets for easier comparison
    dev_policy_set = set(dev_policies)
    prod_policy_set = set(prod_policies)
    
    # Debug comparison
    verbose_print(debug, f"Dev policies (filtered): {dev_policy_set}")
    verbose_print(debug, f"Prod policies (filtered): {prod_policy_set}")
    
    # Check if exactly the same policies exist
    if dev_policy_set != prod_policy_set:
        missing_in_dev = prod_policy_set - dev_policy_set
        missing_in_prod = dev_policy_set - prod_policy_set
        
        verbose_print(debug, f"Missing in dev: {missing_in_dev}")
        verbose_print(debug, f"Missing in prod: {missing_in_prod}")
        
        iam_same = False
        all_same = False
    
    # Compare Resource-Based Policies
    resource_policies_same = True
    
    # Compare resource-based policies with special handling for API Gateway invoke permissions
    if 'resource_policies' in dev_info and 'resource_policies' in prod_info:
        dev_policies = dev_info['resource_policies']
        prod_policies = prod_info['resource_policies']
        
        # Debug output
        verbose_print(debug, f"Dev resource policies: {dev_policies}")
        verbose_print(debug, f"Prod resource policies: {prod_policies}")
        
        # Check if both environments have API Gateway invoke permissions
        dev_has_api_gateway = any(
            policy['principal'] == 'apigateway.amazonaws.com' and 
            'lambda:InvokeFunction' in policy['action']
            for policy in dev_policies
        )
        
        prod_has_api_gateway = any(
            policy['principal'] == 'apigateway.amazonaws.com' and 
            'lambda:InvokeFunction' in policy['action']
            for policy in prod_policies
        )
        
        # If one has API Gateway permissions but the other doesn't
        if dev_has_api_gateway != prod_has_api_gateway:
            verbose_print(debug, f"API Gateway permission mismatch: dev={dev_has_api_gateway}, prod={prod_has_api_gateway}")
            resource_policies_same = False
            all_same = False
        
        # For API Gateway policies, compare content instead of IDs
        if dev_has_api_gateway and prod_has_api_gateway:
            # Get API Gateway policies (excluding SID from comparison)
            dev_api_policies = [
                {k: v for k, v in policy.items() if k != 'sid'}
                for policy in dev_policies 
                if policy['principal'] == 'apigateway.amazonaws.com' and 'lambda:InvokeFunction' in policy['action']
            ]
            
            prod_api_policies = [
                {k: v for k, v in policy.items() if k != 'sid'}
                for policy in prod_policies 
                if policy['principal'] == 'apigateway.amazonaws.com' and 'lambda:InvokeFunction' in policy['action']
            ]
            
            # Compare policies excluding SIDs
            if dev_api_policies != prod_api_policies:
                verbose_print(debug, f"API Gateway policy content mismatch: dev={dev_api_policies}, prod={prod_api_policies}")
                resource_policies_same = False
                all_same = False
        
        # Handle non-API Gateway policies if they exist
        # Get meaningful policies (those with non-UUID SIDs)
        uuid_regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        
        meaningful_dev_policies = [
            policy for policy in dev_policies 
            if not (policy['principal'] == 'apigateway.amazonaws.com' and 'lambda:InvokeFunction' in policy['action']) 
            and not re.match(uuid_regex, policy['sid'])
        ]
        
        meaningful_prod_policies = [
            policy for policy in prod_policies 
            if not (policy['principal'] == 'apigateway.amazonaws.com' and 'lambda:InvokeFunction' in policy['action'])
            and not re.match(uuid_regex, policy['sid'])
        ]
        
        if meaningful_dev_policies != meaningful_prod_policies:
            verbose_print(debug, f"Other policy mismatch: dev={meaningful_dev_policies}, prod={meaningful_prod_policies}")
            resource_policies_same = False
            all_same = False
    
    # Compare API keys
    api_keys_same = True
    if dev_info['api_keys']['required'] != prod_info['api_keys']['required']:
        api_keys_same = False
        all_same = False
    elif dev_info['api_keys']['required'] and prod_info['api_keys']['required']:
        if 'keys' in dev_info['api_keys'] and 'keys' in prod_info['api_keys']:
            dev_plans = sorted([k['plan'] for k in dev_info['api_keys']['keys']])
            prod_plans = sorted([k['plan'] for k in prod_info['api_keys']['keys']])
            if dev_plans != prod_plans:
                api_keys_same = False
                all_same = False
    
    # Compare WAF
    waf_same = True
    if dev_info['waf']['enabled'] != prod_info['waf']['enabled']:
        waf_same = False
        all_same = False
    elif dev_info['waf']['enabled'] and prod_info['waf']['enabled']:
        if 'acl' in dev_info['waf'] and 'acl' in prod_info['waf']:
            if dev_info['waf']['acl'] != prod_info['waf']['acl']:
                waf_same = False
                all_same = False
    
    # Compare Logging with corrected structure
    logging_same = True

    # Compare Logs and Tracing section
    if dev_info['logging']['config'] != prod_info['logging']['config']:
        verbose_print(debug, "Logs and Tracing configuration mismatch")
        verbose_print(debug, f"Dev: {dev_info['logging']['config']}")
        verbose_print(debug, f"Prod: {prod_info['logging']['config']}")
        logging_same = False
        all_same = False

    # Compare custom access logging
    if ('custom_enabled' in dev_info['logging'] and 'custom_enabled' in prod_info['logging']):
        if dev_info['logging']['custom_enabled'] != prod_info['logging']['custom_enabled']:
            verbose_print(debug, "Custom access logging enabled status mismatch")
            logging_same = False
            all_same = False
        
        # Compare ARN with substitutions
        if 'custom_arn' in dev_info['logging'] and 'custom_arn' in prod_info['logging']:
            dev_arn = dev_info['logging']['custom_arn']
            prod_arn = prod_info['logging']['custom_arn']
            
            # Transform dev ARN to expected prod ARN
            if dev_arn.endswith('_dev'):
                expected_prod_arn = dev_arn[:-4] + '-prod_prod'
            else:
                expected_prod_arn = dev_arn
            
            if expected_prod_arn != prod_arn:
                verbose_print(debug, f"Custom ARN mismatch: expected '{expected_prod_arn}', got '{prod_arn}'")
                logging_same = False
                all_same = False
        
        # Compare schema
        if 'custom_schema' in dev_info['logging'] and 'custom_schema' in prod_info['logging']:
            if dev_info['logging']['custom_schema'] != prod_info['logging']['custom_schema']:
                verbose_print(debug, "Custom schema mismatch")
                logging_same = False
                all_same = False

    # Compare log groups
    dev_log_groups = dev_info['logging']['log_groups'] if 'log_groups' in dev_info['logging'] else []
    prod_log_groups = prod_info['logging']['log_groups'] if 'log_groups' in prod_info['logging'] else []

    verbose_print(debug, f"Dev log groups: {dev_log_groups}")
    verbose_print(debug, f"Prod log groups: {prod_log_groups}")

    # Check for each type of log group
    for dev_log in dev_log_groups:
        found_match = False
        
        if dev_log.startswith('/aws/lambda/') and dev_log.endswith('-dev'):
            # Lambda logs: -dev → -prod 
            expected_prod = dev_log[:-4] + '-prod'
            for prod_log in prod_log_groups:
                if prod_log == expected_prod:
                    found_match = True
                    break
        
        elif dev_log.startswith('API-Gateway-Access-Logs_') and dev_log.endswith('_dev'):
            # Access logs: _dev → -prod_prod
            expected_prod = dev_log[:-4] + '-prod_prod'
            for prod_log in prod_log_groups:
                if prod_log == expected_prod:
                    found_match = True
                    break
        
        elif dev_log.startswith('API-Gateway-Execution-Logs_'):
            # Execution logs: ignore API ID, check for /prod
            if '/' in dev_log:
                base_prefix = 'API-Gateway-Execution-Logs_'
                for prod_log in prod_log_groups:
                    if prod_log.startswith(base_prefix) and '/prod' in prod_log:
                        found_match = True
                        break
        
        if not found_match:
            verbose_print(debug, f"No match found for log group: {dev_log}")
            logging_same = False
            all_same = False
            break

    # Also check we have same number of each type
    if len(dev_log_groups) != len(prod_log_groups):
        verbose_print(debug, f"Log group count mismatch: dev={len(dev_log_groups)}, prod={len(prod_log_groups)}")
        logging_same = False
        all_same = False
    
    # Compare Integration Configuration
    integration_same = True
    if dev_info['integration'] != prod_info['integration']:
        integration_same = False
        all_same = False
    
    # Compare Resources - exact text comparison only
    resources_same = True

    # Compare the raw text directly
    if 'raw_resources' in dev_info and 'raw_resources' in prod_info:
        dev_resources_text = dev_info['raw_resources'].strip()
        prod_resources_text = prod_info['raw_resources'].strip()
        
        verbose_print(debug, f"Dev resources text length: {len(dev_resources_text)}")
        verbose_print(debug, f"Prod resources text length: {len(prod_resources_text)}")
        
        if dev_resources_text != prod_resources_text:
            verbose_print(debug, "Resources text doesn't match")
            resources_same = False
            all_same = False
    else:
        verbose_print(debug, "Missing raw resources text in one or both environments")
        resources_same = False
        all_same = False
    
    # Compare Validation Models - exact text comparison only
    validation_same = True

    # Compare the raw text directly
    if 'raw_validation_models' in dev_info and 'raw_validation_models' in prod_info:
        dev_models_text = dev_info['raw_validation_models'].strip()
        prod_models_text = prod_info['raw_validation_models'].strip()
        
        verbose_print(debug, f"Dev validation models text length: {len(dev_models_text)}")
        verbose_print(debug, f"Prod validation models text length: {len(prod_models_text)}")
        
        if dev_models_text != prod_models_text:
            verbose_print(debug, "Validation models text doesn't match")
            validation_same = False
            all_same = False
    else:
        verbose_print(debug, "Missing raw validation models text in one or both environments")
        validation_same = False
        all_same = False
    
    # Now build the comparison text with the appropriate status emojis
    comparison = f"## comparison to -prod - {'✅ ALL SAME' if all_same else '⚠️ DIFFERENT'}\n"
    
    comparison += f"{'✅ SAME' if lambda_same else '⚠️ DIFFERENT'} - Lambda config (excluding 'Last Updated')\n"
    comparison += f"{'✅ SAME' if iam_same else '⚠️ DIFFERENT'} - IAM Role policies (excluding extra -dev and -prod inline one if exists)\n"
    comparison += f"{'✅ SAME' if resource_policies_same else '⚠️ DIFFERENT'} - Lambda Resource-Based Policies (checking API Gateway invoke permissions)\n"
    comparison += f"{'✅ SAME' if api_keys_same else '⚠️ DIFFERENT'} - API keys\n"
    comparison += f"{'✅ SAME' if waf_same else '⚠️ DIFFERENT'} - WAF\n"
    comparison += f"{'✅ SAME' if logging_same else '⚠️ DIFFERENT'} - Logging (3 Cloudwatch groups with same prefixes)\n"
    comparison += f"{'✅ SAME' if integration_same else '⚠️ DIFFERENT'} - Integration Configuration\n"
    comparison += f"{'✅ SAME' if resources_same else '⚠️ DIFFERENT'} - Resources\n"
    comparison += f"{'✅ SAME' if validation_same else '⚠️ DIFFERENT'} - Request Validation (Models, model_name, and schema identical)\n"
    
    return comparison
def compare_envs_in_api_state_report(report_file_path):
    """
    Parse an API state report and add a comparison section between dev and prod environments.
    
    :param report_file_path: str, path to the generated API state report
    :return: None
    """
    # Read the file content
    with open(report_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Print file size to verify it's being read correctly
    #print(f"DEBUG: Read file with {len(content)} characters")
    
    # Get the header section (everything before the first API section)
    header_match = re.search(r'^(.*?)(?=# [^\n]+ - stages:)', content, re.DOTALL)
    header = header_match.group(1) if header_match else ""
    
    # Use a simpler approach - split the content by API section markers
    sections = re.split(r'(# [^\n]+ - stages:)', content)
    
    if len(sections) <= 1:
        print("No API sections found using primary pattern. Trying alternative pattern...")
        # Try with a more lenient pattern
        sections = re.split(r'(# [^\n]+:)', content)
        
    if len(sections) <= 1:
        print("Error: Could not parse API sections in the file. Printing first 100 chars:")
        print(content[:100])
        return
    
    # Reconstruct the sections properly
    api_sections = []
    current_api = None
    
    for i, section in enumerate(sections):
        if i == 0:  # This is the header or empty string before first section
            continue
            
        if section.startswith('#'):  # This is a section header
            current_api = section.replace('#', '').replace('- stages:', '').strip()
        elif current_api:  # This is the content of a section
            api_sections.append((current_api, section))
    
    #print(f"DEBUG: Found {len(api_sections)} API sections")
    
    if not api_sections:
        print("No API sections found. The file format may have changed.")
        return
    
    # Build the modified content starting with the header
    modified_content = header
    
    # Process each API section
    for i, (api_name, api_section) in enumerate(api_sections):
        # Check if this is a base app (not the -prod version)
        if not api_name.endswith('-prod'):
            # Look for the corresponding prod version
            prod_api_name = f"{api_name}-prod"
            prod_idx = -1
            
            # Find the prod version of this API in the list
            for j, (name, _) in enumerate(api_sections):
                if name == prod_api_name:
                    prod_idx = j
                    break
            
            if prod_idx != -1:
                # We found matching dev and prod environments
                _, prod_section = api_sections[prod_idx]
                
                # Parse both sections to extract required info
                dev_info = parse_api_state_report_section(api_name, api_section)
                prod_info = parse_api_state_report_section(prod_api_name, prod_section)
                
                # Generate comparison section
                comparison = generate_api_report_env_comparison(api_name, dev_info, prod_info)
                
                # Extract the "Lambda code last updated comment" from both dev and prod sections
                dev_comment_match = re.search(r'### Lambda code last updated comment\n([^\n#]+)', api_section)
                prod_comment_match = re.search(r'### Lambda code last updated comment\n([^\n#]+)', prod_section)
                
                dev_comment = dev_comment_match.group(1).strip() if dev_comment_match else "⚠️ Not found"
                prod_comment = prod_comment_match.group(1).strip() if prod_comment_match else "⚠️ Not found"
                
                # Get the local app.py last updated comment
                try:
                    #print(f"DEBUG: Getting local app.py last updated comment for {api_name}")
                    local_comment = get_last_updated_comment_in_local_app_code(api_name)
                except Exception as e:
                    local_comment = f"⚠️ Error: {str(e)}"
                
                # Generate the app.py last updated comments section
                additional_sections = "\n## app.py last updated comments\n"
                additional_sections += f"-local : {local_comment}\n"
                additional_sections += f"-dev   : {dev_comment}\n"
                additional_sections += f"-prod  : {prod_comment}\n"
                
                                # Get deployment log paths
                dev_log_path, prod_log_path = get_last_deployed_log_file_paths(api_name)
                
                # Format the logs section. Reports live in logs/aws_api_state_reports/,
                # so ../aws_chalice_deploys/... reaches the deploy-log home.
                logs_section = "\n## last deployed logs\n"
                # Format dev log
                if dev_log_path:
                    dev_filename = os.path.basename(dev_log_path)
                    dev_relative_path = f"../aws_chalice_deploys/{api_name}/deployed_dev_logs/{dev_filename}"
                    logs_section += f"-dev   : [{dev_filename}]({dev_relative_path})\n"
                else:
                    logs_section += f"-dev   : No deployment log found\n"
                # Format prod log
                if prod_log_path:
                    prod_filename = os.path.basename(prod_log_path)
                    prod_relative_path = f"../aws_chalice_deploys/{api_name}/deployed_prod_logs/{prod_filename}"
                    logs_section += f"-prod  : [{prod_filename}]({prod_relative_path})\n"
                else:
                    logs_section += f"-prod  : No deployment log found\n"
                
                logs_section += "\n"
                
                # Add logs section to additional_sections
                additional_sections += logs_section

                # Find the first header in the section
                first_header_match = re.search(r'(## [^\n]+)', api_section)
                if first_header_match:
                    insert_pos = first_header_match.start()
                    # Insert comparison and comments sections before the first header
                    api_section = api_section[:insert_pos] + comparison + additional_sections + api_section[insert_pos:]
                else:
                    # If no header found, insert at the beginning after a newline
                    api_section = comparison + additional_sections + api_section
        
        # Add the current section to the modified content
        modified_content += f"# {api_name} - stages:{api_section}"
    
    # Write the modified content back to the file
    with open(report_file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"Added environment comparison sections to: {report_file_path}")
def mrun_compare_envs_in_api_state_report():
    pass
#if __name__ == "__main__":
    report_file_path = "logs/aws_api_state_reports/2025-04-14_173245_API-state_send-email.md"
    compare_envs_in_api_state_report(report_file_path)
def generate_api_state_report(api_gateway_names=None, stages=None, output_folder="logs/aws_api_state_reports", compare_envs=True):
    """
    Generate a comprehensive report on the state of API Gateways and their associated resources.
    
    :param api_gateway_names: list or str, specific API Gateway name(s) to report on, or None for all
    :param stages: list, specific stages to include, or None for all
    :param output_folder: str, directory path to save the report
    :return: str, path to the generated report file
    """ 
    if isinstance(api_gateway_names, str):
        api_gateway_names = [api_gateway_names]
    
    # Default to all API Gateways if none specified
    if api_gateway_names is None:
        api_gateway_names = list(APIS_VALIDATION_ENABLED.keys())
    
    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Initialize API client
    api_client = boto3.client('apigateway')
    
    # Create filename with timestamp
    datetime_now = get_current_datetime_filefriendly()
    # Determine suffix based on API names
    if api_gateway_names is None:
        apps_suffix = "_ALL"
    else:
        # Check if all API names share a common prefix
        if len(api_gateway_names) > 0:
            common_prefix = api_gateway_names[0]
            all_match = all(name.startswith(common_prefix) or name == common_prefix for name in api_gateway_names)
            if all_match:
                apps_suffix = f"_{common_prefix}"
            else:
                apps_suffix = "_various"
        else:
            apps_suffix = "_various"
    report_file_path = f"{output_folder}/{datetime_now}_API-state{apps_suffix}.md"
    
    with open(report_file_path, 'w', encoding='utf-8') as fh:
        fh.write(f"# API Gateway State Report - {datetime_now}\n\n")
        
        # Process each API Gateway
        for api_gateway_name in api_gateway_names:
            # Get API ID
            rest_api_id = None
            try:
                apis = api_client.get_rest_apis()
                api_matches = [api for api in apis['items'] if api['name'] == api_gateway_name]
                
                if not api_matches:
                    fh.write(f"# {api_gateway_name} - No API Gateway found\n\n")
                    continue
                    
                # Check for multiple API Gateways with the same name
                if len(api_matches) > 1:
                    fh.write(f"# {api_gateway_name} - WARNING: Multiple API Gateways found with this name\n\n")
                
                api = api_matches[0]
                rest_api_id = api['id']
            except Exception as e:
                fh.write(f"# {api_gateway_name} - Error: {str(e)}\n\n")
                continue
            
            # Determine which stages exist for this API
            api_stages = []
            try:
                stage_response = api_client.get_stages(restApiId=rest_api_id)
                api_stages = [stage['stageName'] for stage in stage_response['item']]
            except Exception as e:
                fh.write(f"Error getting stages: {str(e)}\n\n")
            
            # If stages is None, use all available stages for this API
            stages_to_process = stages if stages is not None else api_stages
            
            # Create heading with available stages
            available_stages = [s for s in stages_to_process if s in api_stages]
            fh.write(f"# {api_gateway_name} - stages: {', '.join(available_stages)}\n")
            
            # Get REST API details
            try:
                api_details = api_client.get_rest_api(restApiId=rest_api_id)
                description = api_details.get('description', '')
                if description:
                    fh.write(f"{description}\n\n")
            except Exception as e:
                fh.write(f"Error getting API details: {str(e)}\n\n")
            
            # Get all validation models for this API (outside of stage processing)
            validation_models = get_api_validation_models(rest_api_id)
            
            # Process each stage
            for stage_name in stages_to_process:
                if stage_name not in api_stages:
                    continue
                
                # Get comprehensive deployment info for this stage
                deployment_info = get_api_stage_current_config(rest_api_id, stage_name)
                
                # Write stage heading with deployment info
                deployment = deployment_info['deployment']
                fh.write(f"## {stage_name} - active deployment: {deployment.get('id', 'None')} on {deployment.get('date', 'Unknown')}\n")

                # Write last updated comments by extracting app.py code from lambda zip
                full_app_code = get_lambda_code_from_deployment_info(deployment_info)
                last_updated_comment = extract_last_updated_comment(full_app_code)
                fh.write(f"### Lambda code last updated comment\n{last_updated_comment}\n\n")

                # Write last deployment log path
                dev_log_path, prod_log_path = get_last_deployed_log_file_paths(api_gateway_name.replace('-prod', ''))
                app_name = api_gateway_name.replace('-prod', '')
                
                if api_gateway_name.endswith('-prod'):
                    log_path = prod_log_path
                    env_type = "prod"
                else:
                    log_path = dev_log_path
                    env_type = "dev"
                
                if log_path:
                    # Extract just the filename from the path
                    filename = os.path.basename(log_path)
                    # Create a relative link to the file
                    relative_path = f"../../web-shared/aws_chalice/{app_name}/deployed_{env_type}_logs/{filename}"
                    # Format as a Markdown link
                    log_info = f"[{filename}]({relative_path})"
                else:
                    log_info = "No deployment log found"
                    
                fh.write(f"### Lambda last deployed log\n{log_info}\n\n")

                # Write Lambda function details
                lambda_info = deployment_info['lambda']
                if lambda_info.get('name'):
                    fh.write(f"### Lambda config: {lambda_info.get('name')}\n")
                    
                    # Add qualifier information
                    if lambda_info.get('qualifier'):
                        qualifier = lambda_info.get('qualifier')
                        if qualifier == '$LATEST':
                            fh.write("Integration target: $LATEST version (automatically uses most recent code updates)\n")
                        elif qualifier.isdigit():
                            fh.write(f"Integration target: Version {qualifier} (immutable specific version)\n")
                        else:
                            fh.write(f"Integration target: Alias '{qualifier}' (pointer that can be updated to different versions)\n")
                    
                    # Show all integrations if multiple exist
                    if lambda_info.get('integrations') and len(lambda_info.get('integrations', [])) > 1:
                        # Check if they all use the same Lambda function and qualifier
                        first_integration = lambda_info['integrations'][0]
                        all_same = all(
                            integration['function_name'] == first_integration['function_name'] and 
                            integration['qualifier'] == first_integration['qualifier']
                            for integration in lambda_info['integrations']
                        )
                        
                        if not all_same:
                            # Only show the details if they're actually different
                            fh.write("\n#### Multiple Lambda Integrations:\n")
                            for integration in lambda_info.get('integrations', []):
                                fh.write(f"- {integration['resource_path']} ({integration['method']}): {integration['function_name']}:{integration['qualifier']}\n")
                        else:
                            # Just show count of methods using the same Lambda - COMMENT OUT BECAUSE -prod is not showing
                            # method_count = len(lambda_info['integrations'])
                            # fh.write(f"({method_count} API methods use this same Lambda integration)\n")
                            pass
                    
                    if 'error' in lambda_info:
                        fh.write(f"{lambda_info['error']}\n\n")
                    else:
                        fh.write(f"Runtime: {lambda_info.get('runtime', 'Unknown')}\n")
                        fh.write(f"Memory: {lambda_info.get('memory', 'Unknown')} MB\n")
                        fh.write(f"Timeout: {lambda_info.get('timeout', 'Unknown')}s\n")
                        fh.write(f"Environment Variables: {lambda_info.get('env_vars_count', 0)} configured\n")
                        
                        if 'last_modified' in lambda_info:
                            fh.write(f"Last Modified: {lambda_info['last_modified']}\n")
                        
                        # Get Lambda role information
                        try:
                            lambda_client = boto3.client('lambda')
                            function_config = lambda_client.get_function(FunctionName=lambda_info['name'])
                            role_arn = function_config['Configuration'].get('Role')
                            
                            if role_arn:
                                role_info = get_lambda_role_policies(role_arn)
                                role_name = role_info['role_name']
                                
                                fh.write("\n")
                                fh.write(f"### Lambda IAM Role: {role_name}\n")
                                
                                for policy in role_info['policies']:
                                    policy_name = policy['name']
                                    policy_type = policy['type']
                                    fh.write(f"{policy_name} - {policy_type}\n")
                        except Exception as e:
                            fh.write(f"\nError retrieving IAM role information: {str(e)}\n")
                        
                        # Get Lambda resource-based policies
                        try:
                            resource_policies = get_lambda_resource_policies(lambda_info['name'])
                            
                            if resource_policies['policy_statements']:
                                fh.write("\n")
                                fh.write(f"### Lambda Resource-Based Policies: {len(resource_policies['policy_statements'])}\n")
                                
                                for statement in resource_policies['policy_statements']:
                                    sid = statement['sid']
                                    principal = statement['principal'].get('Service', statement['principal'])
                                    action = statement['action']
                                    
                                    # Format condition for display
                                    condition_str = "None"
                                    if statement['condition']:
                                        condition_keys = list(statement['condition'].keys())
                                        if condition_keys:
                                            condition_str = condition_keys[0]
                                    
                                    fh.write(f"{sid} - Principal: {principal}, Action: {action}, Condition: {condition_str}\n")
                            else:
                                fh.write("\n")
                                fh.write(f"### Lambda Resource-Based Policies: 0\n")
                                fh.write("No resource-based policies found\n")
                        except Exception as e:
                            fh.write(f"\nError retrieving resource policies: {str(e)}\n")
                        
                        fh.write("\n")
                else:
                    # No Lambda found
                    fh.write("### Lambda config: NOT FOUND\n")
                    if 'error' in lambda_info:
                        fh.write(f"{lambda_info['error']}\n\n")
                
                # Write API key info
                api_keys = deployment_info['api_keys']
                fh.write(f"### API keys: {api_keys.get('required', False)}\n")
                
                if api_keys.get('required'):
                    if 'error' in api_keys:
                        fh.write(f"{api_keys['error']}\n")
                    elif 'usage_plans' in api_keys:
                        for plan in api_keys['usage_plans']:
                            for key in plan.get('keys', []):
                                fh.write(f"#### API key: {key.get('truncated_value', 'N/A')}  usage plan: {plan.get('name', 'Unknown')}\n\n")
                else:
                    fh.write("No API keys required\n\n")

                # Write WAF info
                waf = deployment_info['waf']
                fh.write(f"### WAF: {'enabled' if waf.get('enabled', False) else 'disabled'}\n")
                
                if waf.get('enabled'):
                    fh.write(f"#### ACL: {waf.get('name', 'Unknown')}\n\n")
                
                # Write logging info
                logging = deployment_info['logging']
                if logging:
                    fh.write("### Logging\n")
                    
                    if 'error' in logging:
                        fh.write(f"{logging['error']}\n\n")
                    else:
                        # API Gateway > Logs and Tracing section
                        fh.write("#### API Gateway > Logs and Tracing\n")
                        fh.write(f"loggingLevel:     {logging.get('level', 'OFF')}\n")
                        fh.write(f"CloudWatch logs:  {'Error and info logs' if logging.get('cloudwatch_logs_enabled', False) else 'Disabled'}\n")
                        fh.write(f"Detailed metrics: {'Active' if logging.get('detailed_metrics', False) else 'Inactive'}\n")
                        fh.write(f"Data tracing:     {'Active' if logging.get('data_tracing', False) else 'Inactive'}\n")
                        fh.write(f"X-Ray tracing:    {'Active' if logging.get('xray_tracing', False) else 'Inactive'}\n")
                        
                        # API Gateway > Custom access logging section
                        custom_access_logging = logging.get('custom_access_logging', {})
                        fh.write(f"#### API Gateway > Custom access logging: {'Active' if custom_access_logging.get('enabled', False) else 'Inactive'}\n")
                        
                        if custom_access_logging.get('enabled', False):
                            # Write log group ARN if available
                            if custom_access_logging.get('log_group_arn'):
                                fh.write(f"{custom_access_logging['log_group_arn']}\n")
                            
                            # Write schema info
                            if custom_access_logging.get('uses_standard_schema', False):
                                fh.write("standard custom access logging schema (12-20-24)\n")
                            elif custom_access_logging.get('format'):
                                # If using non-standard format, show it
                                fh.write(f"{custom_access_logging['format']}\n")
                        
                        # CloudWatch Log Groups section
                        log_groups = logging.get('log_groups', [])
                        if log_groups:
                            fh.write("\n#### Cloudwatch Log Groups\n")
                            for log_group in log_groups:
                                fh.write(f"{log_group}\n")
                        
                        fh.write("\n")
                
                # Write integration info
                integration = deployment_info['integration']
                if integration:
                    fh.write("### Integration Configuration\n")
                    
                    if 'error' in integration:
                        fh.write(f"{integration['error']}\n\n")
                    else:
                        fh.write(f"Type: {integration.get('type', 'Unknown')}\n")
                        
                        if integration.get('timeout_seconds'):
                            fh.write(f"Timeout: {integration['timeout_seconds']}s\n\n")
                
                # Write resources info
                resources = deployment_info['resources']
                if resources:
                    fh.write("### Resources\n")
                    
                    for resource in resources:
                        if 'error' in resource:
                            fh.write(f"{resource['error']}\n\n")
                        else:
                            path = resource.get('path', 'Unknown')
                            methods = resource.get('methods', [])
                            fh.write(f"{path}:\n")
                            for method in methods:
                                fh.write(f"  - {method}\n")
                    fh.write("\n")
            
            # Add validation models section after all stages
            fh.write(f"## Request Validation Models: {len(validation_models)}\n")
            if not validation_models:
                fh.write("No models\n\n")
            else:
                for model_name, schema, content_type, used_by in validation_models:
                    fh.write(f"### Model name: {model_name}\n")
                    
                    # Show where this model is used, if known
                    if used_by:
                        fh.write(f"Used by: {', '.join(used_by)}\n")
                        
                    # Format and write schema
                    try:
                        formatted_schema = json.dumps(schema, indent=2)
                        fh.write(formatted_schema + "\n\n")
                    except (TypeError, ValueError):
                        # Handle case where schema might be a string
                        if isinstance(schema, str):
                            fh.write(f"{schema}\n\n")
            
            # Add deployment history section at the API level after validation models
            fh.write("## Deployment History\n")
            try:
                # Get all deployments with pagination support
                all_deployments = []
                paginator = api_client.get_paginator('get_deployments')
                
                for page in paginator.paginate(restApiId=rest_api_id):
                    all_deployments.extend(page.get('items', []))
                
                # Sort by creation date, most recent first
                sorted_deployments = sorted(
                    all_deployments,
                    key=lambda x: x.get('createdDate', datetime.min),
                    reverse=True
                )
                
                # Get 10 most recent (increasing from 5 to ensure we get all recent ones)
                recent_deployments = sorted_deployments[:10]
                
                if recent_deployments:
                    fh.write(f"Recent deployments ({len(recent_deployments)}):\n")
                    for deployment in recent_deployments:
                        deploy_id = deployment.get('id', 'Unknown')
                        deploy_date = deployment.get('createdDate', 'Unknown date')
                        
                        if isinstance(deploy_date, datetime):
                            # Add time to make it easier to distinguish multiple deployments on same day
                            deploy_date = deploy_date.strftime('%Y-%m-%d %H:%M')
                            
                        description = deployment.get('description', 'No description')
                        fh.write(f"- {deploy_date}: {description} ({deploy_id})\n")
                else:
                    fh.write("No deployments found.\n")
            except Exception as e:
                fh.write(f"Error getting deployment history: {str(e)}\n\n")
            
            fh.write("\n\n") # Extra space between APIs
            
    print(f"Initial API state report written to:  {report_file_path}")
    if compare_envs:
        compare_envs_in_api_state_report(report_file_path)
    return report_file_path
def mrun_generate_api_state_report():
    pass
#if __name__ == "__main__":
    app_name = cur_app_name
    # Generate report for all APIs
    #generate_api_state_report(api_gateway_names=None, output_folder="logs/aws_api_state_reports")
    
    # Or generate report for a specific APIs
    generate_api_state_report([app_name, app_name+"-prod"], output_folder="logs/aws_api_state_reports")



def deploy_lambda_zip(zip_path, target_lambda_function_name, env_variable_changes=None, publish_version=False, version_description=None, logger=None):
    """
    Deploy a locally generated Chalice .zip (from the dev environment) to an existing
    production Lambda function. Optionally update environment variables, publish
    a new Lambda version, and log the deployment.

    :param zip_path: Path to the Chalice deployment .zip file on local filesystem.
    :param target_lambda_function_name: Name of the Lambda function to update (e.g. 'myapp-prod').
    :param env_variable_changes: Dictionary of environment variable changes to CURRENT ones in target lambda (not zip or chalice.json ones).
                          e.g. {"OPENAI_API_KEY": os.environ["OPENAI_API_KEY_PROD"]}
    :param publish_version: If True, publish a new Lambda function version after updating code.
    :param version_description: Optional description for the new published version (if publish_version=True).
    :param logger: Optional logger that provides a .log(msg) method or similar (can be a custom class).
    :return: Dictionary with deployment information:
             {
               "function_name": str,
               "updated_code_sha256": str,
               "published_version": str or None,
               "version_arn": str or None
             }
    """
    if logger:
        logger.log("=== Starting deployment using deploy_lambda_zip ===")
        logger.log(f"  zip_path: {zip_path}")
        logger.log(f"  target_lambda_function_name: {target_lambda_function_name}")
        if env_variable_changes and isinstance(env_variable_changes, dict):
            env_changes_for_log = {k: '[value not logged]' for k in env_variable_changes}
        else:
            env_changes_for_log = env_variable_changes
        logger.log(f"  env_variable_changes: {env_changes_for_log}")
        logger.log(f"  publish_version: {publish_version}")
        logger.log(f"  version_description: {version_description}")
        logger.log(f"  logger: {logger}")
    
    lambda_client = boto3.client('lambda')
    response_data = {
        "function_name": target_lambda_function_name,
        "updated_code_sha256": None,
        "published_version": None,
        "version_arn": None
    }

    # 1) Read the zip file
    try:
        with open(zip_path, 'rb') as f:
            code_bytes = f.read()
    except FileNotFoundError:
        msg = f"Zip file not found at path: {zip_path}"
        if logger:
            logger.log(msg)
        raise FileNotFoundError(msg)

    # 2) Update the Lambda function code
    if logger:
        logger.log(f"Updating Lambda code from zip for function: {target_lambda_function_name} ...")
    try:
        code_response = lambda_client.update_function_code(
            FunctionName=target_lambda_function_name,
            ZipFile=code_bytes,
            Publish=False  # We'll publish below if needed
        )
        
        # Add this wait logic after code update
        waiter = lambda_client.get_waiter('function_updated')
        if logger:
            logger.log("Waiting for Lambda code update to complete...")
        waiter.wait(
            FunctionName=target_lambda_function_name
        )
        
        # CodeSHA256 is the base64-encoded SHA-256 hash of the unencrypted code
        code_sha256 = code_response.get('CodeSha256')
        response_data["updated_code_sha256"] = code_sha256
        if logger:
            logger.log(f"Lambda code updated successfully. CodeSha256={code_sha256}")
    except ClientError as e:
        msg = f"Error updating Lambda code: {str(e)}"
        if logger:
            logger.log(msg)
        raise

    # 3) Update environment variables if overrides are provided
    if env_variable_changes and isinstance(env_variable_changes, dict):
        if logger:
            logger.log("Applying environment variable overrides...")
        try:
            current_config = lambda_client.get_function_configuration(
                FunctionName=target_lambda_function_name
            )
            existing_env = current_config.get('Environment', {}).get('Variables', {})

            # Merge/overwrite the relevant keys
            merged_env = existing_env.copy()
            for k, v in env_variable_changes.items():
                merged_env[k] = v

            # Actually update the Lambda configuration
            lambda_client.update_function_configuration(
                FunctionName=target_lambda_function_name,
                Environment={'Variables': merged_env}
            )
            if logger:
                changed_keys = ", ".join(env_variable_changes.keys())
                logger.log(f"Updated environment variables: {changed_keys}")
                
            # Wait for configuration update to complete before publishing
            waiter = lambda_client.get_waiter('function_updated')
            if logger:
                logger.log("Waiting for Lambda configuration update to complete...")
            waiter.wait(
                FunctionName=target_lambda_function_name
            )
        except ClientError as e:
            msg = f"Error updating environment variables: {str(e)}"
            if logger:
                logger.log(msg)
            raise
    else:
        if logger:
            logger.log("No env_variable_changes provided, skipping environment variable update.")

    # 4) (Optional) Publish a new version if requested
    if publish_version:
        if logger:
            logger.log("Publishing a new Lambda version...")
        try:
            publish_kwargs = {
                'FunctionName': target_lambda_function_name
            }
            if version_description:
                publish_kwargs['Description'] = version_description

            version_response = lambda_client.publish_version(**publish_kwargs)
            published_version = version_response.get('Version')
            version_arn = version_response.get('FunctionArn')

            response_data["published_version"] = published_version
            response_data["version_arn"] = version_arn

            if logger:
                logger.log(f"Published version {published_version} for {target_lambda_function_name}")
                if version_description:
                    logger.log(f"Version description: {version_description}")

        except ClientError as e:
            msg = f"Error publishing new version: {str(e)}"
            if logger:
                logger.log(msg)
            raise
    else:
        if logger:
            logger.log("Not publishing a new version (publish_version=False).")

    return response_data
def mtest_deploy_lambda_zip():
    pass
#if __name__ == "__main__":
    zip_path = 'web-shared/aws_chalice/hmac-hash/.chalice/deployments/2025-04-04_063224_9cc1732dfcca94718655e284f7ee1d2c-python3.11.zip'
    prod_log_path = 'web-shared/aws_chalice/hmac-hash/deployed_prod_logs'
    repo_path = '/Users/randytrue/Documents/Code/corpus-tools/'
    target_lambda = 'hmac-hash-prod'

    env_variable_changes = {
        "USERS_HMAC_SECRET_KEY": os.environ.get("USERS_HMAC_SECRET_KEY", "error_prod_key_not_found_in_dot_env_file")
    }

    datetime = get_current_datetime_filefriendly()
    log_file_path = prod_log_path + '/deploy_prod_log_' + datetime + '.md'
    logger = UnifiedLogger(log_file_path=log_file_path)
    try:
        result = deploy_lambda_zip(
            zip_path=zip_path,
            target_lambda_function_name=target_lambda,
            env_variable_changes=None,#env_variable_changes,
            publish_version=False,#True,
            version_description="Testing Promote dev code from 2025-04-04_063224 WIP logger 0909",
            logger=logger
        )
        logger.log(f"deploy_lambda_zip result: {json.dumps(result, indent=2)}")
    finally:
        # Save logs to your .md file
        logger.save()
        full_log_path = repo_path + log_file_path
        print(f"deploy_lambda_zip log saved to: {full_log_path}")
def get_lambda_zip_from_deployed_log(log_file_path):
    """
    Extract the Lambda zip file path from a deployment log file.
    
    :param log_file_path: str, path to the deployment log file
    :return zip_path: str, relative path to the Lambda zip file or None if not found
    """
    try:
        with open(log_file_path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("Lambda zip created by deployment:") and i + 1 < len(lines):
                    # Return the next line which should contain the zip path
                    zip_path = lines[i + 1].strip()
                    return zip_path
            return None
    except Exception as e:
        print(f"Error in get_lambda_zip_from_deployed_log function: {str(e)}")
        return None
def mtest_get_lambda_zip_from_deployed_log():
    pass
#if __name__ == "__main__":
    log_file_path = 'web-shared/aws_chalice/hmac-hash/deployed_dev_logs/deployed_dev_log_2025-04-06_114140.md'
    zip_path = get_lambda_zip_from_deployed_log(log_file_path)
    print(f"zip_path: {zip_path}")

PROMOTE_PROD_APP_NAME = cur_app_name
COMPOSITE_LOG_FILE_PATH = "web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md"
def fix_post_promote_api_state_report(app_name, post_promote_api_state_report_file_path):
    """
    Update the post-promote API state report to reference the latest prod deployment log.
    
    :param app_name: str, name of the application (e.g., 'hmac-hash')
    :param post_promote_api_state_report_file_path: str, path to the post-promote API state report file
    :return: bool, True if successful, False otherwise
    """
    try:
        # Get the latest prod log file path
        _, latest_prod_log_path = get_last_deployed_log_file_paths(app_name)
        
        if not latest_prod_log_path:
            print(f"Error: Could not find latest prod log for {app_name}")
            return False
            
        # Extract the filename from the full path
        latest_prod_log_filename = os.path.basename(latest_prod_log_path)
        
        # Build the relative path as it should appear in the API state report
        # (reports live under logs/aws_api_state_reports/)
        relative_path = f"../aws_chalice_deploys/{app_name}/deployed_prod_logs/{latest_prod_log_filename}"
        # Create the new line that will replace the old one
        new_prod_log_line = f"-prod  : [{latest_prod_log_filename}]({relative_path})"
        
        # Read the content of the API state report
        with open(post_promote_api_state_report_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find and replace the prod log line
        found_and_replaced = False
        last_deployed_logs_section_found = False
        for i, line in enumerate(lines):
            if not last_deployed_logs_section_found and line.strip().startswith("## last deployed logs"):
                last_deployed_logs_section_found = True
                continue
            
            if last_deployed_logs_section_found and line.strip().startswith("-prod  :"):
                lines[i] = new_prod_log_line + '\n'
                found_and_replaced = True
                break
                
        if not found_and_replaced:
            print(f"Warning: Could not find prod log line in {post_promote_api_state_report_file_path}")
            return False
            
        # Write the updated content back to the file
        with open(post_promote_api_state_report_file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        print(f"Updated post-promote API state report with latest prod log: {latest_prod_log_filename}")
        return True
        
    except Exception as e:
        print(f"Error updating post-promote API state report: {str(e)}")
        return False
def mrun_fix_post_promote_api_state_report():
    pass
#if __name__ == "__main__":
    post_promote_api_state_report_file_path = "logs/aws_api_state_reports/2025-04-09_085840_API-state_hmac-hash.md"
    fix_post_promote_api_state_report(PROMOTE_PROD_APP_NAME, post_promote_api_state_report_file_path)
def add_line_to_top_of_file_but_below_header_lines(file_path, line):
    """
    Add a line to the top of a file but below the header lines.
    The new line is added below the first line and any blank lines or lines starting with #.
    If a line starts with #, the new line will be inserted directly below it.

    :param file_path: str, path to the file to modify.
    :param line: str, line to add below the header lines.
    :return None
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Ensure we have at least one line
    if not lines:
        lines = ['\n']
    
    # Find the position to insert the new line
    # Skip first line, then handle blank lines or lines starting with #
    insert_pos = 1  # Start after the first line
    i = 1
    while i < len(lines):
        current_line = lines[i].strip()
        
        # If we find a line starting with #, insert right after it
        if current_line.startswith('#'):
            insert_pos = i + 1
            break
        # Skip blank lines
        elif not current_line:
            insert_pos = i + 1
            i += 1
            continue
        else:
            # Found a non-blank, non-comment line - insert before this
            break
        
        i += 1
    
    # If insert_pos is beyond the end of the file, append to the end
    if insert_pos >= len(lines):
        lines.append(line + '\n' if not line.endswith('\n') else line)
    else:
        # Insert the new line at the determined position
        lines.insert(insert_pos, line + '\n' if not line.endswith('\n') else line)
    
    with open(file_path, 'w') as f:
        f.writelines(lines)
def mrun_add_line_to_top_of_file_but_below_header_lines():
    pass
#if __name__ == "__main__":
    line = "This is a test line"
    add_line_to_top_of_file_but_below_header_lines(COMPOSITE_LOG_FILE_PATH, line)
def mrun_pre_promote_api_state_report():
    pass
#if __name__ == "__main__":
    dev_api_name = PROMOTE_PROD_APP_NAME
    prod_api_name = f"{dev_api_name}-prod"
    generate_api_state_report(api_gateway_names=[dev_api_name, prod_api_name])
def confirm_action(prompt_message, confirm_char='c', logger=None):
    """
    Prompt the user for confirmation and log the result.
    
    :param prompt_message: str, the message to display to the user
    :param confirm_char: str, the character that indicates confirmation
    :param logger: UnifiedLogger instance or None
    :return: bool, True if confirmed, False otherwise
    """
    print(f"{prompt_message} (Press '{confirm_char}' to continue or any other key to abort): ")
    confirmation = input()
    
    is_confirmed = confirmation.lower() == confirm_char.lower()
    
    if logger:
        if is_confirmed:
            logger.log(f"Action confirmed by user.")
        else:
            logger.log(f"Action cancelled by user.")
    
    return is_confirmed

def promote_to_prod(app_name, version_description, zip_path=None):
    api_state_report_folder = "logs/aws_api_state_reports/"
    pre_promote_api_state_report_file_path = get_last_file_in_folder(api_state_report_folder)
    
    prod_lambda_name = f"{app_name}-prod"
    # Setup log paths early (local-only under root logs/)
    prod_log_folder = get_deploy_logs_dir(app_name, "prod")
    datetime = get_current_datetime_filefriendly()
    prod_log_file_path = prod_log_folder + '/deployed_prod_log_' + datetime + '.md'
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(prod_log_file_path)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger at the beginning
    logger = UnifiedLogger(log_file_path=prod_log_file_path)
    logger.log("===== PROMOTION CONFIRMATION =====")
    logger.log(f"Before promoting {app_name} to production, please review the API state report:")
    logger.log(f"Pre-promote API State Report: {ROOT_FOLDER}{pre_promote_api_state_report_file_path}")
    
    if zip_path is None:
        last_dev_log_path, last_prod_log_path = get_last_deployed_log_file_paths(app_name)
        logger.log(f"last_dev_log_path: {last_dev_log_path}")
        zip_path = get_lambda_zip_from_deployed_log(last_dev_log_path)
        if zip_path is None:
            logger.log(f"Error: No zip path found in {last_dev_log_path}")
            return
        else:
            logger.log(f"extracted zip_path from last_dev_log: {zip_path}")
    else:
        logger.log(f"using provided zip_path: {zip_path}")
    
    # First confirmation
    if not confirm_action("After reviewing the pre-promote API state report, continue with promotion?", 'c', logger):
        return
    logger.log("Continuing with promotion...\n")

    # Extract and save app.py for reference
    zip_app_dot_py_code = get_app_dot_py_code_from_zip(zip_path)
    prod_log_code_file_path = prod_log_file_path.replace('.md', '_app.py')
    with open(prod_log_code_file_path, 'w') as f:
        f.write(zip_app_dot_py_code)
    logger.log(f"Saved app.py code from zip to: {ROOT_FOLDER}{prod_log_code_file_path}")
    
    # Compare full Lambda code between zip and deployed dev version
    logger.log("Comparing full Lambda code between zip file and deployed dev version...")
    
    # Simply call the comparison function directly - it will print any differences to console
    is_same_code = is_same_lambda_code_zip_vs_deployed(zip_path, app_name, 'dev')
    
    if not is_same_code:
        logger.log(f"⚠️ Warning: Zip file code differs from deployed dev Lambda code", is_change=True)
    else:
        logger.log(f"✅ Zip file code matches deployed dev Lambda code")
    
    # Second confirmation
    if not confirm_action("After reviewing the code comparison, continue with promotion?", 'c', logger):
        return
    logger.log("Continuing with promotion...\n")
    
    try:
        result = deploy_lambda_zip(
            zip_path=zip_path,
            target_lambda_function_name=prod_lambda_name,
            env_variable_changes=None,
            publish_version=True,
            version_description=version_description,
            logger=logger
        )
        # Log deploy_lambda_zip result
        logger.log(f"deploy_lambda_zip result: {json.dumps(result, indent=2)}")

        # Run and log post-promote api state report (reverse order want them to appear in log in correct order)
        post_promote_api_state_report_file_path = generate_api_state_report(api_gateway_names=[app_name, prod_lambda_name])
        logger.add_header(f"Post-promote: [{os.path.basename(post_promote_api_state_report_file_path)}](../../../../{post_promote_api_state_report_file_path})")
        logger.add_header(f"Pre-promote: [{os.path.basename(pre_promote_api_state_report_file_path)}](../../../../{pre_promote_api_state_report_file_path})")
        logger.add_header("## API State Reports")
    finally:
        # Save logs to your .md file
        logger.add_header(f"# Promoted Prod Log for {app_name} {datetime}\n")
        logger.save()

        full_prod_log_path = ROOT_FOLDER + prod_log_file_path
        print(f"\npromote_to_prod log for {app_name} saved to: {full_prod_log_path}")

        # Add line to composite log (composite lives at web-shared/aws_chalice/)
        new_log_line = f"{datetime}    __prod__ {app_name}  promote from dev log using lambda zip - {version_description} [log](../../{prod_log_file_path})\n"
        add_line_to_top_of_file_but_below_header_lines(COMPOSITE_LOG_FILE_PATH, new_log_line)
    
    # Fix post-promote api state report to have correct last deployed log path for prod
    # This is a hack to fix the post-promote api state report to have the correct last deployed log path for prod
    # This is because the post-promote api state report is generated from the dev log and the dev log is not updated
    # until the prod log is created.
    fix_post_promote_api_state_report(app_name, post_promote_api_state_report_file_path)
def mrun_promote_to_prod():
    pass
if __name__ == "__main__":
    #zip_path = PROMOTE_TO_PROD_ZIP_PATH
    #description = "Promote live dev version from zip file XXXX"
    zip_path=None
    description = "Promote live dev version for multi-q"
    
    # Check if zip_path is provided and validate that the folder matches the app name
    if zip_path is not None:
        # Extract the folder name from the zip path
        import re
        match = re.search(r'web-shared/aws_chalice/([^/]+)/', zip_path)
        if match:
            folder_name = match.group(1)
            if folder_name != PROMOTE_PROD_APP_NAME:
                raise ValueError(f"Zip path folder '{folder_name}' does not match app name '{PROMOTE_PROD_APP_NAME}'")
        else:
            raise ValueError(f"Could not extract folder name from zip path: {zip_path}")
    
    promote_to_prod(cur_app_name, description, zip_path)

def sub_prod_api_urls_for_dev(file_path, append_suffix='_dev-api-urls'):
    """
    Substitute the prod API URLs with the dev API URLs in the given file.
    
    :param file_path: str, path to the file containing the API URLs
    :param append_suffix: str, suffix to append to the output file name
    """
    # Read the content of the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track replacements
    replacements = []
    
    # Get all globals from current scope
    all_globals = globals()
    
    # Process each API in API_NAME_GLOBALS_MAPPING
    for api_name, suffix in API_NAME_GLOBALS_MAPPING.items():
        # Skip non-prod APIs
        if not suffix.endswith('_PROD'):
            continue
        
        # Get the PROD API URL global variable name
        prod_endpoint_var_name = f"API_ENDPOINT_{suffix}"
        
        # Get the corresponding DEV API URL global variable name
        dev_suffix = suffix[:-5]  # Remove _PROD
        dev_endpoint_var_name = f"API_ENDPOINT_{dev_suffix}"
        
        # Check if both globals exist
        if prod_endpoint_var_name in all_globals and dev_endpoint_var_name in all_globals:
            prod_url = all_globals[prod_endpoint_var_name]
            dev_url = all_globals[dev_endpoint_var_name]
            
            # Replace prod URL with dev URL in content
            if prod_url in content:
                content = content.replace(prod_url, dev_url)
                replacements.append(f"Replaced {prod_url} with {dev_url}")
    
    # Create the output file name
    base_name, ext = os.path.splitext(file_path)
    output_path = f"{base_name}{append_suffix}{ext}"
    
    # Write the modified content to the new file
    with open(output_path, 'w') as f:
        f.write(content)
    
    # Print the replacements
    if replacements:
        print(f"Made {len(replacements)} replacements:")
        for replacement in replacements:
            print(f"  {replacement}")
        print(f"Output saved to: {output_path}")
    else:
        print("No replacements made.")
    
    return output_path
def mrun_sub_prod_api_urls_for_dev():
    pass
#if __name__ == "__main__":
    file_path = "web/webflow-rag-devpage.js"
    sub_prod_api_urls_for_dev(file_path)    


# ===== END OF FILE core/aws-valid.py =====
