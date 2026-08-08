import os
from datetime import datetime
from pinecone import Pinecone
from chalicelib.vectordb import generate_embedding
from chalicelib.llm import simple_openai_chat_completion_request
from chalicelib.rag_prompts_routes import *
from chalicelib.config import PINECONE_API_KEY, OPENAI_API_KEY_CONFIG_LLM, ANTHROPIC_API_KEY_CONFIG_LLM


# TODO consider where and how we are getting the openai api keys
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY_CONFIG_LLM
os.environ['ANTHROPIC_API_KEY'] = ANTHROPIC_API_KEY_CONFIG_LLM

DEFAULT_LLM_MODEL = 'gpt-4o'
pc = Pinecone(api_key=PINECONE_API_KEY)  # 'pc' is the standard convention so we'll keep it despite it being unclear


### RETRIEVAL
def pinecone_retriever(query, vector_index_name, num_chunks=5):
    """ 
    Retrieves relevant question chunks from a Pinecone index based on the input question.

    :param question: string of the input question to search for.
    :param vector_index_name: string of the name of the Pinecone index to query.
    :return: tuple containing fetched question chunks and a dictionary of retrieved IDs with their scores.
    """
    vectorized_query = generate_embedding(query)
    index = pc.Index(vector_index_name)
    retrieved_qchunks = index.query(
        namespace="",
        vector=vectorized_query,
        top_k=num_chunks,  # determines number of vectors retuned by pinecone
        include_values=False)
    
    # Extract the IDs from the retrieved question chunks
    retrieved_ids_scores = {vector['id']: vector['score'] for vector in retrieved_qchunks['matches']}
    # print(f"DEBUG retrieved_ids: {retrieved_ids})
    # Fetch the question chunks using the IDs
    ids = list(retrieved_ids_scores.keys())
    fetched_chunks = index.fetch(ids=ids, namespace="")

    # DEBUG save to file
    # with open('fetched_chunks.txt', 'w') as f:
    #     f.write(str(fetched_qchunks))

    return fetched_chunks, retrieved_ids_scores


### VRAG
def print_vrag_display_text(json_object, show_prompt=False):
    """
    Prints a formatted display text for VRAG (Vector Retrieval Augmented Generation) results.

    :param json_object: dictionary containing VRAG results with 'content' key.
    :param show_prompt: boolean to determine whether to show the full LLM prompt.
    :return: None.
    """
    user_question = json_object['content']['user_question']
    ai_answer = json_object['content']['ai_answer']
    
    display_text = f"USER QUESTION: {user_question}\n\n"
    
    if show_prompt:
        llm_prompt = json_object['content']['llm_prompt']
        display_text += f"LLM PROMPT:\n{llm_prompt}\n\n"
    else:
        chunk_texts = json_object['content']['chunk_texts']
        display_text += f"RETRIEVED CHUNKS:\n{chunk_texts}\n\n"
    
    display_text += f"AI ANSWER: {ai_answer}"
    
    print(display_text)
    
def vrag_llm_call(user_question, vector_index_name, vrag_preamble=VRAG_PREAMBLE_V1, llm_model=DEFAULT_LLM_MODEL, user_id='default', vrag_version="1.0"):
    """
    Initiates a chat session using vector retrieval augmented generation (VRAG) with a specified question,
    prompt template, and index name. Returns a JSON object with the results.

    :param user_question: string of the question to initiate the chat with.
    :param vector_index_name: string of the name of the pinecone index to use for retrieval.
    :param vrag_preamble: string of the preamble used to format the chat prompt.
    :param llm_model: string of the language model to use.
    :param user_id: string of the user identifier.
    :param bot_version: string of the bot version.
    :return: dictionary containing the chat response and metadata.
    """
    fetched_chunks, retrieved_ids_scores = pinecone_retriever(user_question, vector_index_name)
    chunk_texts = ''
    for chunk_id, chunk_data in fetched_chunks['vectors'].items():
        text = chunk_data['metadata'].get('text', '')
        if text:
            chunk_texts += text + '\n'
    chunk_texts = chunk_texts.rstrip('\n')  # Remove trailing newline if present

    llm_prompt = vrag_preamble + "\n" + chunk_texts + "\nUSER QUESTION: " + user_question + "\n\nAI ANSWER: "
    llm_answer = simple_openai_chat_completion_request(llm_prompt, model=llm_model)
    
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
            "ai_answer": llm_answer
        }
    }
 
