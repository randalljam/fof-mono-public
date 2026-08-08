# ===== START OF FILE core/rag.py =====
# Library of functions and execution code to do RAG tasks

import os
from datetime import datetime
from pinecone import Pinecone  # This is correct - imports the Pinecone class
import pinecone  # Add this - imports the module for version info
import pyperclip

from core.vectordb import generate_embedding, convert_date_to_unix
from core.llm import simple_openai_chat_completion_request, deepseek_chat_completion_request_sdk, openai_chat_completion_request_sdk
from core.llm import get_call_cost_from_response, TOKEN_PRICE_DICT
from core.rag_prompts_routes import *
from core.fileops import convert_data_object_to_json_data, get_json_data_from_json_file, verbose_print


# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
 

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

### RETRIEVAL
def pinecone_retriever(query, vector_index_name, num_chunks, date_range=None, debug=False):
    """
    Retrieves relevant question chunks from a Pinecone index based on the input question.
    :param query: string of the input question to search for.
    :param vector_index_name: string of the name of the Pinecone index to query.
    :param num_chunks: integer specifying the number of chunks to retrieve.
    :param date_range: optional list of two dates [start_date, end_date] in ISO format (e.g., ['2021-01-01', '2021-12-31']).
    :return: tuple containing fetched question chunks and a dictionary of retrieved IDs with their scores.
    """
    pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    verbose_print(debug, "DEBUG: Pinecone version:", pinecone.__version__)
    verbose_print(debug, f"DEBUG: Starting pinecone_retriever with date_range={date_range}")
    verbose_print(debug, f"DEBUG: Connecting to index: {vector_index_name}")

    vectorized_query = generate_embedding(query)
    verbose_print(debug, f"DEBUG: Generated embedding of length: {len(vectorized_query)}")
    
    index = pinecone_client.Index(vector_index_name)
    verbose_print(debug, f"DEBUG: Successfully connected to index")
    
    # Prepare query parameters for v6
    query_params = {
        "vector": vectorized_query,
        "top_k": num_chunks,
        "include_metadata": True  # Changed from include_values
    }
    
    # Add date range filter if provided
    if date_range and len(date_range) == 2:
        try:
            # Use UTC-7 (PDT) to match how vectors were created
            utc_offset = -7
            
            # Convert dates to timestamps using UTC-7
            start_date_timestamp_unix = convert_date_to_unix(date_range[0], utc_offset)
            end_date_timestamp_unix = convert_date_to_unix(date_range[1], utc_offset)
            
            verbose_print(debug,f"DEBUG: Converting dates (UTC-7/PDT):")
            verbose_print(debug,f"  Input dates: {date_range[0]} to {date_range[1]}")
            verbose_print(debug,f"  Unix timestamps: {start_date_timestamp_unix} to {end_date_timestamp_unix}")
            
            query_params["filter"] = {
                "DATE": {
                    "$gte": start_date_timestamp_unix,
                    "$lte": end_date_timestamp_unix
                }
            }
            
            # Create a copy of query_params with truncated vector for logging
            log_params = query_params.copy()
            log_params['vector'] = f"[{log_params['vector'][0]:.4f}, ... {len(log_params['vector'])} values]"
            verbose_print(debug,f"DEBUG: Final query_params: {log_params}")
        except Exception as e:
            verbose_print(debug,f"DEBUG: Error in date conversion: {str(e)}")
            raise
    
    # Execute query with v6 API
    verbose_print(debug, "DEBUG: Executing query...")
    query_response = index.query(**query_params)
    verbose_print(debug, f"DEBUG: Query response type: {type(query_response)}")
    verbose_print(debug, f"DEBUG: Query response attributes: {dir(query_response)}")
    # Add full response printing for debugging - outside the hasattr check
    verbose_print(debug, f"DEBUG: Full query response: {query_response}")
    verbose_print(debug, f"DEBUG: Full query response __dict__: {query_response.__dict__}")
    
    # Print just IDs and scores from matches, not full metadata
    if hasattr(query_response, 'matches'):
        matches_summary = [{'id': m.id, 'score': m.score} for m in query_response.matches]
        verbose_print(debug, f"DEBUG: Query response matches (ids and scores): {matches_summary}")
    
    # Extract matches using v6 object attributes
    retrieved_ids_scores = {
        match.id: match.score 
        for match in query_response.matches
    }
    verbose_print(debug, f"DEBUG: Retrieved IDs and scores: {retrieved_ids_scores}")
    
    # Fetch chunks using v6 API
    ids = list(retrieved_ids_scores.keys())
    verbose_print(debug, f"DEBUG: Fetching chunks for IDs: {ids}")
    fetch_response = index.fetch(ids=ids)
    verbose_print(debug, f"DEBUG: Fetch response type: {type(fetch_response)}")
    verbose_print(debug, f"DEBUG: Fetch response attributes: {dir(fetch_response)}")
    
    # Convert fetch response to expected format
    fetched_chunks = {
        id: {
            'metadata': vector.metadata if hasattr(vector, 'metadata') else {},
            'values': vector.values if hasattr(vector, 'values') else None
        }
        for id, vector in fetch_response.vectors.items()
    }

    # Wrap the fetched chunks in a dictionary with key "vectors" because of changes in Pinecone v6 (2-25 RT ugly troubleshooting)
    print("Wrapping fetched chunks in a dictionary with key 'vectors'")
    return {"vectors": fetched_chunks}, retrieved_ids_scores

