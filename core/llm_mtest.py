# ===== START OF FILE core/llm_mtest.py =====
# Manual tests for the llm.py library

from core.fileops import *
from core.llm import *

if True:
    pass
# if __name__ == "__main__":    
    cur_file_path = "tests/test_data_files/llm/dialogue.md"


### PRINT AND TOKEN
def mtest_token_counter():
    pass
#if __name__ == "__main__":
    
    #print(token_counter("This is a test string of arbitrary length. The output should be the number of tokens within this string."))
    # cur_file_path = 'tests/test_data_files/llm/dialogue.md'
    # print(token_counter(get_heading_from_file(cur_file_path, "### transcript")) / 1000000 * 5)
    cur_str = '''
USER QUESTION: What is the meaning of life?

There is a partial match of your question in David Deutsch's interviews. See his QUOTED QUESTIONS AND ANSWERS below followed by an AI ANSWER that synthesizes these quotes with David Deutsch's philosophy and your exact question.

QUOTED QUESTION 1: What does it mean to know everything?
QUOTED ANSWER 1: When I was a child, I remember being told that in the distant past, a very learned person might hope to understand everything that was understood. Whereas now because of specialization, because so much is known, that's impossible. That one person can only understand a very small fraction of what's known. And I really didn't believe this, I didn't want to believe this. And I envied the ancient scholars who might have aspired to knowing everything that was known at the time. And what I meant by, "knowing everything that was known," or "understanding everything that was understood," is not that they knew in detail everything that happened, that they had lists of things which they remembered. That's very far from what I meant. I meant that they understood all the explanations that were known. And I believe that we are not heading away from an era in which one might understand all the explanations as they're known, but towards it, because we are continually unifying and broadening and deepening our explanations of the world.
QUOTED ANSWER STARS: 5
QUOTED QUESTION SIMILARITY SCORE: 42%

QUOTED QUESTION 2: What is meaning of life, the significance of our existence?
QUOTED ANSWER 2: _Regarding the significance of our existence,_ this has to do with both moral and aesthetic values. What we're trying to do, even though many people try to deny this, they deny that they are seeking, trying to do what is right or trying to create what is actually beautiful and so on. But that is what we're trying to do, and that is the meaning. Religions traditionally thought that the meaning was already known or had been revealed to humans and that what our task is, is to live up to that, to enact it. My view is the other way around, that __the meaning of life is something that we are using creativity to discover, to build. There isn't a perfectly accurate word for what we're doing, but we can't find the meaning of life in the world out there, nor just by pure thought or by reference to an authority. What we have to do is form explanations about what is right and wrong, what is better and worse, what's beautiful and ugly, and hone those theories while also trying to meet them. At any one moment, we will meet them imperfectly, just like scientific theories at any one moment are only an imperfect explanation of what the physical world is like. But through criticism and conjecture and seeking the truth, we can eliminate the errors in what we had previously thought and thereby make progress. And that is trying to find the meaning of life, trying to create the meaning of life is the meaning of life.__ *IN-LINE: So we want to model and articulate reality.* Yes, both moral, aesthetic, as well as abstract and physical reality. Yes, exactly.
QUOTED ANSWER STARS: 4
QUOTED QUESTION SIMILARITY SCORE: 76%
'''
    print(count_tokens(cur_str) / 1000000 * 5)
def mtest_cost_llm_on_file():
    pass
#if __name__ == "__main__":
    cur_file_path = 'data/floodlamp/reg/fda-townhalls/dev/2020-12-09_Virtual Town Hall 36_cemanual.md'
    print(cost_llm_on_file(cur_file_path, "this is an arbitrary prompt", 'gpt-4o', TOKEN_COST_DICT, verbose=True,output_tokens_ratio=0)) 
def mrun_cost_llm_input_only():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_sections-nodelims.md"
    IS_CACHED_INPUT = True
    #IS_CACHED_INPUT = False
    cost_llm_input_only(cur_file_path, TOKEN_PRICE_DICT, IS_CACHED_INPUT)
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    cost_llm_input_only(cur_file_path, TOKEN_PRICE_DICT, IS_CACHED_INPUT)
    cur_file_path = "data/deutsch/books/boi.md"
    cost_llm_input_only(cur_file_path, TOKEN_PRICE_DICT, IS_CACHED_INPUT)
    cur_file_path = "data/deutsch/books/for.md"
    cost_llm_input_only(cur_file_path, TOKEN_PRICE_DICT, IS_CACHED_INPUT)
