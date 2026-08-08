# ===== START OF FILE core/rag_mtests.py =====
# Library for manual testing of rag functions

from core.fileops import *
from core.llm import *
from core.rag import *
from rag_prompts_routes import *
import os

if True:
    pass
# if __name__ == "__main__":    
    cur_file_path = ""

# CUR_VECTOR_INDEX_NAME = 'deutsch-transcript-qrag-83f-20250202'
# CUR_ROUTES_DICT = ROUTES_DICT_DEUTSCH_M1
# CUR_QUERY = "Why is Thomas Kuhn's philosophy of science taught in universities instead of Karl Popper's?"
# CUR_NUM_CHUNKS = 20
# CUR_LARGE_CONTEXT_FILENAME = 'deutsch_large_context_v1.md'
# CUR_JSON_PATH = 'tests/test_data_files/rag/qrag_routing.json'

# CUR_VECTOR_INDEX_NAME = 'fda-townhalls-qrag-4f-20250114'
# CUR_ROUTES_DICT = ROUTES_DICT_FDA_TOWNHALLS_M1
# CUR_QUERY = "What is the FDA's response to the COVID-19 pandemic?"

# CUR_VECTOR_INDEX_NAME = 'pv-evac-qrag-3f-20250202'
# CUR_ROUTES_DICT = ROUTES_DICT_PV_EVAC_M1
# CUR_QUERY = "What is the PSVD school evacuation plan?"
# CUR_NUM_CHUNKS = 10

# CUR_VECTOR_INDEX_NAME = 'sovereign-child-qrag-2f-20250208'
# CUR_ROUTES_DICT = ROUTES_DICT_SOVEREIGN_CHILD_M1
# CUR_QUERY = "How should I raise my child?"
# CUR_NUM_CHUNKS = 10
# CUR_LARGE_CONTEXT_FILENAME = '2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_trimmed.md'

ROOT_FOLDER = "/Users/randytrue/Documents/Code/corpus-tools/"

### RETRIEVAL
CUR_VECTOR_INDEX_NAME = 'deutsch-transcript-qrag-83f-20250311'  #'deutsch-transcript-qrag-83f-20250202'
CUR_ROUTES_DICT = ROUTES_DICT_DEUTSCH_M1
CUR_QUERY = "What is the meaning of the good life?"
CUR_NUM_CHUNKS = 10
CUR_LARGE_CONTEXT_FILENAME = 'deutsch_large_context_v1.md'
def mtest_pinecone_retriever():
    pass
if __name__ == "__main__":
    print(f"Local Python version: {sys.version}")
    print(f"Local Pinecone version: {pinecone.__version__}")
    print(f"Local Pinecone package location: {pinecone.__file__}")
    retrieved_chunks, retrieved_ids_scores = pinecone_retriever(CUR_QUERY, CUR_VECTOR_INDEX_NAME, num_chunks=CUR_NUM_CHUNKS)
    print(colored(f"Retrieving chunks WITHOUT DATE RANGE and BEFORE FILTERING - num chunks: {len(retrieved_ids_scores)}", "yellow"))
    for id, score in retrieved_ids_scores.items():
        print(f"{id}: {score:.3f}")
    
    filtered_chunks, filtered_ids_scores = filter_same_block_chunks(retrieved_chunks, retrieved_ids_scores)
    print(colored(f"\nRetrieving chunks WITHOUT DATE RANGE and AFTER FILTERING WITHOUT num_chunks_keep - num chunks: {len(filtered_ids_scores)}", "green"))
    for id, score in filtered_ids_scores.items():
        print(f"{id}: {score:.3f}")
        
    filtered_chunks, filtered_ids_scores = filter_same_block_chunks(retrieved_chunks, retrieved_ids_scores, 3)
    print(colored(f"\nRetrieving chunks WITHOUT DATE RANGE and AFTER FILTERING WITH num_chunks_keep=3 - num chunks: {len(filtered_ids_scores)}", "green"))
    for id, score in filtered_ids_scores.items():
        print(f"{id}: {score:.3f}")

    # *****FROM BEFORE FILTERING SAME BLOCK CHUNKS FOR MULTI_Q BLOCKS*****
    # print(colored("\nRetrieving chunks WITH DATE RANGE", "yellow"))
    # date_range = ["2024-09-20", "2024-10-23"]
    # #date_range = ["2023-11-15", "2024-10-23"]
    # fetched_chunks, retrieved_ids_scores = pinecone_retriever(CUR_QUERY, CUR_VECTOR_INDEX_NAME, num_chunks=CUR_NUM_CHUNKS, date_range=date_range)
    # print(f"Retrieved IDs and scores with date range of {date_range}:")
    # for id, score in retrieved_ids_scores.items():
    #     print(f"{id}: {score:.3f}")
    