def filter_same_block_chunks(fetched_chunks, retrieved_ids_scores, num_chunks_keep=None):
    """
    Filters chunks that come from the same QA block, keeping only the one with the highest similarity score.
    This handles cases where multiple questions from the same block are retrieved due to semantic overlap.
    When num_chunks_keep is None, returns all unique chunks (one per block) sorted by similarity score.
    When num_chunks_keep is specified, returns only the top N chunks by similarity score.

    :param fetched_chunks: dictionary containing fetched chunks from Pinecone with 'vectors' key.
    :param retrieved_ids_scores: dictionary of retrieved IDs with their similarity scores.
    :param num_chunks_keep: optional integer specifying the maximum number of chunks to keep after filtering.
    :return: tuple containing filtered chunks dictionary and updated retrieved_ids_scores dictionary.
    """
    # Group chunks by their block ID (everything before the last underscore)
    block_groups = {}
    for chunk_id in fetched_chunks['vectors'].keys():
        # Extract the block ID prefix (everything before the last underscore)
        block_id_prefix = chunk_id.rsplit('_', 1)[0]
        
        if block_id_prefix not in block_groups:
            block_groups[block_id_prefix] = []
        block_groups[block_id_prefix].append((chunk_id, retrieved_ids_scores.get(chunk_id, 0)))

    # For each group, keep only the chunk with highest similarity score
    filtered_chunks = {'vectors': {}}
    filtered_ids_scores = {}
    
    # Process each group and add the best chunk to filtered results
    for group in block_groups.values():
        # Sort by similarity score (descending) and get the highest scoring chunk
        best_chunk_id, best_score = max(group, key=lambda x: x[1])
        
        # Add the best chunk to the filtered results
        filtered_chunks['vectors'][best_chunk_id] = fetched_chunks['vectors'][best_chunk_id]
        filtered_ids_scores[best_chunk_id] = best_score
    
    # Sort the filtered_ids_scores by score in descending order
    sorted_ids_scores = dict(sorted(filtered_ids_scores.items(), key=lambda item: item[1], reverse=True))
    
    # If num_chunks_keep is specified, limit the results to the top N chunks
    if num_chunks_keep is not None and num_chunks_keep > 0:
        # Get the top chunk_ids
        top_chunk_ids = list(sorted_ids_scores.keys())[:num_chunks_keep]
        
        # Create new dictionaries with only the top chunks
        limited_ids_scores = {chunk_id: sorted_ids_scores[chunk_id] for chunk_id in top_chunk_ids}
        limited_chunks = {'vectors': {}}
        
        for chunk_id in top_chunk_ids:
            if chunk_id in filtered_chunks['vectors']:
                limited_chunks['vectors'][chunk_id] = filtered_chunks['vectors'][chunk_id]
        
        # Replace the full dictionaries with the limited ones
        sorted_ids_scores = limited_ids_scores
        sorted_chunks = limited_chunks
    else:
        # Create a new filtered_chunks dictionary with chunks in the same order as sorted_ids_scores
        sorted_chunks = {'vectors': {}}
        for chunk_id in sorted_ids_scores.keys():
            sorted_chunks['vectors'][chunk_id] = filtered_chunks['vectors'][chunk_id]
    
    return sorted_chunks, sorted_ids_scores