TEST_REASONING_RESPONSE = {
        "usage": {
            "prompt_tokens": 1234,
            "completion_tokens": 789,
            "total_tokens": 2479,  # sum of all tokens
            "completion_tokens_details": {
                "reasoning_tokens": 456,
                "accepted_prediction_tokens": 0,
                "rejected_prediction_tokens": 0
            }
        }
    }
def mtest_get_reasoning_model_cost_table_from_response():
    pass
#if __name__ == "__main__":
    reasoning_model="o3-mini"
    #reasoning_model="o1"
    #reasoning_model="deepseek-reasoner
    cost = get_reasoning_model_cost_table_from_response(TEST_REASONING_RESPONSE, reasoning_model=reasoning_model, verbose=True)
def mtest_compare_reasoning_model_cost_table_from_response():
    pass
#if __name__ == "__main__":
    #reasoning_response_json = TEST_REASONING_RESPONSE
    pickle_file_path = "exchanges/response_files/chat_response_2025-02-11_191321_deepseek-reasoner_What is a thorough response to.pkl"
    reasoning_response = get_object_from_pickle_file(pickle_file_path, verbose=False, print_object=False)
    reasoning_response_json = convert_data_object_to_json_data(reasoning_response, default_handler=None, verbose=False, print_analysis=False, print_values=False)
    compare_reasoning_model_cost_table_from_response(reasoning_response_json)
 
### SPLIT FILES
def mtest_get_line_numbers_with_match():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/llm/dialogue_blocks.md"
    print(get_line_numbers_with_match(cur_file_path, "---"))
def mtest_get_speaker_segments():
    pass
#if __name__ == "__main__":        
    cur_file_path = "data/floodlamp/reg/fda-townhalls/2020-12-09_Virtual Town Hall 36_fixnames.md"
    print(get_speaker_segments(cur_file_path))
def mtest_plot_segment_tokens():  # tests count_segment_tokens also
    pass
#if __name__ == "__main__":        
    cur_file_path = "data/floodlamp/reg/fda-townhalls/2020-12-09_Virtual Town Hall 36_fixnames.md"
    print(plot_segment_tokens(cur_file_path))
def mtest_split_file_select_speaker():
    pass
#if __name__ == "__main__":  
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    new_file_path = split_file_select_speaker(cur_file_path, speaker="Test Expert")
    line_numbers = get_line_numbers_with_match(new_file_path, "---")
    print(line_numbers)
    print(line_numbers == [10, 16])
def mtest_split_file_every_speaker():
    pass
#if __name__ == "__main__":        
    #cur_file_path = "tests/test_data_files/llm/dialogue.md"
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    new_file_path = split_file_every_speaker(cur_file_path)
    line_numbers = get_line_numbers_with_match(new_file_path, "---")
    print(line_numbers)
    print(line_numbers == [10, 13, 16, 19, 22])
def mtest_split_file_token_cap():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    new_file_path = split_file_token_cap(cur_file_path, token_cap=20)
    line_numbers = get_line_numbers_with_match(new_file_path, "---")
    print(line_numbers)
    print(line_numbers == [13, 16])
    
### OPENAI LLM
def mrun_get_openai_models():
    pass
#if __name__ == "__main__":
    api_key = OPENAI_API_KEY_T5
    get_openai_models(api_key)
def mrun_test_openai_connection():
    pass
#if __name__ == "__main__":
    test_openai_connection()

def mtest_test_openai_chat():
    pass
#if __name__ == "__main__":
    #generate_openai_testcurl_command()
    print("testing test_openai_chat")
    test_openai_chat()
def mtest_openai_chat_completion_request():
    pass
#if __name__ == "__main__":
    messages = [{"role": "user", "content": "What is the meaning of life?"}]
    response = openai_chat_completion_request(messages=messages)
    print("Response:", response.json()['choices'][0]['message']['content'])
def mtest_openai_chat_completion_request_sdk():
    pass
#if __name__ == "__main__":
    query = "Give me a silly math joke"
    model = "gpt-4o"
    messages = [{"role": "user", "content": query}]
    response = openai_chat_completion_request_sdk(messages=messages, model=model)
    datetime = get_current_datetime_filefriendly()
    save_llm_response_files(response, datetime, model, query)
    print("Response:", response.choices[0].message.content)