### QRAG
def select_chunks_qrag_1or2(fetched_qa_chunks, retrieved_ids_scores):
    """ 
    Sorts and returns the most relevant chunks based on similarity score and 'STARS' rating.
    Filters down to 1 or 2 chunks from the 5 fetched.

    :param fetched_qchunks: dictionary of fetched question chunks from Pinecone.
    :param retrieved_ids_scores: dictionary of retrieved IDs with their similarity scores.
    :return: tuple containing the highest similarity chunk and the highest 'STARS' rated chunk (if different).
    """
    # Find the id of the chunk with the highest similarity score
    highest_sim_id = max(retrieved_ids_scores, key=retrieved_ids_scores.get)
    
    # Find the id of the chunk with the highest 'STARS' rating
    highest_stars_id = max(fetched_qa_chunks['vectors'], key=lambda x: fetched_qa_chunks['vectors'][x]['metadata'].get('STARS', 0))
    
    # Extract chunks
    highest_sim_chunk = fetched_qa_chunks['vectors'][highest_sim_id]
    highest_stars_chunk = fetched_qa_chunks['vectors'][highest_stars_id] if highest_sim_id != highest_stars_id else None

    # Return the chunks directly
    return (highest_sim_chunk, highest_stars_chunk)

def parse_chunk_all(chunk, simscores=None):
    """ 
    Formats information from a chunk and its optional similarity scores into a structured dictionary,
    including all fields present in the chunk's metadata. Handles various data types including lists.

    :param chunk: dictionary containing metadata and content of a document chunk.
    :param simscores: optional dictionary of similarity scores keyed by chunk id.
    :return: dictionary containing formatted chunk information.
    """
    def safe_convert(value):
        """Converts value to appropriate type, handling various data types including lists."""
        if isinstance(value, (int, float, str, bool)):
            return value
        elif isinstance(value, list):
            return [safe_convert(item) for item in value]
        else:
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return str(value)

    result = {}

    # Process all metadata fields
    for key, value in chunk['metadata'].items():
        result[key.lower()] = safe_convert(value)

    # Add similarity score if available
    if simscores is not None and chunk['id'] in simscores:
        result['sim'] = safe_convert(simscores[chunk['id']])

    return result

def parse_chunk_qa_dd(chunk, simscores, prefix=''):
    """ 
    Wrapper function that formats information from a chunk and its similarity scores into a structured dictionary,
    maintaining the same functionality as the original parse_chunk_qa_dd function while using parse_chunk_all internally.
    Handles complex data types like lists and empty strings.

    :param chunk: dictionary containing metadata and content of a document chunk.
    :param simscores: dictionary of similarity scores keyed by chunk id.
    :param prefix: string of prefix to add to dictionary keys. default is empty string.
    :return: dictionary containing formatted chunk information with prefixed keys.
    """
    # Call the general parsing function
    general_result = parse_chunk_all(chunk, simscores)

    def safe_int(value, default=0):
        try:
            return int(value) if value != '' else default
        except (ValueError, TypeError):
            return default

    def safe_float(value, default=0.0):
        try:
            return float(value) if value != '' else default
        except (ValueError, TypeError):
            return default

    # Modify the result to match the original function's output
    result = {
        f'{prefix}source': str(general_result.get('source', 'Unknown source')),
        f'{prefix}timestamp': str(general_result.get('timestamp', 'Unknown timestamp')),
        f'{prefix}question': str(general_result.get('question', 'Unknown question')),
        f'{prefix}answer': str(general_result.get('answer', 'Unknown answer')),
        f'{prefix}sim': safe_float(general_result.get('sim', 0.0)),
        f'{prefix}stars': safe_int(general_result.get('stars', 0))
    }

    # Create the display string
    stars = result[f'{prefix}stars']
    sim_score = result[f'{prefix}sim']
    result[f'{prefix}display'] = f"QUOTED ANSWER STARS: {stars}\nQUOTED QUESTION SIMILARITY SCORE: {round(sim_score * 100)}%"

    return result