### VRAG
def print_vrag_display_text(vrag_json_object, show_prompt=False):
    """
    Prints a formatted display text for VRAG (Vector Retrieval Augmented Generation) results.

    :param vrag_json_object: dictionary containing VRAG results with 'content' key.
    :param show_prompt: boolean to determine whether to show the full LLM prompt.
    :return: None.
    """
    user_question = vrag_json_object['content']['user_question']
    ai_answer = vrag_json_object['content']['ai_answer']
    
    display_text = f"USER QUESTION: {user_question}\n\n"
    
    if show_prompt:
        llm_prompt = vrag_json_object['content']['llm_prompt']
        display_text += f"LLM PROMPT:\n{llm_prompt}\n\n"
    else:
        chunk_texts = vrag_json_object['content']['chunk_texts']
        display_text += f"RETRIEVED CHUNKS:\n{chunk_texts}\n\n"
    
    display_text += f"AI ANSWER: {ai_answer}"
    
    print(display_text)

# TODO: update for deepseek-reasoner
def vrag_llm_call(user_question, vector_index_name, num_chunks, vrag_preamble=VRAG_PREAMBLE_V1, llm_model='deepseek-reasoner', user_id='default', vrag_version="1.0"):
    """
    Initiates a chat session using vector retrieval augmented generation (VRAG) with a specified question,
    prompt template, and index name. Returns a JSON object with the results.

    :param user_question: string of the question to initiate the chat with.
    :param vector_index_name: string of the name of the pinecone index to use for retrieval.
    :param num_chunks: integer specifying the number of chunks to retrieve.
    :param vrag_preamble: string of the preamble used to format the chat prompt.
    :param llm_model: string of the language model to use.
    :param user_id: string of the user identifier.
    :param bot_version: string of the bot version.
    :return: dictionary containing the chat response and metadata.
    """
    fetched_chunks, retrieved_ids_scores = pinecone_retriever(user_question, vector_index_name, num_chunks)
    chunk_texts = ''
    for chunk_id, chunk_data in fetched_chunks['vectors'].items():
        text = chunk_data['metadata'].get('text', '')
        if text:
            chunk_texts += text + '\n'
    chunk_texts = chunk_texts.rstrip('\n')  # Remove trailing newline if present

    llm_prompt = vrag_preamble + "\n" + chunk_texts + "\nUSER QUESTION: " + user_question + "\n\nAI ANSWER: "
    ai_answer = simple_openai_chat_completion_request(llm_prompt, model=llm_model)
    
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "vector_index_name": vector_index_name,
            "vrag_version": vrag_version,
            "llm_model": llm_model,
            "vrag_info": {
                "vrag_preamble": vrag_preamble,
                "num_chunks": len(fetched_chunks['vectors'])
            }
        },
        "content": {
            "user_question": user_question,
            "chunk_texts": chunk_texts,
            "llm_prompt": llm_prompt,
            "ai_answer": ai_answer
        }
    }
 

