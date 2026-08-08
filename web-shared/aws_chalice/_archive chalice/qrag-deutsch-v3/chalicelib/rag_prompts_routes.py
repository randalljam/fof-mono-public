
ROUTES_DICT_DEUTSCH_V3 = {
    'routes_dict_name': 'ROUTES_DICT_DEUTSCH_V3',  # mirror global variable name

    'prompt_initial_good_match': 'Given your knowledge of David Deutsch and his philosophy of deep optimism, as well as the QUOTED QUESTIONS AND ANSWERS from Deutsch below, to answer the USER QUESTION below.\n',

    'route_preamble_good_match': 'There is a good match of your question in David Deutsch\'s interviews. See his QUOTED QUESTIONS AND ANSWERS below followed by an AI ANSWER that synthesizes these quotes with David Deutsch\'s philosophy and your exact question.',

    'prompt_initial_partial_match': 'Given your knowledge of David Deutsch and his philosophy of deep optimism, as well as the QUOTED QUESTIONS AND ANSWERS from Deutsch below, to answer the USER QUESTION below.\n',

    'route_preamble_partial_match': 'There is a partial match of your question in David Deutsch\'s interviews. See his QUOTED QUESTIONS AND ANSWERS below followed by an AI ANSWER that synthesizes these quotes with David Deutsch\'s philosophy and your exact question.',

    'prompt_initial_no_match': 'Given your knowledge of David Deutsch and his philosophy of deep optimism, answer the USER QUESTION below.\n',

    'route_preamble_no_match': 'Your question is not addressed in David Deutsch\'s interviews. No QUOTED QUESTIONS AND ANSWERS are therefore provided but here is an AI ANSWER that synthesizes David Deutsch\'s philosophy and your question.',

    'quoted_qa_single': 'QUOTED QUESTION: {top_sim_question}\nQUOTED SOURCE: {top_sim_source}\nQUOTED TIMESTAMP: {top_sim_timestamp}\nQUOTED ANSWER: {top_sim_answer}\n{top_sim_display}\n\n',

    'quoted_qa_double': 'QUOTED QUESTION 1: {top_stars_question}\nQUOTED SOURCE 1: {top_stars_source}\nQUOTED TIMESTAMP 1: {top_stars_timestamp}\nQUOTED ANSWER 1: {top_stars_answer}\n{top_stars_display}\n\nQUOTED QUESTION 2: {top_sim_question}\nQUOTED SOURCE 2: {top_sim_source}\nQUOTED TIMESTAMP 2: {top_sim_timestamp}\nQUOTED ANSWER 2: {top_sim_answer}\n{top_sim_display}\n\n',

    'user_ai_qa': 'USER QUESTION: {user_question}\n\nAI ANSWER: '
}
