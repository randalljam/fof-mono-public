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
    
from core.fileops import *
from core.aws import *

# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
JWT_TEST = os.environ['JWT_03-24']


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
LLM_MODEL_OPTIONS = ["gpt-4o", "gpt-4o-mini", "o3-mini", "deepseek-reasoner", "o3", "o1"]
REMOVE_FIELD = "__REMOVE_FIELD__"  # # Define a sentinel value for field removal

# SKIPPED IMPLEMENTING THIS SCHEMA FOR API GATEWAY VALIDATION 12-16-24 RT
API_ENDPOINT_DEEPGRAM_CALLBACK = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/transcription"
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

API_ENDPOINT_HMAC_HASH = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/generate-hash"
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

API_ENDPOINT_HASH_STORE = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/hash-store"
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

API_ENDPOINT_QRAG_ROUTING = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/qrag-routing"
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

API_ENDPOINT_QRAG_LLM = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/qrag-llm"
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

API_ENDPOINT_SEND_EMAIL = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/send-email"
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
            "maxLength": 10000
        },
        "email_body_html": {
            "type": "string",
            "maxLength": 50000
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

API_ENDPOINT_VRAG_LLM = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/STAGE/vrag-llm"
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
    'hmac-hash': 'HMAC_HASH',
    'qrag-llm': 'QRAG_LLM',
    'qrag-routing': 'QRAG_ROUTING',
    'send-email': 'SEND_EMAIL',
    'vrag-llm': 'VRAG_LLM'
}
LAMBDA_APIS_MAPPING = {
    'deepgram-callback': '[API-GATEWAY-ID]',
    'hash-store': '[API-GATEWAY-ID]',
    'hmac-hash': '[API-GATEWAY-ID]', 
    'qrag-llm': '[API-GATEWAY-ID]',
    'qrag-routing': '[API-GATEWAY-ID]',
    'send-email': '[API-GATEWAY-ID]',
    'vrag-llm': '[API-GATEWAY-ID]'
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
    'hmac-hash': True,
    'qrag-llm': True,
    'qrag-routing': True,
    'send-email': True,
    'vrag-llm': True
}

#cur_lambda_base_name='deepgram-callback'  
cur_lambda_base_name='hmac-hash'
#cur_lambda_base_name='hash-store'
#cur_lambda_base_name='qrag-routing'
#cur_lambda_base_name='qrag-llm'
#cur_lambda_base_name='send-email'
#cur_lambda_base_name='vrag-llm'
all_lambda_base_names = ['deepgram-callback', 'hmac-hash', 'hash-store', 'qrag-routing', 'qrag-llm', 'send-email', 'vrag-llm']

# NOTE: 3-27 DEPRECATED
def get_lambda_configurations(verbose=False):
    """
    Gather all Lambda-related global variables based on naming conventions.

    :param stage: string, deployment stage name to use in API endpoints ('dev', 'prod', etc.).
    :param verbose: boolean, whether to print detailed configuration info.
    :return configurations: dict, dict of dicts with all configurations.
    """
    all_globals = globals()
    configurations = {}
    
    for lambda_name, suffix in API_NAME_GLOBALS_MAPPING.items():
        # Look for API_ENDPOINT_{SUFFIX}, SCHEMA_{SUFFIX}, TEST_REQUESTS_{SUFFIX}
        endpoint_var = f"API_ENDPOINT_{suffix}"
        schema_var = f"SCHEMA_{suffix}"
        test_requests_var = f"TEST_REQUESTS_{suffix}"
        
        # Only include if all required variables exist
        if all(var in all_globals for var in [endpoint_var, schema_var, test_requests_var]):
            # Replace STAGE in endpoint URL with actual stage value
            endpoint_url = all_globals[endpoint_var]
            
            configurations[lambda_name] = {
                'endpoint': endpoint_url,
                'schema': all_globals[schema_var],
                'test_requests': all_globals[test_requests_var]
            }
        else:
            print(f"Warning: Missing configuration variables for {lambda_name}")
            missing = [var for var in [endpoint_var, schema_var, test_requests_var] 
                      if var not in all_globals]
            print(f"  Missing variables: {missing}")
    
    if verbose:
        print("\nLambda Configurations:")
        for lambda_name, config in configurations.items():
            print(f"\n{lambda_name}:")
            print(f"  Endpoint: {config['endpoint']}")
            print(f"  Schema: {json.dumps(config['schema'], indent=2)[:200]}...")
            print(f"  Test Requests: {len(config['test_requests'])} requests defined")
    
    return configurations
def mrun_get_lambda_configurations():
    pass
#if __name__ == "__main__":
    lambda_configs = get_lambda_configurations(verbose=True)
def get_api_endpoint_url(lambda_base_name, stage):
    """
    Get the API endpoint URL for a Lambda function with the correct stage.
    
    :param lambda_base_name: string, base name of the Lambda function (e.g., 'vrag-llm')
    :param stage: string, deployment stage name (e.g., 'dev', 'prod')
    :return endpoint_url: string, the complete API endpoint URL with stage
    """
    # Look up the corresponding API endpoint global variable
    suffix = API_NAME_GLOBALS_MAPPING.get(lambda_base_name)
    if not suffix:
        raise ValueError(f"No API mapping found for Lambda function: {lambda_base_name}")
    
    endpoint_var_name = f"API_ENDPOINT_{suffix}"
    all_globals = globals()
    
    if endpoint_var_name not in all_globals:
        raise ValueError(f"API endpoint not defined for {lambda_base_name} (expected {endpoint_var_name})")
    
    # Get the endpoint URL and replace STAGE with the actual stage value
    endpoint_url = all_globals[endpoint_var_name].replace('STAGE', stage)
    
    return endpoint_url
def mtest_get_api_endpoint_url():
    pass
#if __name__ == "__main__":
    stage = 'dev'
    endpoint_url = get_api_endpoint_url(cur_lambda_base_name, stage)
    print(f"API Endpoint URL for {cur_lambda_base_name} in stage:{stage}\n{endpoint_url}")
def get_test_requests(lambda_base_name):
    """
    Get the test requests for a specific Lambda function.
    
    :param lambda_base_name: string, base name of the Lambda function (e.g., 'vrag-llm')
    :return test_requests: dict, dictionary containing the test requests for the Lambda
    """
    # Look up the corresponding suffix in the mapping
    suffix = API_NAME_GLOBALS_MAPPING.get(lambda_base_name)
    if not suffix:
        raise ValueError(f"No API mapping found for Lambda function: {lambda_base_name}")
    
    # Construct the test requests variable name
    test_requests_var_name = f"TEST_REQUESTS_{suffix}"
    all_globals = globals()
    
    if test_requests_var_name not in all_globals:
        raise ValueError(f"Test requests not defined for {lambda_base_name} (expected {test_requests_var_name})")
    
    # Return the test requests
    return all_globals[test_requests_var_name]
def mtest_get_test_requests():
    pass
#if __name__ == "__main__":
    test_requests = get_test_requests(cur_lambda_base_name)
    print(f"Test requests for {cur_lambda_base_name}:")
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