def mtest_simple_openai_chat_completion_request():
    pass
#if __name__ == "__main__":
    prompt = "Give me a good science dad joke?"
    model=OPENAI_MODEL
    #model="o1"
    response = simple_openai_chat_completion_request(prompt=prompt, model=model)
    print("Response:", response)
def mtest_openai_function_call():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    content = read_complete_text(cur_file_path)
    print(openai_function_call("turn the text into 2 lines that rhyme", content, tools=TOOLS_FCALL_TEST_RHYME))

### ANTHROPIC LLM
def mtest_anthropic_chat_completion_request():
    pass
#if __name__ == "__main__":
    messages = [{"role": "user", "content": "What is the meaning of life?"}]
    response = anthropic_chat_completion_request(messages=messages)
    print("Response:", response)
def mtest_simple_anthropic_chat():
    pass
#if __name__ == "__main__":
    cur_prompt = "give me a corny Dad joke"
    print(simple_anthropic_chat(cur_prompt))
def mtest_anthropic_function_call():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    content = read_complete_text(cur_file_path)
    print(anthropic_function_call("turn the text into 2 lines that rhyme", content, tools=TOOLS_ANT_FCALL_TEST_JOKE))

### DEEPSEEK
def mtest_test_deepseek_connection():
    pass
#if __name__ == "__main__":
    test_deepseek_connection()
def mtest_test_deepseek_chat():
    pass
#if __name__ == "__main__":
    test_deepseek_chat()
def mtest_deepseek_chat_completion_request_sdk():
    pass
if __name__ == "__main__":
    prompt = """
Explain this quote:
'It is usually thought that consent can be determined by looking at the state of mind of the affirming party alone. If someone gave explicit affirmation, so it is said, he consented. But now that we have established the need for the regard for consent by the other party, we can see that that is not necessarily the case. To distinguish between actual consent and the mere sanctioning of force, one must consider the mental states and intentions of everyone involved. It is the offenders who turn their victim's consent on its head, not the victims themselves. So at most, the affirming party can invite the other party to make the intention consensual. Accordingly, people can be mistaken about whether they are consenting or being coerced. That's because they have strictly limited visibility into other people's minds and even their own. They can also be mistaken in thinking they have regard for consent when it comes to others.'
Give some examples.
"""
    messages = [{"role": "user", "content": prompt}]
    response = deepseek_chat_completion_request_sdk(messages=messages)
    print("Response:", response)
def mtest_simple_deepseek_chat():
    pass
#if __name__ == "__main__":
    prompt = "What is politics so screwed up?"
    print(simple_deepseek_chat(prompt))

### REASONING
def mrun_openai_chat_completion_request_sdk_reasoning():
    pass
#if __name__ == "__main__":
    #reasoning_model="o3-mini"
    reasoning_model="deepseek-reasoner"
    user_prompt = "Create a surefire project plan for teaching a 6 year old logic."
    reasoning_effort='medium'  # 'low', 'medium', 'high' default is 'medium'
    max_completion_tokens=50000
    messages = [{"role": "user", "content": user_prompt}]
    response = openai_chat_completion_request_sdk(messages=messages, model=reasoning_model, max_completion_tokens=max_completion_tokens, reasoning_effort=reasoning_effort)    
    if isinstance(response, Exception):
        print(colored("*** ERROR ***", "red"))
        print(f"Error type: {type(response)}")
        print(f"Error message: {str(response)}")
    else:
        print(colored("Full response object:", "green"))
        print(response)
        print(colored("\nResponse content:", "green"))
        print(response.choices[0].message.content)
        
        reasoning_response_json = convert_data_object_to_json_data(response, default_handler=None, verbose=True, print_analysis=True, print_values=True)
        compare_reasoning_model_cost_table_from_response(reasoning_response_json)
def mtest_reasoning_response_to_md_multipart():
    pass
