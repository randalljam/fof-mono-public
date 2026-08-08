import os
import json
from bs4 import BeautifulSoup
from pinecone import Pinecone as PineconePinecone
from datetime import datetime
from chalicelib.llm import simple_openai_completion_request
from chalicelib.vectordb import generate_embedding
from chalicelib.rag_prompts_routes import *
from chalicelib.config import PINECONE_API_KEY, OPENAI_API_KEY


os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  # reconsider where we are getting the openai api keys

# TODO: Double check that 'gpt-4-turbo' works
#DEFAULT_LLM_MODEL = 'gpt-4-turbo'
DEFAULT_LLM_MODEL = 'gpt-4o'
pc = PineconePinecone(api_key=PINECONE_API_KEY)  # 'pc' is the standard convention so we'll keep it despite it being unclear


def pinecone_retriever(question, index_name):
    vectorized_question = generate_embedding(question)  # import from create_vectordbs_pinecone
    index = pc.Index(index_name)
    retrieved_qchunks = index.query(
        namespace="",
        vector=vectorized_question,
        top_k=5,  # determines number of vectors retuned by pinecone
        include_values=False)
    
    # Extract the IDs from the retrieved question chunks
    retrieved_ids_scores = {vector['id']: vector['score'] for vector in retrieved_qchunks['matches']}
    # print(f"DEBUG retrieved_ids: {retrieved_ids})
    # Fetch the question chunks using the IDs
    ids = list(retrieved_ids_scores.keys())
    fetched_qchunks = index.fetch(ids=ids, namespace="")

    # DEBUG save to file
    # with open('fetched_chunks.txt', 'w') as f:
    #     f.write(str(fetched_qchunks))

    return fetched_qchunks, retrieved_ids_scores

def qrag_chunk_sorter(fetched_qchunks, retrieved_ids_scores):
    # Find the id of the chunk with the highest similarity score
    highest_sim_id = max(retrieved_ids_scores, key=retrieved_ids_scores.get)
    
    # Find the id of the chunk with the highest 'STARS' rating
    highest_stars_id = max(fetched_qchunks['vectors'], key=lambda x: fetched_qchunks['vectors'][x]['metadata'].get('STARS', 0))
    
    # Extract chunks
    highest_sim_chunk = fetched_qchunks['vectors'][highest_sim_id]
    highest_stars_chunk = fetched_qchunks['vectors'][highest_stars_id] if highest_sim_id != highest_stars_id else None

    # Return the chunks directly
    return (highest_sim_chunk, highest_stars_chunk)

# in llm.py, simple_openai_completion_request should let any message work with a response. need to stuff prompts with retrieved docs

### BOT FUNCTIONS
def call_qrag_chat(question, prompt_template, index_name, llm_model=DEFAULT_LLM_MODEL):  # DS, cat 1
    """
    Initiates a chat session using question retrieval augmented generation (QRAG) with a specified question, prompt template, and index name.

    :param question: string of the question to initiate the chat with.
    :param prompt_template: string of the template used to format the chat prompt.
    :param index_name: string of the name of the pinecone index to use for retrieval.
    :return: dictionary containing the chat response and metadata.

    :category: 1
    :heading: BOT FUNCTIONS
    :usage: call_qrag_chat("What is the weather today?", "Your prompt template here.", "your_index_name")
    """
    # Actual QRAG chatbot function,  give question and return response and metadata from bot
    index = pc.Index(index_name)
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
    vectorstore = PineconeVectorStore(index, embeddings, text_key="ANSWER")
    # Setting up chat model and retrieval QA chain. Use max marginal relevance search to increase diversity of results.
    llm = ChatOpenAI(model_name = llm_model, temperature=0)
    retriever = vectorstore.as_retriever(search_type="mmr")
    CONDENSE_QUESTION_PROMPT = streamlit_bots.prompts.CONDENSE_QUESTION_PROMPT

    QA_PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
    doc_chain = load_qa_chain(chain_type="stuff", prompt=QA_PROMPT, llm=llm, verbose=True)
    chat_history = ''
    qa_chain = ConversationalRetrievalChain(
        retriever=retriever,
        combine_docs_chain=doc_chain,
        question_generator=question_generator,
        return_source_documents=True,
    )
    result = qa_chain({"question": question, "chat_history": chat_history})
    # result = qa_chain
    return result