def test_lambda_requests(lambda_function_base_name, stage, direct_lambda=True, with_gateway=True, debug_prompt=False, output_file="apps/qrag/web/test_back-end_validation.md", jwt_token=None):
    """
    Test requests for any Lambda function both directly and through API Gateway.

    :param lambda_function_base_name: str, base name of the Lambda function (e.g., 'hmac-hash').
    :param stage: str, deployment stage ('dev', 'prod', etc.).
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
    
    # Get AWS Lambda name with stage
    aws_lambda_name = f"{lambda_function_base_name}-{stage}"
    
    # Get API endpoint URL for this Lambda function
    try:
        api_endpoint = get_api_endpoint_url(lambda_function_base_name, stage)
    except ValueError as e:
        raise ValueError(f"Failed to get API endpoint for {lambda_function_base_name}: {str(e)}")
    
    # Get test requests for this Lambda function
    try:
        test_requests = get_test_requests(lambda_function_base_name)
    except ValueError as e:
        raise ValueError(f"Failed to get test requests for {lambda_function_base_name}: {str(e)}")
    
    # Get template request from first clean request
    if not test_requests.get('clean_requests'):
        raise ValueError(f"No clean requests found for {lambda_function_base_name}")
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
    write_to_both(f"\n\n## ====== Testing {lambda_function_base_name}  {now_datetime} ======")
    for category, request_list in test_requests.items():
        write_to_both(f"\n\n## ====== {category} for {lambda_function_base_name} ======")
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
        
        write_to_both(f"\n## ===== API Gateway Validation Test Summary {lambda_function_base_name} =====")
        
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
    stage = 'dev'
    jwt_token = None
    if LAMBDA_JWT_REQUIRED.get(cur_lambda_base_name, False):
        jwt_token = JWT_TEST

    results = test_lambda_requests(cur_lambda_base_name, stage, direct_lambda=True, with_gateway=True, jwt_token=jwt_token)
    #print(colored("TESTING the green color", "green"))
def confirm_lambda_jwt_required(lambda_function_base_name, stage):
    """
    Confirm whether a Lambda function requires JWT by testing through API Gateway with and without JWT token.
    
    :param lambda_function_base_name: str, base name of the Lambda function (e.g., 'qrag-routing').
    :param stage: str, deployment stage ('dev', 'prod', etc.).
    :return: bool, True if the LAMBDA_JWT_REQUIRED setting is confirmed correct, False otherwise.
    """
    print(f"\n===== Testing JWT requirement for {lambda_function_base_name} =====")
    
    # Get expected JWT requirement from global dictionary
    expected_jwt_required = LAMBDA_JWT_REQUIRED.get(lambda_function_base_name, False)
    print(f"Global LAMBDA_JWT_REQUIRED setting: {expected_jwt_required}")
    
    # Get AWS Lambda name with stage
    aws_lambda_name = f"{lambda_function_base_name}-{stage}"
    
    # Get API endpoint URL for this Lambda function
    try:
        api_endpoint = get_api_endpoint_url(lambda_function_base_name, stage)
    except ValueError as e:
        print(f"ERROR: Failed to get API endpoint for {lambda_function_base_name}: {str(e)}")
        return False
    
    # Get test requests for this Lambda function
    try:
        test_requests = get_test_requests(lambda_function_base_name)
    except ValueError as e:
        print(f"ERROR: Failed to get test requests for {lambda_function_base_name}: {str(e)}")
        return False
    
    # Get template request from first clean request
    if not test_requests.get('clean_requests'):
        print(f"ERROR: No clean requests found for {lambda_function_base_name}")
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
    stage = 'dev'
    # Test a specific Lambda
    confirm_lambda_jwt_required(cur_lambda_base_name, stage)
    
    # OR test all Lambdas
    # for lambda_base_name in all_lambda_base_names:
    #     confirm_lambda_jwt_required(lambda_base_name, stage)
    #     print("\n" + "-"*80 + "\n")

def is_validation_setup(api_gateway_name, http_method='POST', verbose=False, print_method_config=False):
    """
    Check if API Gateway validation is set up.

    :param lambda_function_base_name: str, name of the API Gateway
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
    validation_exists = is_validation_setup(cur_lambda_base_name, verbose=True)
    print(f"API Gateway is_validation_setup for {cur_lambda_base_name}: {validation_exists}")
    
    # OR TO CHECK ALL LAMBDAS:
    # for lambda_base_name in all_lambda_base_names:
    #     validation_exists = is_validation_setup(lambda_base_name)
    #     print(f"API Gateway is_validation_setup for {lambda_base_name}: {validation_exists}")
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
                print(f"Warning: Could not update Content-Type header: {e}")

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
    model_id = get_existing_model_id(cur_lambda_base_name)
    print(f"API Gateway get_existing_model_id for {cur_lambda_base_name}: {model_id}")
def get_method_config(rest_api_id, resource_id, http_method):
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
    get_method_config(cur_lambda_base_name)
def get_deployed_model_info(api_gateway_name, stage_name):
    """
    Get validation model info for a specific deployed stage without changing anything.
    
    :param api_gateway_name: Name of the API Gateway
    :param stage_name: Stage name (e.g., 'dev', 'prod')
    :return: Dictionary with model name and schema
    """
    api_client = boto3.client('apigateway')
    
    # Get REST API ID
    apis = api_client.get_rest_apis()
    rest_api_id = None
    for api in apis['items']:
        if api['name'] == api_gateway_name:
            rest_api_id = api['id']
            break
    
    if not rest_api_id:
        print(f"API Gateway '{api_gateway_name}' not found")
        return None
    
    # Get stage to find deployment ID
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
        'deployment_id': deployment_id,
        'models': models,
        'method_models': method_models
    }
def mrun_get_deployed_model_info():
    pass
#if __name__ == "__main__":
    cur_stage = 'dev'
    deployed_model_info = get_deployed_model_info(cur_lambda_base_name, cur_stage)
    print(f"API Gateway get_deployed_model_info for {cur_lambda_base_name} for stage: {cur_stage}\n{deployed_model_info}")
    cur_stage = 'prod'
    deployed_model_info = get_deployed_model_info(cur_lambda_base_name, cur_stage)
    print(f"\nAPI Gateway get_deployed_model_info for {cur_lambda_base_name} for stage: {cur_stage}\n{deployed_model_info}")

class ValidationLogger:
    """Logger class to collect validation setup messages."""
    
    def __init__(self):
        self.messages = []
        self.changes_detected = False
        
    def log(self, message, is_change=False):
        """Log a message and optionally mark it as a change."""
        print(message)  # Still print to console
        self.messages.append(message)
        if is_change:
            self.changes_detected = True
            
    def get_summary(self):
        """Get a summary of all logged messages."""
        return "\n".join(self.messages)
def mrun_setup_request_validation():
    pass
#if __name__ == "__main__":
    setup_request_validation(cur_lambda_base_name)
def setup_request_validation(api_gateway_name, stage, http_method='POST', force_deployment=False):
    """
    Set up request validation for an API Gateway endpoint if enabled.
    Only creates a new deployment if changes were made or forced.
    
    :param api_gateway_name: str, name of the API Gateway
    :param stage: str, deployment stage ('dev' or 'prod') 
    :param http_method: str, HTTP method to validate
    :param force_deployment: bool, if True forces a new deployment even if no changes
    :return: bool, True if successful, False otherwise
    """
    # Initialize logger
    logger = ValidationLogger()
    
    # Check if validation is enabled for this API
    validation_enabled = APIS_VALIDATION_ENABLED.get(api_gateway_name, False)
    if not validation_enabled:
        logger.log(f"Request validation is disabled for API: {api_gateway_name}")
        return True
        
    # Get schema for this API using the API_NAME_GLOBALS_MAPPING
    suffix = API_NAME_GLOBALS_MAPPING.get(api_gateway_name)
    schema = globals().get(f"SCHEMA_{suffix}")
    if not schema:
        logger.log(f"No schema defined for API: {api_gateway_name}")
        return False
    
    # Get API Gateway IDs
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method)
    if not rest_api_id or not resource_id:
        logger.log(f"Failed to get API Gateway IDs for {api_gateway_name}")
        return False
    
    # Create stage-specific model name
    base_model_name = f"{api_gateway_name.replace('-', '')}"
    model_name = f"{base_model_name}{stage.capitalize()}Model"  # e.g., hmachashDevModel or hmachashProdModel
    
    logger.log(f"Using model name: {model_name} for stage: {stage}")
    
    # Get existing model ID and method configuration
    old_model_id = get_existing_model_id(rest_api_id, model_name)
    method_before = get_method_config(rest_api_id, resource_id, http_method)
    
    # Create or update request model
    model_id = create_request_model(rest_api_id, model_name, schema)
    if not model_id:
        return False
    
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
    
    # Create deployment if changes were made or forced
    if logger.changes_detected or force_deployment:
        action = "Forced deployment" if force_deployment and not logger.changes_detected else "Changes detected"
        logger.log(f"{action}, creating new deployment for {api_gateway_name} stage {stage}")
        if not create_api_gateway_deployment(rest_api_id, stage):
            return False
    else:
        logger.log(f"No changes detected, skipping deployment for {api_gateway_name}")
    
    logger.log(f"Successfully completed validation setup for {api_gateway_name}")
    
    # Write a detailed log to a file for reference
    log_dir = "logs/aws_api_deploy"
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
        print(f"Warning: Could not write log file: {e}")
    
    return True
def mrun_setup_request_validation():
    pass
#if __name__ == "__main__":
    is_validation_setup(cur_lambda_base_name)
    if setup_request_validation(cur_lambda_base_name):
        user_continue_response = input("\n*** WAIT 30 SECONDS FOR CHANGE TO TAKE EFFECT *** - Then Press any key to continue or 'x' to exit...").strip().lower()
        if user_continue_response != 'x':
            # Use the same JWT logic as mrun_test_lambda_requests
            jwt_token = None
            if LAMBDA_JWT_REQUIRED.get(cur_lambda_base_name, False):
                jwt_token = JWT_TEST
                
            test_lambda_requests(
                cur_lambda_base_name, 
                direct_lambda=True, 
                with_gateway=True, 
                jwt_token=jwt_token
            )