### QRAG
def transform_and_sort_chunks_by_stars(retrieved_qa_chunks, retrieved_ids_scores, num_chunks):
    """
    Sorts chunks primarily by star rating and then by similarity score, returning the top `num_chunks`.
    Converts 'STARS' to integer and sets to 0 if blank.

    :param retrieved_qa_chunks: dictionary of fetched question chunks from Pinecone.
    :param retrieved_ids_scores: dictionary of retrieved IDs with their similarity scores.
    :param num_chunks: integer specifying the number of chunks to return.
    :return: list of sorted chunks.
    """
    # Extract chunks and their metadata
    chunks = []
    for chunk_id, chunk_data in retrieved_qa_chunks['vectors'].items():
        metadata = chunk_data['metadata']
        metadata['id'] = chunk_id
        metadata['sim_score'] = retrieved_ids_scores.get(chunk_id, 0)
        # Convert STARS to integer, set to 0 if blank
        metadata['STARS'] = int(metadata.get('STARS', 0)) if metadata.get('STARS') else 0
        chunks.append(metadata)

    # Sort chunks by star rating (descending) and then by similarity score (descending)
    sorted_chunks = sorted(chunks, key=lambda x: (-x['STARS'], -x['sim_score']))

    # Return the top `num_chunks` chunks
    return sorted_chunks[:num_chunks]

def transform_and_sort_chunks_by_sim(retrieved_qa_chunks, retrieved_ids_scores, num_chunks):
    """
    Sorts chunks primarily by similarity score and returns the top `num_chunks`.
    Converts 'STARS' to integer and sets to 0 if blank, but doesn't use it for sorting.

    :param retrieved_qa_chunks: dictionary of fetched question chunks from Pinecone.
    :param retrieved_ids_scores: dictionary of retrieved IDs with their similarity scores.
    :param num_chunks: integer specifying the number of chunks to return.
    :return: list of sorted chunks.
    """
    # Extract chunks and their metadata
    chunks = []
    for chunk_id, chunk_data in retrieved_qa_chunks['vectors'].items():
        metadata = chunk_data['metadata']
        metadata['id'] = chunk_id
        metadata['sim_score'] = retrieved_ids_scores.get(chunk_id, 0)
        # Convert STARS to integer, set to 0 if blank
        metadata['STARS'] = int(metadata.get('STARS', 0)) if metadata.get('STARS') else 0
        chunks.append(metadata)

    # Sort chunks by similarity score in descending order
    sorted_chunks = sorted(chunks, key=lambda x: x['sim_score'], reverse=True)

    # Return the top `num_chunks` chunks
    return sorted_chunks[:num_chunks]

def parse_chunks(chunks):
    """ 
    Parses a list of chunks and returns a list of dictionaries containing formatted chunk information.
    Maps QA block fields (CLARIFIED_QUESTION/ANSWER) to standard QUESTION/ANSWER fields.

    :param chunks: list of chunk metadata dictionaries.
    :return: list of parsed chunk dictionaries.
    """
    parsed_chunks = []
    for chunk in chunks:
        chunk_id = chunk['id']
        sim_score = chunk['sim_score']  # Get sim_score directly from the chunk

        # Map CLARIFIED_QUESTION/ANSWER fields to QUESTION/ANSWER fields if present
        question = (
            chunk.get('CLARIFIED QUESTION') or  # Try CLARIFIED_QUESTION first
            chunk.get('QUESTION')  # Fall back to standard fields
        )
        if question is None:
            raise ValueError("Missing required question field in chunk")

        answer = (
            chunk.get('CLARIFIED ANSWER') or  # Try CLARIFIED_ANSWER first
            chunk.get('ANSWER')  # Fall back to standard fields
        )
        if answer is None:
            raise ValueError("Missing required answer field in chunk")

        parsed_chunk = {
            "question": question,
            "answer": answer,
            "verbatim_question": chunk.get("VERBATIM QUESTION", ""),
            "verbatim_answer": chunk.get("VERBATIM ANSWER", ""),
            "speaker_question": chunk.get("SPEAKER QUESTION", ""),
            "speaker_answer": chunk.get("SPEAKER ANSWER", ""),
            "topics": chunk.get("TOPICS", ""),
            'source': str(chunk.get('SOURCE', 'No source')),
            "timestamp": chunk.get("TIMESTAMP", "No timestamp"),
            "stars": int(chunk.get("STARS", 0)),
            "sim": float(sim_score),
            "display": (
                f"ANSWER STARS: {int(chunk.get('STARS', 0))}\n"
                f"QUESTION SIMILARITY SCORE: {round(sim_score * 100)}%"
            ),
        }
        parsed_chunks.append(parsed_chunk)
    return parsed_chunks