def call_vrag_chat(question, prompt_template, index_name, llm_model=DEFAULT_LLM_MODEL):  # DS, cat 1
    """
    Initiates a chat session using vector retrieval augmented generation (VRAG) with a specified question, prompt template, and index name.

    :param question: string of the question to initiate the chat with.
    :param prompt_template: string of the template used to format the chat prompt.
    :param index_name: string of the name of the pinecone index to use for retrieval.
    :return: dictionary containing the chat response and metadata.

    :category: 1
    :heading: llm
    :usage: call_vrag_chat("What is the weather today?", "Your prompt template here.", "your_index_name")
    """
    import streamlit_bots.prompts
    index = pc.Index(index_name)
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
    vectorstore = PineconeVectorStore(index, embeddings, text_key="text")
    # Setting up chat model and retrieval QA chain. Use max marginal relevance search to increase diversity of results.
    llm = ChatOpenAI(model_name=llm_model, temperature=0)
    retriever = vectorstore.as_retriever(search_type="mmr")
    CONDENSE_QUESTION_PROMPT = streamlit_bots.prompts.CONDENSE_QUESTION_PROMPT

    QA_PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
    doc_chain = load_qa_chain(chain_type="stuff", prompt=QA_PROMPT, llm=llm, verbose=True)
    chat_history = ''
    qa_chain = ConversationalRetrievalChain(
        retriever=retriever,
        combine_docs_chain=doc_chain,
        question_generator=question_generator,
        return_source_documents=True,
    )
    result = qa_chain({"question": question, "chat_history": chat_history})

    return result

# WIP - last updated Wed 4-24 4pm by BS
# TODO: update to pass in the cutoff and prompts in as a list of dictionaries
def call_sim_routed_qrag_chat_langchain(question, prompt_dict, index_name, llm_model=DEFAULT_LLM_MODEL):  # DS, cat 1
    """
    Initiates a chat session using question retrieval augmented generation (QRAG) with a specified question and index name, dynamically selecting the prompt template based on similarity scores.

    :param question: string of the question to initiate the chat with.
    :param index_name: string of the name of the pinecone index to use for retrieval.
    :return: dictionary containing the chat response and metadata.

    :category: 1
    :heading: BOT FUNCTIONS
    :usage: call_sim_routed_qrag_chat("What is the weather today?", "your_index_name")
    """
    import streamlit_bots.prompts
    # Actual QRAG chatbot function, give question and return response and metadata from bot
    index = pc.Index(index_name)
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
    vectorstore = PineconeVectorStore(index, embeddings, text_key="ANSWER")
    # Setting up chat model and retrieval QA chain. Use max marginal relevance search to increase diversity of results.
    llm = ChatOpenAI(model_name=llm_model, temperature=0)
    retriever = vectorstore.as_retriever(search_type="mmr")
    CONDENSE_QUESTION_PROMPT = streamlit_bots.prompts.CONDENSE_QUESTION_PROMPT

    # Retrieve documents and similarity scores
    retrieved_docs, scores = retriever.retrieve(question, return_scores=True)
    # Select prompt template based on the highest similarity score

    if scores and max(scores) > 0.8: 
        prompt_template = prompt_dict['prompt_template_route3']
        # streamlit_bots.prompts.prompt_template_route1
    elif scores and max(scores) > 0.5: #
        prompt_template = prompt_dict['prompt_template_route2']
        # streamlit_bots.prompts.prompt_template_route2
    else:
        prompt_template = prompt_dict['prompt_template_route1']
        # streamlit_bots.prompts.prompt_template_route3

    QA_PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
    doc_chain = load_qa_chain(chain_type="stuff", prompt=QA_PROMPT, llm=llm, verbose=True)
    chat_history = ''
    qa_chain = ConversationalRetrievalChain(
        retriever=retriever,
        combine_docs_chain=doc_chain,
        question_generator=question_generator,
        return_source_documents=True,
    )
    chat_result = qa_chain({"question": question, "chat_history": chat_history})
    return chat_result