# TODO: Not tested yet
def toggle_request_validation(api_gateway_name, stage='dev', http_method='POST'):
    """
    Toggle request validation on/off for an API Gateway endpoint and report the state.
    
    :param api_gateway_name: str, name of the API Gateway.
    :param stage: str, deployment stage ('dev' or 'prod')
    :param http_method: str, HTTP method to modify.
    :return success: bool, True if successful, False otherwise.
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Get API Gateway IDs
        rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method)
        if not rest_api_id or not resource_id:
            print(f"Failed to get API Gateway IDs for {api_gateway_name}")
            return False
            
        # Get current method configuration
        method = api_client.get_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod=http_method
        )
        
        # Check if validation is currently enabled
        validation_enabled = ('requestValidatorId' in method and 
                            'requestModels' in method and 
                            'application/json' in method.get('requestModels', {}))
        
        if validation_enabled:
            # Disable validation by removing validator and model references
            patch_operations = [
                {
                    'op': 'remove',
                    'path': '/requestValidatorId'
                },
                {
                    'op': 'remove', 
                    'path': '/requestModels/application~1json'
                }
            ]
            
            api_client.update_method(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                patchOperations=patch_operations
            )
            
            print(f"Request validation for {api_gateway_name} is now: DISABLED")
        else:
            # Get validator ID
            validators = api_client.get_request_validators(restApiId=rest_api_id)
            validator_id = next((v['id'] for v in validators.get('items', []) 
                              if v['validateRequestBody']), None)
            
            if not validator_id:
                print("No request validator found. Please run setup_request_validation first.")
                return False
                
            # Enable validation by adding validator and model references
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
                        'op': 'replace',
                        'path': '/requestModels/application~1json',
                        'value': f"{api_gateway_name.replace('-', '')}Model"
                    }
                ]
            )
            print(f"Request validation for {api_gateway_name} is now: ENABLED")
        
        # Create deployment to apply changes
        if not create_api_gateway_deployment(rest_api_id, stage):
            return False
            
        return True
        
    except ClientError as e:
        print(f"Error toggling validation: {e}")
        return False
def mrun_toggle_request_validation():
    pass
#if __name__ == "__main__":
    api_gateway_name = "hash-store"
    #toggle_request_validation(api_gateway_name)
    #test_lambda_requests(api_gateway_name, direct_lambda=True, with_gateway=True)

'''
IMPORTANT: the chalice deploy script: web-shared/aws_chalice/chalicelib_mirror_deploy.sh
will read whether the API Gateway validation is enabled or disabled
then it will preserve that state by rerunning the setup_request_validation if enabled.
'''

# aws apigateway delete-model --rest-api-id [API-GATEWAY-ID] --model-name hmachashModel


### PROD STAGE
# TODO: def init_prod_stage(lambda_function_base_name, stage='dev', configure_api_gateway=True):
def create_shared_role_for_lambda(lambda_function_base_name, stage='dev', configure_api_gateway=True):
    """
    Create a shared IAM role for a specific Lambda function's dev and prod versions.
    
    This function takes a dev Lambda, copies its permissions to a new role without
    the -dev/-prod suffix, and updates both dev and prod Lambdas to use this role.
    It also configures API Gateway permissions with stage-specific controls.
    
    :param lambda_function_base_name: str, base name of the Lambda function (e.g., 'hmac-hash').
    :param stage: str, source stage to copy permissions from (usually 'dev').
    :param configure_api_gateway: bool, whether to add API Gateway invoke permissions.
    :return success: bool, True if successful, False otherwise.
    """
    iam = boto3.client('iam')
    lambda_client = boto3.client('lambda')
    
    # Get the Lambda function names
    dev_function_name = f"{lambda_function_base_name}-dev"
    prod_function_name = f"{lambda_function_base_name}-prod"
    new_role_name = f"{lambda_function_base_name}-role"
    
    print(f"Creating shared role for: {lambda_function_base_name}")
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
                    api_gateway_name=lambda_function_base_name,
                    http_method='POST',
                    verbose=True
                )
                
                if not api_id or not resource_id:
                    print(f"  ⚠️ Warning: Could not find API Gateway for {lambda_function_base_name}")
                    print(f"  API Gateway permissions will not be configured")
                    configure_api_gateway = False
                else:
                    print(f"  ✅ Found API Gateway for {lambda_function_base_name}: {api_id}")
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
                    Description=f"Shared role for {lambda_function_base_name} Lambda functions"
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
            dev_statement_id = f"{lambda_function_base_name}-dev-allow-apigateway"
            prod_statement_id = f"{lambda_function_base_name}-prod-allow-apigateway"
            
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
        
        print(f"\n✅ Successfully created shared role {new_role_name} for {lambda_function_base_name}")
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
    lambda_function_base_name = 'hmac-hash'  # Default Lambda to process
    create_shared_role_for_lambda(lambda_function_base_name)

#### V1 MONO
def generate_api_state_report_V1MONO(api_gateway_names=None, stages=None, output_path="logs/aws_api_state_reports"):
    """
    Generate a comprehensive report on the state of API Gateways and their associated resources.
    
    :param api_gateway_names: list or str, specific API Gateway name(s) to report on, or None for all
    :param stages: list, specific stages to include (default: ['api', 'dev', 'prod'])
    :param output_path: str, directory path to save the report
    :return: str, path to the generated report file
    """
    if isinstance(api_gateway_names, str):
        api_gateway_names = [api_gateway_names]
    
    # Default to all API Gateways if none specified
    if api_gateway_names is None:
        api_gateway_names = list(LAMBDA_APIS_MAPPING.keys())
    
    # Default stages to check
    if stages is None:
        stages = ['api', 'dev', 'prod']
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Initialize API client
    api_client = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    waf_client = boto3.client('wafv2')
    
    # Create filename with timestamp
    now_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    file_path = f"{output_path}/{now_str}_API-state.md"
    
    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(f"# API Gateway State Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Process each API Gateway
        for api_gateway_name in api_gateway_names:
            # Get API ID
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
            
            # Determine which stages exist for this API
            api_stages = []
            try:
                stage_response = api_client.get_stages(restApiId=rest_api_id)
                api_stages = [stage['stageName'] for stage in stage_response['item']]
            except Exception as e:
                fh.write(f"Error getting stages: {str(e)}\n\n")
            
            # Create heading with available stages
            available_stages = [s for s in stages if s in api_stages]
            fh.write(f"# {api_gateway_name} - stages: {', '.join(available_stages)}\n")
            
            # Get REST API details
            try:
                api_details = api_client.get_rest_api(restApiId=rest_api_id)
                description = api_details.get('description', 'No description')
                if description:
                    fh.write(f"{description}\n\n")
            except Exception as e:
                fh.write(f"Error getting API details: {str(e)}\n\n")
            
            # Process each stage
            for stage_name in stages:
                if stage_name not in api_stages:
                    continue
                
                try:
                    # Get stage details
                    stage = api_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
                    deployment_id = stage.get('deploymentId', 'None')
                    
                    # Get deployment info
                    deployment_date = "Unknown"
                    try:
                        deployment = api_client.get_deployment(
                            restApiId=rest_api_id,
                            deploymentId=deployment_id
                        )
                        if 'createdDate' in deployment:
                            deployment_date = deployment['createdDate'].strftime('%Y-%m-%d %H:%M') 
                            # Add timezone info if available, otherwise use current timezone
                            deployment_date += f" ({datetime.now().astimezone().strftime('UTC%z')})"
                    except:
                        pass
                    
                    fh.write(f"## {stage_name} - active deployment: {deployment_id} on {deployment_date}\n")
                    
                    # Get Lambda function associated with this stage
                    lambda_function_name = None
                    stage_vars = stage.get('variables', {})
                    
                    if 'LambdaFunctionName' in stage_vars:
                        lambda_function_name = stage_vars['LambdaFunctionName']
                    else:
                        # If no stage variable, try the default naming convention
                        lambda_function_name = f"{api_gateway_name}-{stage_name}"
                    
                    # Get Lambda function details
                    if lambda_function_name:
                        fh.write(f"### Lambda: {lambda_function_name}\n")
                        try:
                            lambda_function = lambda_client.get_function(FunctionName=lambda_function_name)
                            config = lambda_function['Configuration']
                            fh.write(f"Runtime: {config.get('Runtime', 'Unknown')}\n")
                            fh.write(f"Memory: {config.get('MemorySize', 'Unknown')} MB\n")
                            fh.write(f"Timeout: {config.get('Timeout', 'Unknown')}s\n")
                            env_vars = config.get('Environment', {}).get('Variables', {})
                            fh.write(f"Environment Variables: {len(env_vars)} configured\n")
                            
                            # Get lambda update date
                            if 'LastModified' in config:
                                modified_date = config['LastModified']
                                # Convert to just date if it's a full timestamp
                                if 'T' in modified_date:
                                    modified_date = modified_date.split('T')[0]
                                fh.write(f"Last Updated: {modified_date}\n")
                            
                            fh.write("\n")
                        except Exception as e:
                            fh.write(f"Error getting Lambda details: {str(e)}\n\n")
                    
                    # Check for API keys
                    try:
                        # See if API has methods that require API key
                        resources = api_client.get_resources(restApiId=rest_api_id)
                        api_key_required = False
                        
                        for resource in resources.get('items', []):
                            if 'resourceMethods' not in resource:
                                continue
                                
                            for method_name, method_info in resource['resourceMethods'].items():
                                method_details = api_client.get_method(
                                    restApiId=rest_api_id,
                                    resourceId=resource['id'],
                                    httpMethod=method_name
                                )
                                if method_details.get('apiKeyRequired', False):
                                    api_key_required = True
                                    break
                            
                            if api_key_required:
                                break
                        
                        fh.write(f"### API keys: {api_key_required}\n")
                        
                        if api_key_required:
                            # Find API keys that work with this API Gateway
                            usage_plans = api_client.get_usage_plans()
                            associated_usage_plans = []
                            
                            for plan in usage_plans.get('items', []):
                                for api_stage in plan.get('apiStages', []):
                                    if api_stage.get('apiId') == rest_api_id and api_stage.get('stage') == stage_name:
                                        associated_usage_plans.append(plan)
                            
                            if associated_usage_plans:
                                for plan in associated_usage_plans:
                                    plan_keys = api_client.get_usage_plan_keys(usagePlanId=plan['id'])
                                    
                                    for key_item in plan_keys.get('items', []):
                                        key_id = key_item['id']
                                        key_detail = api_client.get_api_key(apiKey=key_id, includeValue=True)
                                        key_value = key_detail.get('value', 'N/A')
                                        
                                        # Truncate the key for security
                                        truncated_key = key_value[:5] + "..." if key_value != 'N/A' else 'N/A'
                                        
                                        fh.write(f"#### API key: {truncated_key}  usage plan: {plan['name']}\n")
                            else:
                                fh.write("#### usage plan: No usage plans associated\n")
                    except Exception as e:
                        fh.write(f"Error checking API keys: {str(e)}\n\n")
                    
                    # Check WAF association
                    try:
                        associated_web_acl = None
                        web_acls = waf_client.list_web_acls(Scope='REGIONAL')
                        
                        # For each web ACL, check if it's associated with this API Gateway
                        for web_acl in web_acls.get('WebACLs', []):
                            resources = waf_client.list_resources_for_web_acl(
                                WebACLArn=web_acl['ARN'],
                                ResourceType='API_GATEWAY'
                            )
                            
                            for resource_arn in resources.get('ResourceArns', []):
                                if rest_api_id in resource_arn:
                                    associated_web_acl = web_acl['Name']
                                    break
                            
                            if associated_web_acl:
                                break
                        
                        fh.write(f"\n### WAF: {'enabled' if associated_web_acl else 'disabled'}\n")
                        if associated_web_acl:
                            fh.write(f"#### ACL: {associated_web_acl}\n\n")
                    except Exception as e:
                        fh.write(f"Error checking WAF: {str(e)}\n\n")
                    
                    # IMPROVED: Check Request Validation Models - directly fetch models
                    try:
                        # Get all models for this API
                        models = api_client.get_models(restApiId=rest_api_id)
                        
                        # Find models specific to this stage/API by naming convention
                        stage_models = []
                        
                        api_name_normalized = api_gateway_name.replace("-", "")
                        stage_name_normalized = stage_name.capitalize()
                        expected_model_name = f"{api_name_normalized}{stage_name_normalized}Model"
                        
                        for model in models.get('items', []):
                            model_name = model.get('name')
                            if model_name == expected_model_name:
                                stage_models.append(model)
                                break
                                
                        # For each matched model, show details
                        for model in stage_models:
                            model_name = model.get('name')
                            fh.write(f"### Request Validation Model: {model_name}\n")
                            
                            # Get the full model including schema
                            try:
                                model_detail = api_client.get_model(
                                    restApiId=rest_api_id,
                                    modelName=model_name
                                )
                                
                                schema = model_detail.get('schema')
                                if schema:
                                    try:
                                        # Format schema nicely (it might be a string that needs parsing)
                                        if isinstance(schema, str):
                                            schema_dict = json.loads(schema)
                                            schema_json = json.dumps(schema_dict, indent=2)
                                        else:
                                            schema_json = json.dumps(schema, indent=2)
                                            
                                        fh.write("#### model schema\n")
                                        fh.write(schema_json + "\n\n")
                                    except json.JSONDecodeError:
                                        fh.write(f"#### model schema (raw format)\n{schema}\n\n")
                            except Exception as e:
                                fh.write(f"Error getting model details: {str(e)}\n\n")
                        
                        # If no stage-specific models were found, check if methods use any models
                        if not stage_models:
                            for resource in resources.get('items', []):
                                if 'resourceMethods' not in resource:
                                    continue
                                    
                                for method_name, method_info in resource['resourceMethods'].items():
                                    try:
                                        method_detail = api_client.get_method(
                                            restApiId=rest_api_id,
                                            resourceId=resource['id'],
                                            httpMethod=method_name
                                        )
                                        
                                        request_models = method_detail.get('requestModels', {})
                                        if request_models:
                                            for content_type, model_name in request_models.items():
                                                if model_name:
                                                    fh.write(f"### Request Validation Model: {model_name}\n")
                                                    fh.write(f"Content Type: {content_type}\n")
                                                    
                                                    # Get the model details
                                                    try:
                                                        model_detail = api_client.get_model(
                                                            restApiId=rest_api_id,
                                                            modelName=model_name
                                                        )
                                                        
                                                        schema = model_detail.get('schema')
                                                        if schema:
                                                            try:
                                                                # Format schema nicely
                                                                if isinstance(schema, str):
                                                                    schema_dict = json.loads(schema)
                                                                    schema_json = json.dumps(schema_dict, indent=2)
                                                                else:
                                                                    schema_json = json.dumps(schema, indent=2)
                                                                    
                                                                fh.write("#### model schema\n")
                                                                fh.write(schema_json + "\n\n")
                                                            except json.JSONDecodeError:
                                                                fh.write(f"#### model schema (raw format)\n{schema}\n\n")
                                                    except Exception as e:
                                                        fh.write(f"Error getting model details: {str(e)}\n\n")
                                    except Exception:
                                        continue
                    except Exception as e:
                        fh.write(f"Error checking validation models: {str(e)}\n\n")
                    
                    # Get Logging Configuration
                    try:
                        fh.write("### Logging\n")
                        logging_level = stage.get('methodSettings', {}).get('*/*', {}).get('loggingLevel', 'OFF')
                        logs_enabled = logging_level != 'OFF'
                        
                        fh.write(f"loggingLevel:     {logging_level}\n")
                        fh.write(f"CloudWatch logs:  {'Error and info logs' if logs_enabled else 'Disabled'}\n")
                        
                        metrics_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('metricsEnabled', False)
                        fh.write(f"Detailed metrics: {'Active' if metrics_enabled else 'Inactive'}\n")
                        
                        data_trace_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('dataTraceEnabled', False)
                        fh.write(f"Data tracing:     {'Active' if data_trace_enabled else 'Inactive'}\n")
                        
                        # Check X-Ray tracing
                        xray_enabled = stage.get('tracingEnabled', False)
                        fh.write(f"X-Ray tracing:    {'Active' if xray_enabled else 'Inactive'}\n\n")
                    except Exception as e:
                        fh.write(f"Error checking logging: {str(e)}\n\n")
                    
                    # Get Integration Configuration
                    try:
                        fh.write("### Integration Configuration\n")
                        
                        # Find a POST method to check integration
                        for resource in resources.get('items', []):
                            if 'resourceMethods' not in resource or 'POST' not in resource['resourceMethods']:
                                continue
                            
                            integration = api_client.get_integration(
                                restApiId=rest_api_id,
                                resourceId=resource['id'],
                                httpMethod='POST'
                            )
                            
                            integration_type = integration.get('type', 'Unknown')
                            fh.write(f"Type: {integration_type}\n")
                            
                            if 'timeoutInMillis' in integration:
                                timeout_seconds = integration['timeoutInMillis'] / 1000
                                fh.write(f"Timeout: {timeout_seconds}s\n\n")
                            
                            break
                    except Exception as e:
                        fh.write(f"Error checking integration: {str(e)}\n\n")
                    
                    # Get Resources
                    try:
                        fh.write("### Resources\n")
                        for resource in resources.get('items', []):
                            if 'resourceMethods' in resource:
                                path = resource.get('path', 'Unknown')
                                methods = list(resource['resourceMethods'].keys())
                                fh.write(f"{path}:\n")
                                for method in methods:
                                    fh.write(f"  - {method}\n")
                        fh.write("\n")
                    except Exception as e:
                        fh.write(f"Error listing resources: {str(e)}\n\n")
                    
                    # Get Deployment History
                    try:
                        fh.write("### Deployment History\n")
                        deployments = api_client.get_deployments(restApiId=rest_api_id)
                        
                        # Sort deployments by creation date (most recent first)
                        sorted_deployments = sorted(
                            deployments.get('items', []),
                            key=lambda x: x.get('createdDate', datetime.min),
                            reverse=True
                        )
                        
                        # Get the 5 most recent deployments
                        recent_deployments = sorted_deployments[:5]
                        
                        if recent_deployments:
                            fh.write("Recent deployments (5):\n")
                            for deployment in recent_deployments:
                                deploy_id = deployment.get('id', 'Unknown')
                                deploy_date = deployment.get('createdDate', 'Unknown date')
                                
                                if isinstance(deploy_date, datetime):
                                    deploy_date = deploy_date.strftime('%Y-%m-%d')
                                    
                                description = deployment.get('description', 'No description')
                                fh.write(f"- {deploy_date}: {description} ({deploy_id})\n")
                        else:
                            fh.write("No recent deployments found.\n")
                        fh.write("\n")
                    except Exception as e:
                        fh.write(f"Error getting deployment history: {str(e)}\n\n")
                    
                except Exception as e:
                    fh.write(f"Error processing stage {stage_name}: {str(e)}\n\n")
            
            fh.write("\n") # Extra space between APIs
            
        fh.write(f"\n_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
        
    print(f"API state report written to: {file_path}")
    return file_path

#### V2
def get_validation_models_for_stage(rest_api_id, stage_name):
    """
    Get all validation models that are in use for a specific stage of an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :param stage_name: str, name of the stage
    :return: list of tuples, each containing (model_name, model_schema, source)
             where source is 'method' or 'naming' to indicate how the model was found
    """
    api_client = boto3.client('apigateway')
    results = []
    
    try:
        # Get all resources for this API
        resources = api_client.get_resources(restApiId=rest_api_id)
        
        # Track models used by methods in this stage
        used_models = set()
        
        # Examine each resource and method to find used models
        for resource in resources.get('items', []):
            if 'resourceMethods' not in resource:
                continue
                
            for method_name, method_info in resource['resourceMethods'].items():
                try:
                    # Get detailed method info
                    method_details = api_client.get_method(
                        restApiId=rest_api_id,
                        resourceId=resource['id'],
                        httpMethod=method_name
                    )
                    
                    # Check if this method uses a validation model
                    request_models = method_details.get('requestModels', {})
                    for content_type, model_name in request_models.items():
                        if model_name and model_name != 'Empty':
                            used_models.add(model_name)
                except Exception:
                    continue
        
        # Get details for each used model
        for model_name in used_models:
            try:
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
                            schema_dict = schema  # Keep as string if can't parse
                    else:
                        schema_dict = schema
                        
                    results.append((model_name, schema_dict, 'method'))
            except Exception:
                continue
        
        # If no models were found in methods, check for stage-specific models by convention
        if not used_models:
            try:
                models_response = api_client.get_models(restApiId=rest_api_id)
                for model in models_response.get('items', []):
                    model_name = model.get('name', '')
                    # Check if model name contains the stage name (case insensitive)
                    if stage_name.lower() in model_name.lower():
                        try:
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
                                        schema_dict = schema
                                else:
                                    schema_dict = schema
                                    
                                results.append((model_name, schema_dict, 'naming'))
                        except Exception:
                            continue
            except Exception:
                pass
        
        return results
    
    except Exception as e:
        print(f"Error getting validation models: {str(e)}")
        return []
def get_deployment_info(rest_api_id, deployment_id):
    """
    Get detailed information about a specific API Gateway deployment.
    
    :param rest_api_id: str, ID of the REST API
    :param deployment_id: str, ID of the deployment
    :return: dict, deployment information including creation date, description, etc.
    """
    api_client = boto3.client('apigateway')
    
    try:
        deployment = api_client.get_deployment(
            restApiId=rest_api_id,
            deploymentId=deployment_id
        )
        return deployment
    except Exception as e:
        print(f"Error getting deployment info: {str(e)}")
        return None
def generate_api_state_report_V2(api_gateway_names=None, stages=None, output_path="logs/aws_api_state_reports"):
    """
    Generate a comprehensive report on the state of API Gateways and their associated resources.
    
    :param api_gateway_names: list or str, specific API Gateway name(s) to report on, or None for all
    :param stages: list, specific stages to include (default: ['api', 'dev', 'prod'])
    :param output_path: str, directory path to save the report
    :return: str, path to the generated report file
    """
    if isinstance(api_gateway_names, str):
        api_gateway_names = [api_gateway_names]
    
    # Default to all API Gateways if none specified
    if api_gateway_names is None:
        api_gateway_names = list(LAMBDA_APIS_MAPPING.keys())
    
    # Default stages to check
    if stages is None:
        stages = ['api', 'dev', 'prod']
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Initialize API client
    api_client = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    waf_client = boto3.client('wafv2')
    
    # Create filename with timestamp
    now_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    file_path = f"{output_path}/{now_str}_API-state.md"
    
    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(f"# API Gateway State Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Process each API Gateway
        for api_gateway_name in api_gateway_names:
            # Get API ID
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
            
            # Determine which stages exist for this API
            api_stages = []
            try:
                stage_response = api_client.get_stages(restApiId=rest_api_id)
                api_stages = [stage['stageName'] for stage in stage_response['item']]
            except Exception as e:
                fh.write(f"Error getting stages: {str(e)}\n\n")
            
            # Create heading with available stages
            available_stages = [s for s in stages if s in api_stages]
            fh.write(f"# {api_gateway_name} - stages: {', '.join(available_stages)}\n")
            
            # Get REST API details
            try:
                api_details = api_client.get_rest_api(restApiId=rest_api_id)
                description = api_details.get('description', 'No description')
                if description:
                    fh.write(f"{description}\n\n")
            except Exception as e:
                fh.write(f"Error getting API details: {str(e)}\n\n")
            
            # Process each stage
            for stage_name in stages:
                if stage_name not in api_stages:
                    continue
                
                try:
                    # Get stage details
                    stage = api_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
                    deployment_id = stage.get('deploymentId', 'None')
                    
                    # Get deployment info using the helper function
                    deployment_date = "Unknown"
                    deployment = get_deployment_info(rest_api_id, deployment_id)
                    if deployment and 'createdDate' in deployment:
                        deployment_date = deployment['createdDate'].strftime('%Y-%m-%d %H:%M') 
                        # Add timezone info if available, otherwise use current timezone
                        deployment_date += f" ({datetime.now().astimezone().strftime('UTC%z')})"
                    
                    fh.write(f"\n## {stage_name} - active deployment: {deployment_id} on {deployment_date}\n")
                    
                    # Get Lambda function associated with this stage
                    lambda_function_name = None
                    stage_vars = stage.get('variables', {})
                    
                    if 'LambdaFunctionName' in stage_vars:
                        lambda_function_name = stage_vars['LambdaFunctionName']
                    else:
                        # If no stage variable, try the default naming convention
                        lambda_function_name = f"{api_gateway_name}-{stage_name}"
                    
                    # Get Lambda function details
                    if lambda_function_name:
                        fh.write(f"### Lambda: {lambda_function_name}\n")
                        try:
                            lambda_function = lambda_client.get_function(FunctionName=lambda_function_name)
                            config = lambda_function['Configuration']
                            fh.write(f"Runtime: {config.get('Runtime', 'Unknown')}\n")
                            fh.write(f"Memory: {config.get('MemorySize', 'Unknown')} MB\n")
                            fh.write(f"Timeout: {config.get('Timeout', 'Unknown')}s\n")
                            env_vars = config.get('Environment', {}).get('Variables', {})
                            fh.write(f"Environment Variables: {len(env_vars)} configured\n")
                            
                            # Get lambda update date
                            if 'LastModified' in config:
                                modified_date = config['LastModified']
                                # Convert to just date if it's a full timestamp
                                if 'T' in modified_date:
                                    modified_date = modified_date.split('T')[0]
                                fh.write(f"Last Updated: {modified_date}\n")
                            
                            fh.write("\n")
                        except Exception as e:
                            fh.write(f"Error getting Lambda details: {str(e)}\n\n")
                    
                    # Check for API keys
                    try:
                        # Get resources
                        resources = api_client.get_resources(restApiId=rest_api_id)
                        
                        # See if API has methods that require API key
                        api_key_required = False
                        
                        for resource in resources.get('items', []):
                            if 'resourceMethods' not in resource:
                                continue
                                
                            for method_name, method_info in resource['resourceMethods'].items():
                                method_details = api_client.get_method(
                                    restApiId=rest_api_id,
                                    resourceId=resource['id'],
                                    httpMethod=method_name
                                )
                                if method_details.get('apiKeyRequired', False):
                                    api_key_required = True
                                    break
                            
                            if api_key_required:
                                break
                        
                        fh.write(f"### API keys: {api_key_required}\n")
                        
                        if api_key_required:
                            # Find API keys that work with this API Gateway
                            usage_plans = api_client.get_usage_plans()
                            associated_usage_plans = []
                            
                            for plan in usage_plans.get('items', []):
                                for api_stage in plan.get('apiStages', []):
                                    if api_stage.get('apiId') == rest_api_id and api_stage.get('stage') == stage_name:
                                        associated_usage_plans.append(plan)
                            
                            if associated_usage_plans:
                                for plan in associated_usage_plans:
                                    plan_keys = api_client.get_usage_plan_keys(usagePlanId=plan['id'])
                                    
                                    for key_item in plan_keys.get('items', []):
                                        key_id = key_item['id']
                                        key_detail = api_client.get_api_key(apiKey=key_id, includeValue=True)
                                        key_value = key_detail.get('value', 'N/A')
                                        
                                        # Truncate the key for security
                                        truncated_key = key_value[:5] + "..." if key_value != 'N/A' else 'N/A'
                                        
                                        fh.write(f"#### API key: {truncated_key}  usage plan: {plan['name']}\n")
                            else:
                                fh.write("#### usage plan: No usage plans associated\n")
                    except Exception as e:
                        fh.write(f"Error checking API keys: {str(e)}\n\n")
                    
                    # Check WAF association
                    try:
                        associated_web_acl = None
                        web_acls = waf_client.list_web_acls(Scope='REGIONAL')
                        
                        # For each web ACL, check if it's associated with this API Gateway
                        for web_acl in web_acls.get('WebACLs', []):
                            resources = waf_client.list_resources_for_web_acl(
                                WebACLArn=web_acl['ARN'],
                                ResourceType='API_GATEWAY'
                            )
                            
                            for resource_arn in resources.get('ResourceArns', []):
                                if rest_api_id in resource_arn:
                                    associated_web_acl = web_acl['Name']
                                    break
                            
                            if associated_web_acl:
                                break
                        
                        fh.write(f"### WAF: {'enabled' if associated_web_acl else 'disabled'}\n")
                        if associated_web_acl:
                            fh.write(f"#### ACL: {associated_web_acl}\n\n")
                    except Exception as e:
                        fh.write(f"Error checking WAF: {str(e)}\n\n")
                    
                    # Get Request Validation Models using the helper function
                    try:
                        validation_models = get_validation_models_for_stage(rest_api_id, stage_name)
                        
                        for model_name, schema, source in validation_models:
                            if source == 'naming':
                                fh.write(f"### Request Validation Model: {model_name} (detected by naming)\n")
                            else:
                                fh.write(f"### Request Validation Model: {model_name}\n")
                            
                            # Format and write schema
                            try:
                                formatted_schema = json.dumps(schema, indent=2)
                                fh.write("#### model schema\n")
                                fh.write(formatted_schema + "\n\n")
                            except (TypeError, ValueError):
                                # Handle case where schema might be a string
                                if isinstance(schema, str):
                                    fh.write("#### model schema (raw format)\n")
                                    fh.write(schema + "\n\n")
                    except Exception as e:
                        fh.write(f"Error checking validation models: {str(e)}\n\n")
                    
                    # Get Logging Configuration
                    try:
                        fh.write("### Logging\n")
                        logging_level = stage.get('methodSettings', {}).get('*/*', {}).get('loggingLevel', 'OFF')
                        logs_enabled = logging_level != 'OFF'
                        
                        fh.write(f"loggingLevel:     {logging_level}\n")
                        fh.write(f"CloudWatch logs:  {'Error and info logs' if logs_enabled else 'Disabled'}\n")
                        
                        metrics_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('metricsEnabled', False)
                        fh.write(f"Detailed metrics: {'Active' if metrics_enabled else 'Inactive'}\n")
                        
                        data_trace_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('dataTraceEnabled', False)
                        fh.write(f"Data tracing:     {'Active' if data_trace_enabled else 'Inactive'}\n")
                        
                        # Check X-Ray tracing
                        xray_enabled = stage.get('tracingEnabled', False)
                        fh.write(f"X-Ray tracing:    {'Active' if xray_enabled else 'Inactive'}\n\n")
                    except Exception as e:
                        fh.write(f"Error checking logging: {str(e)}\n\n")
                    
                    # Get Integration Configuration
                    try:
                        fh.write("### Integration Configuration\n")
                        
                        # Find a POST method to check integration
                        for resource in resources.get('items', []):
                            if 'resourceMethods' not in resource or 'POST' not in resource['resourceMethods']:
                                continue
                            
                            integration = api_client.get_integration(
                                restApiId=rest_api_id,
                                resourceId=resource['id'],
                                httpMethod='POST'
                            )
                            
                            integration_type = integration.get('type', 'Unknown')
                            fh.write(f"Type: {integration_type}\n")
                            
                            if 'timeoutInMillis' in integration:
                                timeout_seconds = integration['timeoutInMillis'] / 1000
                                fh.write(f"Timeout: {timeout_seconds}s\n\n")
                            
                            break
                    except Exception as e:
                        fh.write(f"Error checking integration: {str(e)}\n\n")
                    
                    # Get Resources
                    try:
                        fh.write("### Resources\n")
                        for resource in resources.get('items', []):
                            if 'resourceMethods' in resource:
                                path = resource.get('path', 'Unknown')
                                methods = list(resource['resourceMethods'].keys())
                                fh.write(f"{path}:\n")
                                for method in methods:
                                    fh.write(f"  - {method}\n")
                        fh.write("\n")
                    except Exception as e:
                        fh.write(f"Error listing resources: {str(e)}\n\n")
                    
                    # Get Deployment History
                    try:
                        fh.write("### Deployment History\n")
                        deployments = api_client.get_deployments(restApiId=rest_api_id)
                        
                        # Sort deployments by creation date (most recent first)
                        sorted_deployments = sorted(
                            deployments.get('items', []),
                            key=lambda x: x.get('createdDate', datetime.min),
                            reverse=True
                        )
                        
                        # Get the 5 most recent deployments
                        recent_deployments = sorted_deployments[:5]
                        
                        if recent_deployments:
                            fh.write("Recent deployments (5):\n")
                            for deployment in recent_deployments:
                                deploy_id = deployment.get('id', 'Unknown')
                                deploy_date = deployment.get('createdDate', 'Unknown date')
                                
                                if isinstance(deploy_date, datetime):
                                    deploy_date = deploy_date.strftime('%Y-%m-%d')
                                    
                                description = deployment.get('description', 'No description')
                                fh.write(f"- {deploy_date}: {description} ({deploy_id})\n")
                        else:
                            fh.write("No recent deployments found.\n")
                        fh.write("\n")
                    except Exception as e:
                        fh.write(f"Error getting deployment history: {str(e)}\n\n")
                    
                except Exception as e:
                    fh.write(f"Error processing stage {stage_name}: {str(e)}\n\n")
            
            fh.write("\n") # Extra space between APIs
            
        fh.write(f"\n_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
        
    print(f"API state report written to: {file_path}")
    return file_path

#### KEEP FOR ALL VERSIONS
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

#### V3
def get_api_validation_model_info_V3(rest_api_id, stage_name):  # uses name matching which is not what we want
    """
    Get the validation model information for a specific API Gateway stage.
    
    :param rest_api_id: str, ID of the REST API
    :param stage_name: str, name of the stage
    :return: list of tuples, each containing (model_name, model_schema, content_type)
    """
    api_client = boto3.client('apigateway')
    models_info = []
    
    try:
        # Get all resources for this API
        resources = api_client.get_resources(restApiId=rest_api_id)
        
        # Examine each resource and method to find models in use
        for resource in resources.get('items', []):
            if 'resourceMethods' not in resource:
                continue
                
            resource_id = resource['id']
            
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
                        if not model_name or model_name == 'Empty':
                            continue
                            
                        # Get the model details
                        try:
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
                                    
                                # Check if this model is already in our list
                                if not any(model[0] == model_name for model in models_info):
                                    models_info.append((model_name, schema_dict, content_type))
                                    
                        except Exception as e:
                            print(f"Error getting model details for {model_name}: {str(e)}")
                            continue
                            
                except Exception as e:
                    print(f"Error getting method details: {str(e)}")
                    continue
        
        # If no models found in methods, try to find models by naming convention
        if not models_info:
            try:
                # Get all models for this API
                models = api_client.get_models(restApiId=rest_api_id)
                
                for model in models.get('items', []):
                    model_name = model.get('name', '')
                    
                    # Check if model name contains the stage name (case insensitive)
                    if stage_name.lower() in model_name.lower():
                        try:
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
                                        schema_dict = schema
                                else:
                                    schema_dict = schema
                                    
                                models_info.append((model_name, schema_dict, 'application/json'))
                                
                        except Exception as e:
                            print(f"Error getting model details by naming: {str(e)}")
                            continue
            except Exception as e:
                print(f"Error searching for models by naming: {str(e)}")
        
        return models_info
        
    except Exception as e:
        print(f"Error getting validation models: {str(e)}")
        return []
def get_api_stage_deployment_info_V3(rest_api_id, stage_name):
    """
    Get comprehensive information about a specific API Gateway stage deployment.
    
    :param rest_api_id: str, ID of the REST API
    :param stage_name: str, name of the stage
    :return: dict with deployment information
    """
    api_client = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    waf_client = boto3.client('wafv2')
    
    result = {
        'rest_api_id': rest_api_id,
        'stage_name': stage_name,
        'deployment': {},
        'lambda': {},
        'api_keys': {},
        'waf': {},
        'validation_models': [],
        'logging': {},
        'integration': {},
        'resources': [],
        'deployment_history': []
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
        
        # Get associated Lambda function
        lambda_function_name = None
        stage_vars = stage.get('variables', {})
        
        if 'LambdaFunctionName' in stage_vars:
            lambda_function_name = stage_vars['LambdaFunctionName']
        else:
            # Try to infer Lambda name from API name and stage
            try:
                api_details = api_client.get_rest_api(restApiId=rest_api_id)
                api_name = api_details.get('name')
                lambda_function_name = f"{api_name}-{stage_name}"
            except:
                lambda_function_name = None
                
        # Get Lambda function details if available
        if lambda_function_name:
            try:
                lambda_response = lambda_client.get_function(FunctionName=lambda_function_name)
                config = lambda_response['Configuration']
                
                result['lambda'] = {
                    'name': lambda_function_name,
                    'runtime': config.get('Runtime'),
                    'memory': config.get('MemorySize'),
                    'timeout': config.get('Timeout'),
                    'env_vars_count': len(config.get('Environment', {}).get('Variables', {}))
                }
                
                # Get last modified date
                if 'LastModified' in config:
                    modified_date = config['LastModified']
                    # Convert to just date if it's a full timestamp
                    if 'T' in modified_date:
                        modified_date = modified_date.split('T')[0]
                    result['lambda']['last_updated'] = modified_date
            except Exception as e:
                result['lambda'] = {
                    'name': lambda_function_name,
                    'error': f"Error getting Lambda details: {str(e)}"
                }
        
        # Get resources
        resources = api_client.get_resources(restApiId=rest_api_id)
        
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
        
        # Get validation models
        result['validation_models'] = get_api_validation_model_info_V3(rest_api_id, stage_name)
        
        # Get logging configuration
        try:
            logging_level = stage.get('methodSettings', {}).get('*/*', {}).get('loggingLevel', 'OFF')
            metrics_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('metricsEnabled', False)
            data_trace_enabled = stage.get('methodSettings', {}).get('*/*', {}).get('dataTraceEnabled', False)
            xray_enabled = stage.get('tracingEnabled', False)
            
            result['logging'] = {
                'level': logging_level,
                'cloudwatch_logs_enabled': logging_level != 'OFF',
                'detailed_metrics': metrics_enabled,
                'data_tracing': data_trace_enabled,
                'xray_tracing': xray_enabled
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
        
        # Get deployment history
        try:
            deployments = api_client.get_deployments(restApiId=rest_api_id)
            
            # Sort by creation date, most recent first
            sorted_deployments = sorted(
                deployments.get('items', []),
                key=lambda x: x.get('createdDate', datetime.min),
                reverse=True
            )
            
            # Get 5 most recent
            for deployment in sorted_deployments[:5]:
                deploy_id = deployment.get('id')
                deploy_date = deployment.get('createdDate')
                
                if isinstance(deploy_date, datetime):
                    deploy_date = deploy_date.strftime('%Y-%m-%d')
                    
                result['deployment_history'].append({
                    'id': deploy_id,
                    'date': deploy_date,
                    'description': deployment.get('description', 'No description')
                })
        except Exception as e:
            result['deployment_history'] = [{
                'error': f"Error getting deployment history: {str(e)}"
            }]
        
        return result
        
    except Exception as e:
        print(f"Error getting deployment info: {str(e)}")
        return result
def generate_api_state_report_V3(api_gateway_names=None, stages=None, output_path="logs/aws_api_state_reports"):
    """
    Generate a comprehensive report on the state of API Gateways and their associated resources.
    
    :param api_gateway_names: list or str, specific API Gateway name(s) to report on, or None for all
    :param stages: list, specific stages to include (default: ['api', 'dev', 'prod'])
    :param output_path: str, directory path to save the report
    :return: str, path to the generated report file
    """
    if isinstance(api_gateway_names, str):
        api_gateway_names = [api_gateway_names]
    
    # Default to all API Gateways if none specified
    if api_gateway_names is None:
        api_gateway_names = list(LAMBDA_APIS_MAPPING.keys())
    
    # Default stages to check
    if stages is None:
        stages = ['api', 'dev', 'prod']
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Initialize API client
    api_client = boto3.client('apigateway')
    
    # Create filename with timestamp
    now_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    file_path = f"{output_path}/{now_str}_API-state.md"
    
    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(f"# API Gateway State Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
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
            
            # Create heading with available stages
            available_stages = [s for s in stages if s in api_stages]
            fh.write(f"# {api_gateway_name} - stages: {', '.join(available_stages)}\n")
            
            # Get REST API details
            try:
                api_details = api_client.get_rest_api(restApiId=rest_api_id)
                description = api_details.get('description', '')
                if description:
                    fh.write(f"{description}\n\n")
            except Exception as e:
                fh.write(f"Error getting API details: {str(e)}\n\n")
            
            # Process each stage
            for stage_name in stages:
                if stage_name not in api_stages:
                    continue
                
                # Get comprehensive deployment info for this stage
                deployment_info = get_api_stage_deployment_info_V3(rest_api_id, stage_name)
                
                # Write stage heading with deployment info
                deployment = deployment_info['deployment']
                fh.write(f"\n## {stage_name} - active deployment: {deployment.get('id', 'None')} on {deployment.get('date', 'Unknown')}\n")
                
                # Write Lambda function details
                lambda_info = deployment_info['lambda']
                if lambda_info:
                    fh.write(f"### Lambda: {lambda_info.get('name', 'Unknown')}\n")
                    
                    if 'error' in lambda_info:
                        fh.write(f"{lambda_info['error']}\n\n")
                    else:
                        fh.write(f"Runtime: {lambda_info.get('runtime', 'Unknown')}\n")
                        fh.write(f"Memory: {lambda_info.get('memory', 'Unknown')} MB\n")
                        fh.write(f"Timeout: {lambda_info.get('timeout', 'Unknown')}s\n")
                        fh.write(f"Environment Variables: {lambda_info.get('env_vars_count', 0)} configured\n")
                        
                        if 'last_updated' in lambda_info:
                            fh.write(f"Last Updated: {lambda_info['last_updated']}\n")
                        
                        fh.write("\n")
                
                # Write API key info
                api_keys = deployment_info['api_keys']
                fh.write(f"### API keys: {api_keys.get('required', False)}\n")
                
                if api_keys.get('required'):
                    if 'error' in api_keys:
                        fh.write(f"{api_keys['error']}\n")
                    elif 'usage_plans' in api_keys:
                        for plan in api_keys['usage_plans']:
                            for key in plan.get('keys', []):
                                fh.write(f"#### API key: {key.get('truncated_value', 'N/A')}  usage plan: {plan.get('name', 'Unknown')}\n")
                
                # Write WAF info
                waf = deployment_info['waf']
                fh.write(f"### WAF: {'enabled' if waf.get('enabled', False) else 'disabled'}\n")
                
                if waf.get('enabled'):
                    fh.write(f"#### ACL: {waf.get('name', 'Unknown')}\n\n")
                
                # Write validation model info
                validation_models = deployment_info['validation_models']
                for model_name, schema, content_type in validation_models:
                    fh.write(f"### Request Validation Model: {model_name}\n")
                    fh.write(f"Content-Type: {content_type}\n")
                    
                    # Format and write schema
                    try:
                        formatted_schema = json.dumps(schema, indent=2)
                        fh.write("#### model schema\n")
                        fh.write(formatted_schema + "\n\n")
                    except (TypeError, ValueError):
                        # Handle case where schema might be a string
                        if isinstance(schema, str):
                            fh.write("#### model schema (raw format)\n")
                            fh.write(schema + "\n\n")
                
                # Write logging info
                logging = deployment_info['logging']
                if logging:
                    fh.write("### Logging\n")
                    
                    if 'error' in logging:
                        fh.write(f"{logging['error']}\n\n")
                    else:
                        fh.write(f"loggingLevel:     {logging.get('level', 'OFF')}\n")
                        fh.write(f"CloudWatch logs:  {'Error and info logs' if logging.get('cloudwatch_logs_enabled', False) else 'Disabled'}\n")
                        fh.write(f"Detailed metrics: {'Active' if logging.get('detailed_metrics', False) else 'Inactive'}\n")
                        fh.write(f"Data tracing:     {'Active' if logging.get('data_tracing', False) else 'Inactive'}\n")
                        fh.write(f"X-Ray tracing:    {'Active' if logging.get('xray_tracing', False) else 'Inactive'}\n\n")
                
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
                
                # Write deployment history
                history = deployment_info['deployment_history']
                if history:
                    fh.write("### Deployment History\n")
                    
                    if isinstance(history, list) and history and 'error' in history[0]:
                        fh.write(f"{history[0]['error']}\n\n")
                    else:
                        fh.write("Recent deployments (5):\n")
                        for deploy in history:
                            fh.write(f"- {deploy.get('date', 'Unknown date')}: {deploy.get('description', 'No description')} ({deploy.get('id', 'Unknown')})\n")
                    fh.write("\n")
            
            fh.write("\n") # Extra space between APIs
            
        fh.write(f"\n_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
        
    print(f"API state report written to: {file_path}")
    return file_path

#### V4
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
        'rest_api_id': rest_api_id,
        'stage_name': stage_name,
        'deployment': {},
        'lambda': {},
        'api_keys': {},
        'waf': {},
        # Validation models removed - now handled separately
        'logging': {},
        'integration': {},
        'resources': [],
        'deployment_history': []
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
        
        # Get associated Lambda function
        lambda_function_name = None
        stage_vars = stage.get('variables', {})
        
        if 'LambdaFunctionName' in stage_vars:
            lambda_function_name = stage_vars['LambdaFunctionName']
        else:
            # Try to infer Lambda name from API name and stage
            try:
                api_details = api_client.get_rest_api(restApiId=rest_api_id)
                api_name = api_details.get('name')
                lambda_function_name = f"{api_name}-{stage_name}"
            except:
                lambda_function_name = None
                
        # Get Lambda function details if available
        if lambda_function_name:
            try:
                lambda_response = lambda_client.get_function(FunctionName=lambda_function_name)
                config = lambda_response['Configuration']
                
                result['lambda'] = {
                    'name': lambda_function_name,
                    'runtime': config.get('Runtime'),
                    'memory': config.get('MemorySize'),
                    'timeout': config.get('Timeout'),
                    'env_vars_count': len(config.get('Environment', {}).get('Variables', {}))
                }
                
                # Get last modified date
                if 'LastModified' in config:
                    modified_date = config['LastModified']
                    # Convert to just date if it's a full timestamp
                    if 'T' in modified_date:
                        modified_date = modified_date.split('T')[0]
                    result['lambda']['last_updated'] = modified_date
            except Exception as e:
                result['lambda'] = {
                    'name': lambda_function_name,
                    'error': f"Error getting Lambda details: {str(e)}"
                }
        
        # Get resources
        resources = api_client.get_resources(restApiId=rest_api_id)
        
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
            
            result['logging'] = {
                'level': logging_level,
                'cloudwatch_logs_enabled': logging_level != 'OFF',
                'detailed_metrics': metrics_enabled,
                'data_tracing': data_trace_enabled,
                'xray_tracing': xray_enabled
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
        
        # Get deployment history
        try:
            deployments = api_client.get_deployments(restApiId=rest_api_id)
            
            # Sort by creation date, most recent first
            sorted_deployments = sorted(
                deployments.get('items', []),
                key=lambda x: x.get('createdDate', datetime.min),
                reverse=True
            )
            
            # Get 5 most recent
            for deployment in sorted_deployments[:5]:
                deploy_id = deployment.get('id')
                deploy_date = deployment.get('createdDate')
                
                if isinstance(deploy_date, datetime):
                    deploy_date = deploy_date.strftime('%Y-%m-%d')
                    
                result['deployment_history'].append({
                    'id': deploy_id,
                    'date': deploy_date,
                    'description': deployment.get('description', 'No description')
                })
        except Exception as e:
            result['deployment_history'] = [{
                'error': f"Error getting deployment history: {str(e)}"
            }]
        
        return result
        
    except Exception as e:
        print(f"Error getting deployment info: {str(e)}")
        return result
def generate_api_state_report_V4(api_gateway_names=None, stages=None, output_path="logs/aws_api_state_reports"):
    """
    Generate a comprehensive report on the state of API Gateways and their associated resources.
    
    :param api_gateway_names: list or str, specific API Gateway name(s) to report on, or None for all
    :param stages: list, specific stages to include (default: ['api', 'dev', 'prod'])
    :param output_path: str, directory path to save the report
    :return: str, path to the generated report file
    """ 
    if isinstance(api_gateway_names, str):
        api_gateway_names = [api_gateway_names]
    
    # Default to all API Gateways if none specified
    if api_gateway_names is None:
        api_gateway_names = list(LAMBDA_APIS_MAPPING.keys())
    
    # Default stages to check
    if stages is None:
        stages = ['api', 'dev', 'prod']
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Initialize API client
    api_client = boto3.client('apigateway')
    
    # Create filename with timestamp
    now_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    file_path = f"{output_path}/{now_str}_API-state.md"
    
    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(f"# API Gateway State Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
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
            
            # Create heading with available stages
            available_stages = [s for s in stages if s in api_stages]
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
            for stage_name in stages:
                if stage_name not in api_stages:
                    continue
                
                # Get comprehensive deployment info for this stage
                deployment_info = get_api_stage_current_config(rest_api_id, stage_name)
                
                # Write stage heading with deployment info
                deployment = deployment_info['deployment']
                fh.write(f"\n## {stage_name} - active deployment: {deployment.get('id', 'None')} on {deployment.get('date', 'Unknown')}\n")
                
                # Write Lambda function details
                lambda_info = deployment_info['lambda']
                if lambda_info:
                    fh.write(f"### Lambda: {lambda_info.get('name', 'Unknown')}\n")
                    
                    if 'error' in lambda_info:
                        fh.write(f"{lambda_info['error']}\n\n")
                    else:
                        fh.write(f"Runtime: {lambda_info.get('runtime', 'Unknown')}\n")
                        fh.write(f"Memory: {lambda_info.get('memory', 'Unknown')} MB\n")
                        fh.write(f"Timeout: {lambda_info.get('timeout', 'Unknown')}s\n")
                        fh.write(f"Environment Variables: {lambda_info.get('env_vars_count', 0)} configured\n")
                        
                        if 'last_updated' in lambda_info:
                            fh.write(f"Last Updated: {lambda_info['last_updated']}\n")
                        
                        fh.write("\n")
                
                # Write API key info
                api_keys = deployment_info['api_keys']
                fh.write(f"### API keys: {api_keys.get('required', False)}\n")
                
                if api_keys.get('required'):
                    if 'error' in api_keys:
                        fh.write(f"{api_keys['error']}\n")
                    elif 'usage_plans' in api_keys:
                        for plan in api_keys['usage_plans']:
                            for key in plan.get('keys', []):
                                fh.write(f"#### API key: {key.get('truncated_value', 'N/A')}  usage plan: {plan.get('name', 'Unknown')}\n")
                
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
                        fh.write(f"loggingLevel:     {logging.get('level', 'OFF')}\n")
                        fh.write(f"CloudWatch logs:  {'Error and info logs' if logging.get('cloudwatch_logs_enabled', False) else 'Disabled'}\n")
                        fh.write(f"Detailed metrics: {'Active' if logging.get('detailed_metrics', False) else 'Inactive'}\n")
                        fh.write(f"Data tracing:     {'Active' if logging.get('data_tracing', False) else 'Inactive'}\n")
                        fh.write(f"X-Ray tracing:    {'Active' if logging.get('xray_tracing', False) else 'Inactive'}\n\n")
                
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
                
                # Write deployment history
                history = deployment_info['deployment_history']
                if history:
                    fh.write("### Deployment History\n")
                    
                    if isinstance(history, list) and history and 'error' in history[0]:
                        fh.write(f"{history[0]['error']}\n\n")
                    else:
                        fh.write("Recent deployments (5):\n")
                        for deploy in history:
                            fh.write(f"- {deploy.get('date', 'Unknown date')}: {deploy.get('description', 'No description')} ({deploy.get('id', 'Unknown')})\n")
                    fh.write("\n")
            
            # Add validation models section after all stages
            if validation_models:
                fh.write("\n## Request Validation Models\n")
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
            
            fh.write("\n") # Extra space between APIs
            
        fh.write(f"\n_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")
        
    print(f"API state report written to: {file_path}")
    return file_path
def mrun_generate_api_state_report():
    pass
if __name__ == "__main__":
    # Generate report for all APIs
    generate_api_state_report_V4(output_path="logs/aws_api_state_reports")
    
    # Or generate report for a single API
    # generate_api_state_report("hmac-hash", output_path="logs/aws_api_state_reports")

# ===== END OF FILE core/aws-valid.py =====