### VRAG
def mtest_vrag_llm_call():
    pass
#if __name__ == "__main__":
    cur_user_question1 = "What is the meaning of life?"
    cur_user_question2 = "What is the Mathematician's Misconception?"
    cur_json_object = vrag_llm_call(cur_user_question1, 'dd-transcripts-vrag-80f-20240727', 5)
    print_vrag_display_text(cur_json_object, show_prompt=False)

### QRAG
def mtest_sort_chunks_by_stars():
    pass
#if __name__ == "__main__":
    cur_query = "What is the meaning of life?"
    cur_num_chunks = 10  # Number of chunks to retrieve and sort
    fetched_qa_chunks, retrieved_ids_scores = pinecone_retriever(cur_query, CUR_VECTOR_INDEX_NAME, num_chunks=cur_num_chunks)
    sorted_chunks = sort_chunks_by_stars(fetched_qa_chunks, retrieved_ids_scores, num_chunks=cur_num_chunks)
    print("Sorted Chunks by Stars:")
    for idx, chunk in enumerate(sorted_chunks):
        print(f"Chunk {idx+1}:")
        print(f"ID: {chunk['id']}")
        print(f"Stars: {chunk['STARS']}")
        print(f"Similarity Score: {chunk['sim_score']}")
        print(f"Question: {chunk.get('QUESTION', '')}")
        print(f"Answer: {chunk.get('ANSWER', '')}")
        print("-" * 40)
def mtest_sort_chunks_by_sim():
    pass
#if __name__ == "__main__":
    cur_query = "What is the meaning of life?"
    cur_num_chunks = 10  # Number of chunks to retrieve and sort
    fetched_qa_chunks, retrieved_ids_scores = pinecone_retriever(cur_query, CUR_VECTOR_INDEX_NAME, num_chunks=cur_num_chunks)
    sorted_chunks = sort_chunks_by_sim(fetched_qa_chunks, retrieved_ids_scores, num_chunks=cur_num_chunks)
    print("Sorted Chunks by Similarity:")
    for idx, chunk in enumerate(sorted_chunks):
        print(f"Chunk {idx+1}:")
        print(f"ID: {chunk['id']}")
        print(f"Stars: {chunk['STARS']}")
        print(f"Similarity Score: {chunk['sim_score']}")
        print(f"Question: {chunk.get('QUESTION', '')}")
        print(f"Answer: {chunk.get('ANSWER', '')}")
        print("-" * 40)
def mtest_parse_chunks():
    pass
#if __name__ == "__main__":
    cur_query = "What is the meaning of life?"
    cur_num_chunks = 5
    fetched_chunks, retrieved_ids_scores = pinecone_retriever(cur_query, CUR_VECTOR_INDEX_NAME, num_chunks=cur_num_chunks)
    selected_chunks = sort_chunks_by_sim(fetched_chunks, retrieved_ids_scores, num_chunks=cur_num_chunks)
    parsed_chunks = parse_chunks(selected_chunks, retrieved_ids_scores)
    print("Parsed Chunks:")
    for idx, chunk in enumerate(parsed_chunks):
        print(f"Chunk {idx+1}:")
        print(f"Source: {chunk['source']}")
        print(f"Timestamp: {chunk['timestamp']}")
        print(f"Question: {chunk['question']}")
        print(f"Answer: {chunk['answer']}")
        print(f"Stars: {chunk['stars']}")
        print(f"Similarity Score: {chunk['sim']}")
        print(f"Display: {chunk['display']}")
        print("-" * 40)