def qrag_routing_call(user_question, routes_dict, vector_index_name, routes_bounds=[0.3, 0.9], 
llm_model=DEFAULT_LLM_MODEL, user_id='default', qrag_version="1.0"):
    """ 
    Routes a user question through a question retrieval augmented generation (QRAG) process.

    :param user_question: string of the user's input question.
    :param routes_dict: dictionary containing routing prompts and templates.
    :param vector_index_name: string of the name of the pinecone index to use for retrieval.
    :param routes_bounds: list of two floats representing the lower and upper similarity bounds for routing.
    :param user_id: string of the user identifier. defaults to 'default'.
    :param llm_model: string of the language model to use. defaults to DEFAULT_LLM_MODEL.
    :param bot_version: string of the bot version. defaults to "1.0".
    :return: dictionary containing metadata and content of the QRAG process and response.

    Usage:
    response = qrag_routing_call("What is the capital of France?", routes_dict, "my_index")
    """
    routes_flow_name = "3 routes, sim-star double, separate prompts"
    
    chunks, simscores = pinecone_retriever(user_question, vector_index_name)
    
    top_sim_chunk, top_stars_chunk = select_chunks_qrag_1or2(chunks, simscores)
    top_sim_info = parse_chunk_qa_dd(top_sim_chunk, simscores, 'top_sim_')
    max_sim = top_sim_info['top_sim_sim']
    max_stars = top_sim_info['top_sim_stars']  # Will be reassigned below if there is a 2nd chunk that has the top stars 

    quoted_qa = routes_dict['quoted_qa_single'].format(**top_sim_info)

    if top_stars_chunk is not None:
        top_stars_info = parse_chunk_qa_dd(top_stars_chunk, simscores, 'top_stars_')
        max_stars = top_stars_info['top_stars_stars']
        combined_info = {**top_stars_info, **top_sim_info}
        quoted_qa = routes_dict['quoted_qa_double'].format(**combined_info)
            
    lower_sim_bound, upper_sim_bound = routes_bounds

    if max_sim >= upper_sim_bound:
        route_preamble = routes_dict['route_preamble_good_match']
    elif max_sim <= lower_sim_bound:
        route_preamble = routes_dict['route_preamble_no_match']
        quoted_qa = ""
    else:
        route_preamble = routes_dict['route_preamble_partial_match']
    
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "vector_index_name": vector_index_name,  # pinecone vector db id
            "qrag_version": qrag_version,
            "llm_model": llm_model,
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
            "quoted_qa": quoted_qa,  # includes 'QUOTED X: ' and newlines at end
            "ai_answer": "WAITING FOR AI ANSWER...",
            "chunks": {
                "max_sim": "{:.3f}".format(max_sim),
                "max_stars": max_stars,
                "chunks": [
                    {
                        "question": top_sim_info['top_sim_question'],
                        "source": top_sim_info['top_sim_source'], 
                        "timestamp": top_sim_info['top_sim_timestamp'],
                        "answer": top_sim_info['top_sim_answer'],
                        "stars": top_sim_info['top_sim_stars'],
                        "sim": "{:.3f}".format(top_sim_info['top_sim_sim'])
                    }
                ] + ([
                    {
                        "question": top_stars_info['top_stars_question'],
                        "source": top_stars_info['top_stars_source'],
                        "timestamp": top_stars_info['top_stars_timestamp'],
                        "answer": top_stars_info['top_stars_answer'],
                        "stars": top_stars_info['top_stars_stars'],
                        "sim": "{:.3f}".format(top_stars_info['top_stars_sim'])
                    }
                ] if top_stars_chunk is not None else [])
            }
        }
    }

def qrag_llm_call(json_object):
    """ 
    Generates an AI answer for a given JSON object containing question and context information.

    :param json_object: dictionary containing the question, context, and metadata for generating an AI answer.
    :return: dictionary with the updated JSON object including the AI-generated answer.
    """
    # Verify necessary fields exist in the JSON object
    required_fields = ['user_question', 'route_preamble', 'quoted_qa', 'ai_answer']
    missing_fields = [field for field in required_fields if field not in json_object['content']]
    if missing_fields:
        raise ValueError(f"Missing required fields in JSON object: {', '.join(missing_fields)}")

    # Extract necessary information from json_object
    user_question = json_object['content']['user_question']
    route_preamble = json_object['content']['route_preamble']
    quoted_qa = json_object['content']['quoted_qa']
    
    # Prepare the prompt for the LLM call
    llm_prompt = route_preamble + "\n" + quoted_qa + "\nUSER QUESTION: " + user_question + "\n\nAI ANSWER: "
    
    # Make the LLM call using simple_openai_chat_completion_request function
    llm_model = json_object['metadata']['llm_model']
    llm_answer = simple_openai_chat_completion_request(llm_prompt, model=llm_model)
    
    # Add the AI answer to the json_object
    json_object['content']['ai_answer'] = llm_answer
    
    return json_object

def print_qrag_display_text(json_object):
    """ 
    Prints a formatted display text for QRAG (Question Retrieval Augmented Generation) results.

    :param json_object: dictionary containing QRAG results with 'content' key.
    :return: None.
    """
    user_question = json_object['content']['user_question']
    route_preamble = json_object['content']['route_preamble']
    quoted_qa = json_object['content']['quoted_qa']
    ai_answer = json_object['content']['ai_answer']
    display_text = 'USER QUESTION: ' + user_question + '\n\n' + 'ROUTE PREAMBLE: ' + route_preamble + '\n\n' + quoted_qa + 'AI ANSWER: ' + ai_answer
    print(display_text)

def qrag_2step(user_question, routes_dict, vector_index_name):
    """ 
    Performs a two-step question-answering process using QRAG (Question Retrieval Augmented Generation).

    :param user_question: string of the user's input question.
    :return: None
    """
    # Create JSON object with routing information
    routing_json_obj = qrag_routing_call(user_question, routes_dict, vector_index_name)

    # Print the display text for the QRAG process
    print_qrag_display_text(routing_json_obj)

    # Generate and print the AI answer
    ai_answer = qrag_llm_call(routing_json_obj)['content']['ai_answer']
    print(ai_answer)