def format_chunk_info(chunk, simscores, prefix=''):
    def safe_int(value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def safe_float(value, default=0.0):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    source = chunk['metadata'].get('SOURCE', 'Unkown source')
    question = chunk['metadata'].get('QUESTION', 'Unknown question')
    answer = chunk['metadata'].get('ANSWER', 'Unknown answer')
    timestamp = chunk['metadata'].get('TIMESTAMP', 'Unknown timestamp')
    stars_str = chunk['metadata'].get('STARS', '0')  # Default to '0' if STARS is not present
    sim = simscores.get(chunk['id'], '0.0')  # Default to '0.0' if simscore is not present

    stars = safe_int(stars_str)
    sim_score = safe_float(sim)
    
    display = f"QUOTED ANSWER STARS: {stars}\nQUOTED QUESTION SIMILARITY SCORE: {round(sim_score * 100)}%"
    
    return {
        f'{prefix}source': source,
        f'{prefix}timestamp': timestamp,
        f'{prefix}question': question,
        f'{prefix}answer': answer,
        f'{prefix}sim': sim_score,
        f'{prefix}stars': stars,
        f'{prefix}display': display
    }

# TODO consider moving to fileops because this is general to all json and not qrag specific
def write_json_file_from_object(json_object, file_path, overwrite="no"):
    if overwrite not in ["yes", "no"]:
        raise ValueError("The 'overwrite' parameter must be 'yes' or 'no'.")

    if overwrite == "no" and os.path.exists(file_path):
        raise FileExistsError(f"The file {file_path} already exists and will not be overwritten.")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as json_file:
        json.dump(json_object, json_file, indent=4)

def read_json_object_from_file(file_path):  # consider moving to fileops
    with open(file_path, 'r') as json_file:
        json_object = json.load(json_file)
    return json_object

def print_qrag_display_text(json_object):
    user_question = json_object['content']['user_question']
    route_preamble = json_object['content']['route_preamble']
    quoted_qa = json_object['content']['quoted_qa']
    ai_answer = json_object['content']['ai_answer']
    display_text = 'USER QUESTION: ' + user_question + '\n\n' + 'ROUTE PREAMBLE: ' + route_preamble + '\n\n' + quoted_qa + 'AI ANSWER: ' + ai_answer
    print(display_text)

def get_qrag_display_dict(json_object):
    return {
        'user_question': json_object['content']['user_question'],
        'route_preamble': json_object['content']['route_preamble'],
        'quoted_qa': json_object['content']['quoted_qa'],
        'ai_answer': json_object['content']['ai_answer']
    }

def create_html_page_from_json_file(json_file_path, html_file_path):
    # Read JSON object from file
    json_object = read_json_object_from_file(json_file_path)
    
    # Get display dictionary from JSON object
    display_dict = get_qrag_display_dict(json_object)
    
    # Read the HTML file
    with open(html_file_path, 'r') as file:
        html_content = file.read()
    
    # Replace placeholders in HTML with values from display_dict
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Update HTML content based on display_dict
    fields_updated = []
    if 'user_question' in display_dict:
        user_question_element = soup.find(id="displayUserQuestion")
        user_question_element.clear()
        # Create a new BeautifulSoup object from the HTML content
        new_content = BeautifulSoup("\n" + display_dict['user_question'].replace('\n', '<br>\n'), 'html.parser')
        # Append the new content as HTML
        user_question_element.append(new_content)
        fields_updated.append('User Question')
    if 'route_preamble' in display_dict:
        route_preamble_element = soup.find(id="displayRoutePreamble")
        route_preamble_element.clear()
        new_content = BeautifulSoup("\n" + display_dict['route_preamble'].replace('\n', '<br>\n'), 'html.parser')
        route_preamble_element.append(new_content)
        fields_updated.append('Route Preamble')
    if 'quoted_qa' in display_dict:
        quoted_qa_element = soup.find(id="displayQuotedQA")
        quoted_qa_element.clear()
        new_content = BeautifulSoup("\n" + display_dict['quoted_qa'].replace('\n', '<br>\n'), 'html.parser')
        quoted_qa_element.append(new_content)
        fields_updated.append('Quoted QA')
    if 'ai_answer' in display_dict:
        ai_answer_element = soup.find(id="displayAiAnswer")
        ai_answer_element.clear()
        new_content = BeautifulSoup("\n" + display_dict['ai_answer'].replace('\n', '<br>\n'), 'html.parser')
        ai_answer_element.append(new_content)
        fields_updated.append('AI Answer')
    
    # Write the updated HTML back to file
    with open(html_file_path, 'w') as file:
        file.write(str(soup))
    
    # Print success message
    print("Successfully updated HTML file with the following fields:")
    for field in fields_updated:
        print(field)

def qrag_sim_routed(user_question, routes_dict, index_name, routes_bounds=[0.3, 0.9], user_id='default', 
llm_model=DEFAULT_LLM_MODEL, bot_version="1.0"):
    routes_flow_name = "3 routes, sim-star double, separate prompts"
    
    chunks, simscores = pinecone_retriever(user_question, index_name)
    
    top_sim_chunk, top_stars_chunk = qrag_chunk_sorter(chunks, simscores)
    top_sim_info = format_chunk_info(top_sim_chunk, simscores, 'top_sim_')
    max_sim = top_sim_info['top_sim_sim']
    max_stars = top_sim_info['top_sim_stars']  # Will be reassigned below if there is a 2nd chunk that has the top stars

    quoted_qa = routes_dict['quoted_qa_single'].format(**top_sim_info)

    if top_stars_chunk is not None:
        top_stars_info = format_chunk_info(top_stars_chunk, simscores, 'top_stars_')
        max_stars = top_stars_info['top_stars_stars']
        combined_info = {**top_stars_info, **top_sim_info}
        quoted_qa = routes_dict['quoted_qa_double'].format(**combined_info)
            
    lower_sim_bound, upper_sim_bound = routes_bounds

    user_ai_qa = routes_dict['user_ai_qa'].format(user_question=user_question)

    if max_sim >= upper_sim_bound:
        prompt_initial = routes_dict['prompt_initial_good_match']
        route_preamble = routes_dict['route_preamble_good_match']
    elif max_sim <= lower_sim_bound:
        prompt_initial = routes_dict['prompt_initial_no_match']
        route_preamble = routes_dict['route_preamble_no_match']
        quoted_qa = ""
    else:
        prompt_initial = routes_dict['prompt_initial_partial_match']
        route_preamble = routes_dict['route_preamble_partial_match']

    prompt = prompt_initial + quoted_qa + user_ai_qa
    response = simple_openai_completion_request(prompt, llm_model)
    
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "index_name": index_name,  # pinecone vector db id
            "bot_version": bot_version,
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
            "ai_answer": response,
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

def qrag_routing(user_question, routes_dict, index_name, routes_bounds=[0.3, 0.9], user_id='default', 
llm_model=DEFAULT_LLM_MODEL, bot_version="1.0"):
    routes_flow_name = "3 routes, sim-star double, separate prompts"
    
    chunks, simscores = pinecone_retriever(user_question, index_name)
    
    top_sim_chunk, top_stars_chunk = qrag_chunk_sorter(chunks, simscores)
    top_sim_info = format_chunk_info(top_sim_chunk, simscores, 'top_sim_')
    max_sim = top_sim_info['top_sim_sim']
    max_stars = top_sim_info['top_sim_stars']  # Will be reassigned below if there is a 2nd chunk that has the top stars

    quoted_qa = routes_dict['quoted_qa_single'].format(**top_sim_info)

    if top_stars_chunk is not None:
        top_stars_info = format_chunk_info(top_stars_chunk, simscores, 'top_stars_')
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
            "index_name": index_name,  # pinecone vector db id
            "bot_version": bot_version,
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
            "ai_answer": "WAITING FOR LLM RESPONSE",
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

def qrag_llm(routing_response):
    # Extract necessary information from routing_response
    user_question = routing_response['content']['user_question']
    route_preamble = routing_response['content']['route_preamble']
    quoted_qa = routing_response['content']['quoted_qa']
    
    # Prepare the prompt for the LLM call
    llm_prompt = route_preamble + "\n" + quoted_qa + "\nUSER QUESTION: " + user_question + "\n\nAI ANSWER: "
    
    # Make the LLM call using simple_openai_completion_request function
    llm_model = routing_response['metadata']['llm_model']
    llm_answer = simple_openai_completion_request(llm_prompt, model=llm_model)
    
    # Update the routing_response with the AI answer
    routing_response['content']['ai_answer'] = llm_answer
    
    # Return the completed json
    return routing_response

def qrag_2_step():
    
    cur_user_question = 'What is the meaning of life?'  # q1 PARTIAL MATCH
    # cur_user_question = 'What should I eat for lunch?'  # q2 NO MATCH
    # cur_user_question = 'What are computers and computation at a deep level?'  # q3 GOOD MATCH

    # FOR CREATING JSON
    cur_json_obj = qrag_routing(cur_user_question, ROUTES_DICT_DEUTSCH_V3, 'qragnospace')

    # FOR PRINTING TO CONSOLE 
    print_qrag_display_text(cur_json_obj)
    print("\n\n")

    print(qrag_llm(cur_json_obj)['content']['ai_answer'])
    

### CHAT LOGGING
def initialize_chat_session_md(file_path, session_name, verbose=False):  # DS, cat 3
    """
    Creates or updates a markdown file for a chat session with metadata and a predefined content structure.

    :param file_path: string of the path to the markdown file to be created or updated.
    :param session_name: string of the name for the chat session.
    :param verbose: boolean, if true, prints the path of the created or updated file.
    :return: string of the new file path.

    :category: 3
    :heading: chat logging
    :usage: initialize_chat_session_md('/path/to/markdown.md', 'session_name', verbose=True)
    """
    # Create or update the markdown file with the provided content

    from primary.fileops import create_initial_header, set_metadata_field, write_header_and_content_ffop

    content = "### session\n\n" + "\n"
    header = create_initial_header()
    date_today = datetime.now().strftime("%m-%d-%Y") # Assign today's date in format MM-DD-YYY
    header = set_metadata_field(header, 'last updated', date_today + ' Created')  
    header = set_metadata_field(header, 'session_name', session_name)
    # Use fileops function to write the header and content to the file
    new_file_path = write_header_and_content_ffop(file_path, header, content, "_"+session_name)
    if verbose:
        print(f"Markdown session file created/updated at: {new_file_path}")
    return new_file_path
# initialize_chat_session_md('test_session.md', 'thisisatest' , verbose=True)
def append_chat_to_session_md(file_path, response, requested_fields, bot_name, verbose=False):  # DS, cat 3
    """
    Appends a chat response to a markdown session file under the '### session' heading.

    :param file_path: string of the path to the markdown file.
    :param response: dictionary containing the chat response to append.
    :param requested_fields: list of strings specifying which fields from the response to include.
    :param bot_name: string of the bot's name.
    :param verbose: boolean, if true, prints additional information during the process.
    :return: None.

    :category: DO NOT FILL IN BUT LEAVE HERE
    :heading: DO NOT FILL IN BUT LEAVE HERE
    :usage: append_chat_to_session_md('path/to/session.md', response, ['field1', 'field2'], 'bot_name', verbose=True)
    """
    from primary.fileops import write_header_and_content_ffop, read_header_and_content_from_file

    # Read the current header and content from the session file
    bot_response = parse_langchain_qa_response(response, requested_fields, bot_name)
    header, content = read_header_and_content_from_file(file_path, delimiter="### session")
    # Append the new content under the ### session heading
    new_content = content + "\n" + bot_response
    # Write the updated content back to the file
    write_header_and_content_ffop(file_path, header, new_content, suffix_new="")

# TODO reformat topics without the list brakets and quotes
def parse_langchain_qa_response(response, requested_fields, bot_name):
    """
    Converts a language model chain query response into a markdown string.

    :param response: dictionary containing the language model's response.
    :param requested_fields: list of strings of fields to include in the markdown output.
    :param bot_name: string of the bot's name for inclusion in the output.
    :return: string of the markdown-formatted response.

    :category: DO NOT FILL IN BUT LEAVE HERE
    :heading: DO NOT FILL IN BUT LEAVE HERE
    :usage: 
    """
    bot_answer = response['answer']
    user_question = response['question']
    doc_dict = {}
    try:
        for source in response['source_documents']:
            source_fields = {'source_answer': source.page_content,
                             'source_question': source.metadata['QUESTION'],
                             'source_stars': source.metadata['STARS'],
                             'source_topics': source.metadata['TOPICS']}
            doc_dict[source.metadata['SOURCE']] = source_fields
    except KeyError:
        for source in response['source_documents']:
            source_fields = {'text': source.page_content}
            doc_dict[source.metadata['source']] = source_fields

    parsed_chat_response = ''
    if 'user_question' in requested_fields:
        parsed_chat_response += f'#### user question: {user_question}\n##### {bot_name}\n'
        parsed_chat_response += f'bot answer: {bot_answer}\n'
    parsed_chat_response += "###### sources\n"

    for doc in doc_dict:
        parsed_chat_response += f"source: {doc}\n"
        for field in requested_fields:
            if field in doc_dict[doc]:
                parsed_chat_response += f"{field}: {doc_dict[doc][field]}\n"
    parsed_chat_response += '\n\n'
    return parsed_chat_response

# bot_name by default is the portion of the global variable following BOT_DICT in lower case. Is used in the bot output md file.
# BOT_DICT_DEUTSCH_VRAG_V1 = {'bot_name':'deutsch_vrag_v1','rag_func':call_vrag_chat, 'prompt_template':streamlit_bots.prompts.prompt_template_deutsch2_long, 'pinecone_index_name':'dserverless'}
# BOT_DICT_DEUTSCH_QRAG_V1 = {'bot_name':'deutsch_qrag_v1','rag_func':call_qrag_chat, 'prompt_template':streamlit_bots.prompts.prompt_template_deutsch_small, 'pinecone_index_name':'qragtest'}

# BOT_DICT_ROUTING_DEUTSCH_QRAG_V1 = {'bot_name':'deutsch_routing_qrag_v1','rag_func':call_sim_routed_qrag_chat, 'prompt_template':streamlit_bots.prompts.routing_prompt_dict, 'pinecone_index_name':'qragtest'}


ALL_FIELDS = ['bot_answer','user_question','source_question','source_answer','source_stars','source_topics','text']
BASIC_Q_LIST = ['What is the meaning of life?', 'what is a good explanation?', 'what is the square root of 16?']
DEUTSCH_Q_LIST_T1 = ['Do we live in a simulation?', 'What is more fundamental mathematics or physics?', 'How would you make the case to someone who believes humans are just clever animals that people are indeed special in a deep sense?']
DEUTSCH_Q_LIST_T2 = ['What is the meaning of life?']

# BOT_DICT_TOWNHALL_VRAG_V1 = {'bot_name':'townhall_vrag_v1','rag_func':call_vrag_chat, 'prompt_template':streamlit_bots.prompts.prompt_template_fda_basic, 'pinecone_index_name':'fda-townhalls-vrag-test1'}
# FDA_TOWNHALL_TEST_QUESTIONS = ['What is the difference between a over-the-counter test and a point-of-care test?', 'What is the sensitivity requirement for a molecular COVID-19 test?', 'What is required for the asymptomatic intended use indication?']


def run_batch_questions_on_bot_list(file_path, question_list, bot_list, selected_fields=ALL_FIELDS):
    """
    Executes a batch of questions on a list of bots, appending each bot's response to a markdown file.

    :param file_path: string of the path to the markdown file where chat sessions will be recorded.
    :param question_list: list of questions to be asked to each bot.
    :param bot_list: list of dictionaries, each representing a bot with keys for 'rag_func', 'prompt_template', and 'pinecone_index_name'.
    :param selected_fields: list of fields to be included in the markdown file. Defaults to ALL_FIELDS.
    :return: None

    :category: DO NOT FILL IN BUT LEAVE HERE
    :heading: DO NOT FILL IN BUT LEAVE HERE
    :usage: run_batch_questions_on_bot_list('path/to/file.md', ['Question 1', 'Question 2'], [BOT_DICT_1, BOT_DICT_2])
    """
    session_path = initialize_chat_session_md(file_path, 'testing1')  # TODO pass in suffix 
    for question in question_list:
        for bot in bot_list:
            rag_func = bot['rag_func']
            # If the prompt_template is a dictionary, pass it directly to the rag_func
            prompt_template = bot['prompt_template']
            pinecone_index_name = bot['pinecone_index_name']
            response = rag_func(question, prompt_template, pinecone_index_name)
            append_chat_to_session_md(session_path, response, selected_fields, bot['bot_name'])
        
        # After appending responses for all bots for a question, clean up the headings
        with open(session_path, 'r') as file:
            lines = file.readlines()
        
        # Identify and keep only the first occurrence of a heading for the current question
        heading = f"#### user question: {user_question}\n"
        heading_found = False
        with open(session_path, 'w') as file:
            for line in lines:
                if line == heading:
                    if not heading_found:
                        heading_found = True
                        file.write(line)
                    else:
                        continue  # Skip writing the line if it's a duplicate heading
                else:
                    file.write(line)