def mtest_qrag_routing_call():
    pass
#if __name__ == "__main__":
    qrag_routing_output_json_object = qrag_routing_call(
        user_question=CUR_QUERY,
        vector_index_name=CUR_VECTOR_INDEX_NAME,
        num_chunks=CUR_NUM_CHUNKS,
        routes_dict=CUR_ROUTES_DICT
    )
    pretty_print_json_data(qrag_routing_output_json_object, print_values=True)
    # Save the routing output to a temporary JSON file
    import json
    temp_file = ROOT_FOLDER + "temp.json"
    with open(temp_file, "w") as f:
        json.dump(qrag_routing_output_json_object, f, indent=4)
    print(f"\nSaved routing output to: {temp_file}")
def mtest_qrag_llm_call():
    pass
#if __name__ == "__main__":
    from core.aws_valid import TEST_REQUESTS_QRAG_LLM
    test_json_obj = TEST_REQUESTS_QRAG_LLM["clean_requests"][0]["request"]

    llm_model = 'o3-mini'
    large_context_filename = CUR_LARGE_CONTEXT_FILENAME
    large_context_folder = "data/large_context_files"

    print(f"Using LLM model: {llm_model}")
    print(f"Using large context file: {large_context_filename}")
    print("Testing qrag_llm_call with first clean request from aws_valid.py...")
    print("\nInput JSON:")
    pretty_print_json_data(test_json_obj, print_values=True)

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

    try:
        result_json = qrag_llm_call(
            test_json_obj, 
            llm_model=llm_model,
            large_context=large_context,
            large_context_filename=large_context_filename
        )
        print("\nqrag_llm_call returned the following output JSON:")
        pretty_print_json_data(result_json, print_values=True)
    except Exception as e:
        print(f"\nError in qrag_llm_call: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def mtest_qrag_2step():
    pass
#if __name__ == "__main__":
    # cur_user_question1 = 'What is the meaning of life?'  # q1 PARTIAL MATCH
    # cur_user_question2 = 'What should I eat for lunch?'  # q2 NO MATCH
    # cur_user_question3 = 'What are computers and computation at a deep level?'  # q3 GOOD MATCH
    #llm_model='deepseek-reasoner'
    llm_model='o3-mini'
    qrag_2step(CUR_QUERY, CUR_VECTOR_INDEX_NAME, CUR_NUM_CHUNKS, CUR_ROUTES_DICT, llm_model=llm_model, large_context_filename=CUR_LARGE_CONTEXT_FILENAME)

def mrun_create_md_from_qrag_exchange_json():
    pass
#if __name__ == "__main__":
    cur_exchange_file_path = "exchanges/qrag_sovereign-child/exchange_jsons/qrag-exch_2025-06-24_064934.json"
    print(f"Created markdown file: {create_md_from_qrag_exchange_json(cur_exchange_file_path)}")

# NOT WORKING - See CHAT LOGGING comments
def mtest_run_batch_questions_on_bot_list(): 
    pass
#if __name__ == "__main__":    
    #run_batch_questions_on_bot_list('FDA_townhall_test1.md', FDA_TOWNHALL_TEST_QUESTIONS, [BOT_DICT_TOWNHALL_VRAG_V1])
    # run_batch_questions_on_bot_list('Deutsch_qraq_v1_t2.md', DEUTSCH_Q_LIST_T2, [BOT_DICT_DEUTSCH_QRAG_V1])



# cur_user_question = 'What should I eat for lunch?'  # q2 NO MATCH
# cur_json_path = 'tests/test_data_files/rag/qrag_routing.json'
# cur_user_question = 'What are computers and computation at a deep level?'  # q3 GOOD MATCH
# cur_json_path = 'tests/test_data_files/rag/qrag_routing.json'

# ===== END OF FILE core/rag_mtests.py =====