def qrag_routing_call(user_question, vector_index_name, num_chunks, routes_dict,
                      date_range=None, routes_bounds=[0.3, 0.9],
                      user_id='default', user_context=None, qrag_version="2.0"):
    """
    Routes a user question through a question retrieval augmented generation (QRAG) process.

    :param user_question: str, the question asked by the user.
    :param vector_index_name: str, name of the vector index to search.
    :param num_chunks: int, number of chunks to retrieve and process.
    :param routes_dict: dict, containing routing information and templates.
    :param date_range: optional list of two dates [start_date, end_date] in ISO format.
    :param routes_bounds: list, lower and upper similarity bounds for routing.
    :param user_id: str, identifier for the user.
    :param user_context: dict, optional context about the user.
    :param qrag_version: str, version of the QRAG system.
    :return response: dict, containing metadata and content of the QRAG response.
    """
    routes_flow_name = "3 routes, separate route prompts"

    # Retrieve chunks from Pinecone
    chunk_retrieval_multiplier = 4  # factor to account for duplicates that will be filtered out
    retrieved_chunks, retrieved_ids_scores = pinecone_retriever(user_question, vector_index_name, 
                                                            num_chunks * chunk_retrieval_multiplier, 
                                                            date_range)

    # Filter out duplicate questions from same chunks, keeping highest similarity
    filtered_chunks, filtered_ids_scores = filter_same_block_chunks(retrieved_chunks, retrieved_ids_scores)

    # Transform and sort chunks by sim score (descending)
    transformed_chunks = transform_and_sort_chunks_by_sim(filtered_chunks, filtered_ids_scores, num_chunks)

    # Parse the filtered chunks
    parsed_chunks = parse_chunks(transformed_chunks)

    # Construct the quoted_qa by iterating over parsed chunks
    # This duplicated text is provided for ease of use by downstream web javascript code
    quoted_qa_list = []
    for chunk in parsed_chunks:
        # Map the fields to match the template expectations
        template_fields = {
            "question": chunk["question"],
            "answer": chunk["answer"],
            "verbatim_question": chunk.get("verbatim_question", ""),
            "verbatim_answer": chunk.get("verbatim_answer", ""),
            "speaker_question": chunk.get("speaker_question", ""),
            "speaker_answer": chunk.get("speaker_answer", ""),
            "topics": chunk.get("topics", ""),
            "source": chunk["source"],
            "timestamp": chunk["timestamp"],
            "display": chunk["display"]
        }
        chunk_formatted = routes_dict['quoted_qa_item_template'].format(**template_fields)
        quoted_qa_list.append(chunk_formatted)

    quoted_qa_formatted = ''.join(quoted_qa_list)
    quoted_qa = routes_dict['quoted_qa_template'].format(quoted_qa_formatted=quoted_qa_formatted)

    # Determine max similarity and stars
    max_sim = max(chunk['sim'] for chunk in parsed_chunks) if parsed_chunks else 0
    max_stars = max(chunk['stars'] for chunk in parsed_chunks) if parsed_chunks else 0
    lower_sim_bound, upper_sim_bound = routes_bounds

    if max_sim >= upper_sim_bound:
        route_preamble = routes_dict['route_preamble_good_match']
        prompt_initial = routes_dict['prompt_initial_good_match']
    elif max_sim <= lower_sim_bound:
        route_preamble = routes_dict['route_preamble_no_match']
        prompt_initial = routes_dict['prompt_initial_no_match']
        quoted_qa = ""
    else:
        route_preamble = routes_dict['route_preamble_partial_match']
        prompt_initial = routes_dict['prompt_initial_partial_match']

    # Prepare chunk metadata for the response
    chunks_metadata = []
    for chunk in parsed_chunks:
        chunks_metadata.append({
            "question": chunk['question'],
            "source": chunk['source'],
            "timestamp": chunk['timestamp'],
            "answer": chunk['answer'],
            "stars": chunk['stars'],
            "sim": "{:.3f}".format(chunk['sim'])
        })

    # Build the final JSON response
    qrag_routing_output_json_object = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            # Add user_context if provided
            **({"user_context": user_context} if user_context else {}),
            "vector_index_name": vector_index_name,
            "qrag_version": qrag_version,
            "routes_info": {
                "routes_flow_name": routes_flow_name,
                "upper_sim_bound": upper_sim_bound,
                "lower_sim_bound": lower_sim_bound,
                "max_sim": "{:.3f}".format(max_sim),
                "max_stars": max_stars,
                "routes_dict_content": routes_dict
            }
        },
        "content": {
            "user_question": user_question,
            "route_preamble": route_preamble,
            "prompt_initial": prompt_initial,
            "quoted_qa": quoted_qa,
            "ai_answer": "WAITING FOR AI ANSWER - using high quality reasoning model so it may take 30-60 seconds...",
            "retrieved_content": {
                "max_sim": "{:.3f}".format(max_sim),
                "max_stars": max_stars,
                "chunks": chunks_metadata
            }
        }
    }

    # Add date range if provided
    if date_range is not None:
        qrag_routing_output_json_object["metadata"]["date_range"] = date_range
    
    return qrag_routing_output_json_object