#if __name__ == "__main__":
    choose = "deepseek"
    #choose = "openai"
    if choose == "deepseek":
        pickle_file_path = "exchanges/response_files/chat_response_2025-02-11_191321_deepseek-reasoner_What is a thorough response to.pkl"
    elif choose == "openai":
        pickle_file_path = "exchanges/response_files/chat_response_2025-02-11_190841_o3-mini_What is a thorough response to.pkl"
    else:
        ValueError("Invalid choice of choose :)")
    response = get_object_from_pickle_file(pickle_file_path, verbose=True, print_object=True)
    prompt_parts = {
        'prompt_initial': "dummy prompt_initial",
        'query': "dummy query - " + choose,
        'query_context': "dummy query_context",
        'rag_context': "dummy rag_context",
        'large_context': "dummy large_context",
        'large_context_file_path': "dummy large_context_file_path"
    }
    md_file_path = "exchanges/response_files/test_reasoning_response_to_md_multipart.md"
    datetime_now = get_current_datetime_filefriendly()

    # json_file_path = pickle_file_path.replace(".pkl", ".json")
    # json_data = convert_data_object_to_json_data(response, default_handler=None, verbose=True, print_analysis=True, print_values=True)
    # print(f"json_data:\n{json_data}")
    # write_json_file_from_json_data(json_data, json_file_path, overwrite="yes")

    if choose == "deepseek":
        reasoning_response_to_md_multipart_deepseek(prompt_parts, response, "deepseek-reasoner-pickle", md_file_path, datetime_now)
    else:
        reasoning_response_to_md_multipart_openai(prompt_parts, response, "o3-mini-pickle", md_file_path, datetime_now)
def mtest_get_call_cost_from_response():
    pass
#if __name__ == "__main__":
    #choose = "deepseek"
    choose = "openai"
    if choose == "deepseek":
        pickle_file_path = "exchanges/response_files/chat_response_2025-02-11_191321_deepseek-reasoner_What is a thorough response to.pkl"
        model = "deepseek-reasoner"
    elif choose == "openai":
        pickle_file_path = "exchanges/response_files/chat_response_2025-02-11_190841_o3-mini_What is a thorough response to.pkl"
        model = "o3-mini"
    else:
        ValueError("Invalid choice of choose :)")
    response = get_object_from_pickle_file(pickle_file_path, verbose=False, print_object=False)
    cost = get_call_cost_from_response(response, model, TOKEN_PRICE_DICT, verbose=True)
    print(f"get_call_cost_from_response: {cost}")

### LLM PROCESSING
def mtest_scall_replace():
    pass
#if __name__ == "__main__":
    cur_blocks_file_path = "tests/test_data_files/llm/dialogue_blocks.md"
    MY_PROMPT = "turn the text into 2 lines that rhyme"
    print(scall_replace(cur_blocks_file_path, MY_PROMPT, suffix_new='_scall-replace-poem', retain_delimiters=True))
def mtest_scall_append():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/dialogue_blocks.md"
    MY_PROMPT = "make a onery redneck response to this as a single sentence in all caps"
    print(scall_append(cur_file_path, MY_PROMPT, suffix_new='_scall-append-redneck', retain_delimiters=True))
def mtest_create_simple_llm_file():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    #MY_PROMPT = "turn the text into a short corny Dad joke"
    #print(create_simple_llm_file(cur_file_path, MY_PROMPT, "_dadjoke", "replace", split_file_every_speaker_ffop))
    MY_PROMPT = "reply with what a California valley girl would say about this"
    print(create_simple_llm_file(cur_file_path, MY_PROMPT, "_create-simple-llm-file-replace-valleygirl", "replace", split_file_every_speaker))

#### COPYEDIT
# TODO needs updating to change to replacement for ffop function
def mtest_create_copyedit_file():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    #cur_file_path = "tests/test_data_files/llm/dialogue.md"
    #create_copyedit_file(cur_file_path, split_file_select_speaker_ffop, PROMPT_COPYEDIT, speaker="Test Expert")
    create_copyedit_file(cur_file_path, split_file_every_speaker_ffop, PROMPT_COPYEDIT)
    #create_copyedit_file(cur_file_path, split_file_token_cap_ffop, PROMPT_COPYEDIT, token_cap=1000)

#### TRANSITIONS
def mtest_mod_blocks_file_with_adjacent_words():
    pass
#if __name__ == "__main__":
    # copy the file "1900-01-01_scall test file_blocksREF.md" and rename as just _blocks, then when this mtest works use that _blocks file with the next mtest
    cur_file_path = "tests/test_data_files/llm/dialogue_blocks.md"
    mod_blocks_file_with_adjacent_words(cur_file_path, 5)