LLM_MODEL_OPTIONS_QRAG_LLM_CALL = ["gpt-5.4", "gpt-4o", "gpt-4o-mini", "o3-mini", "deepseek-reasoner"]  # sync these with aws_valid.LLM_MODEL_OPTIONS
def qrag_llm_call(qrag_json_object, llm_model='gpt-5.4', large_context=None, large_context_filename=None, reasoning_effort='medium'):
    """ 
    Generates an AI answer for a given JSON object containing question and context information.

    :param qrag_json_object: dictionary containing the question, context, and metadata for generating an AI answer.
    :param llm_model: str, name of the language model to use.
    :param large_context: str, optional text content of the large context file.
    :param large_context_filename: str, optional filename of the large context file.
    :param reasoning_effort: str, optional reasoning effort level ('low', 'medium', 'high').
    :return: dictionary with the updated JSON object including the AI-generated answer.
    """
    # Check that large_context and large_context_filename are either both present or both None
    if bool(large_context) != bool(large_context_filename):
        raise ValueError("Both large_context and large_context_filename must be provided together or both must be None")
    
    # Verify necessary fields exist in the JSON object
    required_fields = ['user_question', 'prompt_initial', 'quoted_qa']
    missing_fields = [field for field in required_fields if field not in qrag_json_object['content']]
    if missing_fields:
        raise ValueError(f"Missing required fields in JSON object: {', '.join(missing_fields)}")

    # Extract necessary information from qrag_json_object
    user_question = qrag_json_object['content']['user_question']
    prompt_initial = qrag_json_object['content']['prompt_initial']
    quoted_qa = qrag_json_object['content']['quoted_qa']
    
    # Update metadata with LLM model
    qrag_json_object['metadata']['llm_model'] = llm_model
    
    # Store large context filename if provided but not the text content
    if large_context_filename:
        qrag_json_object['content']['large_context_filename'] = large_context_filename
    
    # Prepare the prompt for the LLM call
    llm_full_prompt = (
        f"{prompt_initial.strip()}\n\n"
        f"<USER_QUESTION>\n{user_question}\n</USER_QUESTION>\n\n"
        f"<QUOTED_QA>\n{quoted_qa}\n</QUOTED_QA>\n\n"
    )

    # Only add large context section if it exists
    if large_context:
        llm_full_prompt += f"<LARGE_CONTEXT>\n{large_context}\n</LARGE_CONTEXT>\n\n"

    # Make the LLM call
    llm_messages = [{"role": "user", "content": llm_full_prompt}]

    if llm_model == 'deepseek-reasoner':
        llm_response = deepseek_chat_completion_request_sdk(llm_messages, model=llm_model)
        qrag_json_object['content']['reasoning_steps'] = llm_response.choices[0].message.reasoning_content
    elif llm_model in LLM_MODEL_OPTIONS_QRAG_LLM_CALL:
        llm_response = openai_chat_completion_request_sdk(messages=llm_messages, model=llm_model, reasoning_effort=reasoning_effort)
    else:
        raise ValueError("Currently only the following LLM models are supported for qrag_llm_call: " + ", ".join(LLM_MODEL_OPTIONS_QRAG_LLM_CALL))
    
    # Store only selected parts of the response in the json object
    qrag_json_object['content']['ai_answer'] = llm_response.choices[0].message.content
    
    # Store token counts from response
    if hasattr(llm_response, 'usage') and llm_response.usage:
        qrag_json_object['content']['input_tokens'] = getattr(llm_response.usage, 'prompt_tokens', 0)
        qrag_json_object['content']['output_tokens'] = getattr(llm_response.usage, 'completion_tokens', 0)
        if hasattr(llm_response.usage, 'completion_tokens_details') and llm_response.usage.completion_tokens_details:
            reasoning_tokens = getattr(llm_response.usage.completion_tokens_details, 'reasoning_tokens', 0)
            if reasoning_tokens:
                qrag_json_object['content']['reasoning_tokens'] = reasoning_tokens
        if hasattr(llm_response.usage, 'prompt_tokens_details') and llm_response.usage.prompt_tokens_details:
            cached_input_tokens = getattr(llm_response.usage.prompt_tokens_details, 'cached_tokens', 0)
            if cached_input_tokens:
                qrag_json_object['content']['cached_input_tokens'] = cached_input_tokens
    
    # Store reasoning_effort in metadata if provided
    if reasoning_effort:
        qrag_json_object['metadata']['reasoning_effort'] = reasoning_effort
    
    cost_pennies_mycalc = get_call_cost_from_response(llm_response, llm_model, TOKEN_PRICE_DICT, verbose=False)
    qrag_json_object['content']['cost_pennies_mycalc'] = cost_pennies_mycalc

    return qrag_json_object

def qrag_2step(user_question, vector_index_name, num_chunks, routes_dict,
               date_range=None, llm_model='gpt-5.4', large_context_filename=None,
               large_context_folder="data/large_context_files", verbose=False):
    """ 
    Performs a two-step question-answering process using QRAG (Question Retrieval Augmented Generation).

    :param user_question: str, the question asked by the user.
    :param vector_index_name: str, name of the vector index to search.
    :param num_chunks: int, number of chunks to retrieve and process.
    :param routes_dict: dict, containing routing information and templates.
    :param date_range: optional list of two dates [start_date, end_date] in ISO format.
    :param llm_model: str, name of the language model to use.
    :param large_context_filename: str, optional filename of large context file.
    :param large_context_folder: str, path to folder containing large context files.
    :param verbose: bool, control debug output.
    :return: qrag_json_object: dict, containing the QRAG response.
    """
    from core.fileops import pretty_print_json_data, get_current_datetime_filefriendly
    from core.llm import write_json_file_from_json_data

    print("Running qrag_2step...")

    # Create JSON object with routing information
    print(f"Calling qrag_routing_call with parameters:\n"
          f"  user_question: {user_question}\n"
          f"  vector_index_name: {vector_index_name}\n" 
          f"  num_chunks: {num_chunks}\n"
          f"  routes_dict: {routes_dict}\n"
          f"  date_range: {date_range}")
    
    routing_json_obj = qrag_routing_call(
        user_question=user_question, 
        vector_index_name=vector_index_name, 
        num_chunks=num_chunks, 
        routes_dict=routes_dict,
        date_range=date_range
    )

    if verbose:
        print("******** Routing JSON object: ********")
        pretty_print_json_data(routing_json_obj, print_values=True)
    
    print(f"  Finished qrag_routing_call.\nRunning qrag_llm_call with model {llm_model}...")
    
    # Load large context if filename provided
    large_context = None
    if large_context_filename:
        large_context_path = os.path.join(large_context_folder, large_context_filename)
        try:
            with open(large_context_path, 'r') as file:
                large_context = file.read()
                print(f"Successfully loaded large context from {large_context_filename}")
        except Exception as e:
            print(f"Warning: Failed to load large context file: {str(e)}")
            large_context = None
            large_context_filename = None
    
    # Generate the AI answer with LLM model and large context
    qrag_json_object = qrag_llm_call(
        routing_json_obj,
        llm_model=llm_model,
        large_context=large_context,
        large_context_filename=large_context_filename
    )
    
    print("  Finished qrag_llm_call.\nPrinting display text...")
    
    # Then print the display text with the complete information
    pretty_print_json_data(qrag_json_object, print_values=True)
    
    # Save the response to a file
    datetime = get_current_datetime_filefriendly()
    query = user_question
    query_trim = query[:30] + (query[30:].split(None, 1)[0].rstrip('.,!?;:') if len(query) > 30 and not query[30].isspace() else '')
    json_filename = f"chat_response_{datetime}_{llm_model}_{query_trim}.json"
    json_file_path = "exchanges/response_files/" + json_filename
    write_json_file_from_json_data(qrag_json_object, json_file_path, overwrite="yes")
    
    if verbose:
        print("******** QRAG JSON object: ********")
        pretty_print_json_data(qrag_json_object, print_values=True)
    
    return qrag_json_object