def mtest_scall_replace_adjacent_words():
    pass
#if __name__ == "__main__":
    # use the modified _blocks file from the above mtest
    cur_file_path = "tests/test_data_files/llm/dialogue_blocks.md"
    print(scall_replace_adjacent_words(cur_file_path, PROMPT_TRANSITIONS, 10, overwrite="no-sub"))
def mtest_create_transitions_file():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/dialogue.md"
    print(create_transitions_file(cur_file_path, split_file_every_speaker, PROMPT_TRANSITIONS))

#### QA
def mtest_create_qa_file_select_speaker(): 
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/llm/qa_input.md"
    print(create_qa_file_select_speaker(cur_file_path, "Test Expert", FCALL_PROMPT_QA_DIALOGUE_FROMANSWER))
def mtest_create_qa_file_incremental():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/floodlamp/reg/fda-townhalls/dev/VTH 36_cemanual-splits-1stq.md"
    create_qa_file_from_transcript_incremental(cur_file_path, FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_6C)
def mtest_get_delimiter_line_numbers():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/floodlamp/reg/fda-townhalls/dev/VTH 36_cemanual-sections.md"
    print(get_delimiter_line_numbers(cur_file_path))
def mtest_fcall_meeting_sections():  # Not used - use add_transcript_section_delimiters instead
    pass
#if __name__ == "__main__":
    cur_file_path = "data/floodlamp/reg/fda-townhalls/dev/VTH 36_cemanual.md"
    print("fcall_meeting_sections response:")
    print(fcall_meeting_sections(cur_file_path))
    cur_file_path = "data/floodlamp/reg/fda-townhalls/dev/VTH 36_cemanual-sections.md"
    print("expected output:")
    print(get_delimiter_line_numbers(cur_file_path))


def mrun_create_qa_file_from_transcript_sections():
    pass
#if __name__ == "__main__":
    #cur_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/2020-10-14_Virtual Town Hall 30_fixnames.md"
    cur_file_path = CUR_FILE_PATH
    provider = "openai"
    # provider = "anthropic"
    output_qa_file = create_qa_file_from_transcript_sections(cur_file_path, FCALL_SYSTEM_PROMPT_QA_SECTIONS_TRANSCRIPT_FDA_TOWNHALLS_1B, provider=provider)
    os.rename(output_qa_file, output_qa_file.replace("_qa-created", "_qa-created-1"))
    output_qa_file = create_qa_file_from_transcript_sections(cur_file_path, FCALL_SYSTEM_PROMPT_QA_SECTIONS_TRANSCRIPT_FDA_TOWNHALLS_1B, provider=provider)
    os.rename(output_qa_file, output_qa_file.replace("_qa-created", "_qa-created-2"))

    # output_qa_file = create_qa_file_from_transcript_sections(cur_file_path, FCALL_SYSTEM_PROMPT_QA_SECTIONS_TRANSCRIPT_FDA_TOWNHALLS_1B, provider=provider)
    # os.rename(output_qa_file, output_qa_file.replace("_qa-sec", f"_qa-sec_zz-ant-3"))

    # provider = "openai"
    # output_qa_file = create_qa_file_from_transcript_sections(cur_file_path, FCALL_SYSTEM_PROMPT_QA_SECTIONS_TRANSCRIPT_FDA_TOWNHALLS_1B, provider=provider)
    # os.rename(output_qa_file, output_qa_file.replace("_qa-sec", f"_qa-sec_zz-oai-4-prevQ3times"))



def mtest_run_automated_evaluation():
    pass
#if __name__ == "__main__":
    transcript_file = "data/floodlamp/reg/fda-townhalls/dev/VTH 36_cemanual.md"
    qa_file = "data/floodlamp/reg/fda-townhalls/dev/VHT 36_qa-inc.md"
    run_automated_evaluation(transcript_file, qa_file)
    
    # pos_start = 3977
    # pos_end = pos_start + 100
    # transcript = get_heading(transcript_file, "### transcript")
    # transcript = transcript.lstrip('### transcript').rstrip('\n').lstrip('\n*')
    # print(transcript[pos_start:pos_end])

# ===== END OF FILE core/llm_mtest.py =====