def print_qrag_display_text(qrag_json_object):
    """ 
    Prints a formatted display text for QRAG (Question Retrieval Augmented Generation) results
    and copies it to the clipboard.

    :param qrag_json_object: dictionary containing QRAG results with 'content' key.
    :return: None.
    """
    user_question = qrag_json_object['content']['user_question']
    route_preamble = qrag_json_object['content']['route_preamble']
    quoted_qa = qrag_json_object['content']['quoted_qa']
    ai_answer = qrag_json_object['content']['ai_answer']
    
    # Get optional fields with default values if they don't exist
    reasoning_steps = qrag_json_object['content'].get('reasoning_steps', '')
    large_context_filename = qrag_json_object['content'].get('large_context_filename', '')
    
    user_question_first_line = user_question.split('\n')[0]
    user_question_rest = '\n'.join(user_question.split('\n')[1:])
    
    # Build display text with optional sections
    display_text = [
        f"# {user_question_first_line}",
        user_question_rest,
        "",
        "## ROUTE PREAMBLE:",
        route_preamble,
        "",
        "## QUOTED QA:",
        quoted_qa,
        "",
        "## AI ANSWER:",
        ai_answer
    ]
    
    # Add reasoning steps if they exist
    if reasoning_steps:
        display_text.extend(["", "## REASONING STEPS:", reasoning_steps])
    
    # Add large context filename if it exists
    if large_context_filename:
        display_text.extend(["", f"## LARGE CONTEXT FILE:", large_context_filename])
    
    # Join all sections with newlines
    display_text = '\n'.join(display_text)
    print(display_text)
    
    # Copy to clipboard
    pyperclip.copy(display_text)
    return display_text

def create_md_from_qrag_exchange_json(exchange_json_filepath):
    """
    Creates a markdown file from a qrag exchange JSON object and saves it in the same folder as the JSON.

    :param exchange_json_filepath: string, path to the JSON exchange file.
    :return: string, path to the created markdown file.
    """
    qrag_json_object = get_json_data_from_json_file(exchange_json_filepath)
    display_text = print_qrag_display_text(qrag_json_object)
    
    # Get question
    question = qrag_json_object['content']['user_question']
    
    # Truncate question to 30 chars on word boundary
    words = question.split()
    truncated_question = ""
    for word in words:
        if len(truncated_question + word) > 30:
            break
        truncated_question += word + " "
    truncated_question = truncated_question.strip()
    
    # Get base filename without extension
    base_filename = os.path.splitext(os.path.basename(exchange_json_filepath))[0]
    
    # Create markdown filepath in same folder as JSON
    folder = os.path.dirname(exchange_json_filepath)
    md_filename = f"{base_filename}_{truncated_question}.md"
    exchange_md_filepath = os.path.join(folder, md_filename)
    
    # Write markdown file
    with open(exchange_md_filepath, 'w') as f:
        f.write(display_text)
        
    return exchange_md_filepath

# ===== END OF FILE core/rag.py =====