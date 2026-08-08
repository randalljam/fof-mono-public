## API Gateway Validation Test Results



## ====== Testing qrag-llm  2026-03-22_071842 ======


## ====== clean_requests for qrag-llm ======

## clean_requests           Request 1: Complete matching Portal API Gateway test
Original: {
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
}
Complete: {
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"In a David Deutsch-ish spirit: don\\u2019t ask \\u201cWhat is the correct lunch?\\u201d Ask \\u201cWhat problem am I trying to solve, and what\\u2019s a good conjectured solution I can test?\\u201d\\n\\nSo:\\n\\n1. Define the problem:\\n   - Hunger?\\n   - Need steady energy?\\n   - Want something healthy?\\n   - Limited time?\\n   - Want enjoyment too?\\n\\n2. Propose a decent explanation-based solution:\\n   - A lunch with protein, vegetables, and something filling but not heavy is often a good guess.\\n\\n3. Critically prefer options that solve more problems at once.\\n\\nA good Deutsch-compatible lunch recommendation would be:\\n\\n- Grilled chicken or tofu\\n- Rice, potatoes, or bread\\n- A lot of vegetables\\n- Fruit or yogurt if you want something extra\\n\\nFor example:\\n- Chicken bowl with rice, beans, and salad\\n- Tofu stir-fry with vegetables and noodles\\n- Turkey or hummus sandwich with salad and fruit\\n- Omelet with vegetables and toast\\n\\nIf you want the most Deutsch-sounding answer:\\n> Eat something that is a good, improvable explanation for your current nutritional and practical needs \\u2014 then criticize the result afterward and do better tomorrow.\\n\\nIf you want, I can also give you:\\n- the \\u201cDeutsch would approve\\u201d healthy lunch,\\n- the fastest possible lunch,\\n- or the tastiest lunch.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 47, \"output_tokens\": 340, \"reasoning_tokens\": 57, \"cost_pennies_mycalc\": 0.522}}}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"In a David Deutsch-ish spirit: don\\u2019t ask \\u201cWhat is the correct lunch?\\u201d Ask \\u201cWhat problem am I trying to solve, and what\\u2019s a good conjectured solution I can test?\\u201d\\n\\nSo:\\n\\n1. Define the problem:\\n   - Hunger?\\n   - Need steady energy?\\n   - Want something healthy?\\n   - Limited time?\\n   - Want enjoyment too?\\n\\n2. Propose a decent explanation-based solution:\\n   - A lunch with protein, vegetables, and something filling but not heavy is often a good guess.\\n\\n3. Critically prefer options that solve more problems at once.\\n\\nA good Deutsch-compatible lunch recommendation would be:\\n\\n- Grilled chicken or tofu\\n- Rice, potatoes, or bread\\n- A lot of vegetables\\n- Fruit or yogurt if you want something extra\\n\\nFor example:\\n- Chicken bowl with rice, beans, and salad\\n- Tofu stir-fry with vegetables and noodles\\n- Turkey or hummus sandwich with salad and fruit\\n- Omelet with vegetables and toast\\n\\nIf you want the most Deutsch-sounding answer:\\n> Eat something that is a good, improvable explanation for your current nutritional and practical needs \\u2014 then criticize the result afterward and do better tomorrow.\\n\\nIf you want, I can also give you:\\n- the \\u201cDeutsch would approve\\u201d healthy lunch,\\n- the fastest possible lunch,\\n- or the tastiest lunch.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 47, \"output_tokens\": 340, \"reasoning_tokens\": 57, \"cost_pennies_mycalc\": 0.522}}}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
Result:
{
  "status": "Success",
  "response": {
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
      },
      "llm_model": "gpt-5.4",
      "reasoning_effort": "low"
    },
    "content": {
      "user_question": "What should I eat for lunch?",
      "route_preamble": "Your question is not addressed in David Deutsch's interviews.",
      "prompt_initial": "Given your knowledge of David Deutsch and his philosophy...",
      "quoted_qa": "",
      "ai_answer": "In a vaguely David-Deutsch-ish spirit:\n\nThere is no authoritative \u201ccorrect lunch\u201d handed down by tradition, instinct, or nutritional mysticism. There are only conjectures about what would work well, and then criticism of those conjectures.\n\nSo:\n\n1. Make a guess that solves the actual problem.\n   Your problem is probably some mix of:\n   - hunger\n   - nutrition\n   - enjoyment\n   - convenience\n   - not feeling awful afterward\n\n2. Reject bad explanations.\n   For example:\n   - \u201cI should eat this because people always eat it at lunch\u201d \u2014 bad explanation.\n   - \u201cI crave sugar, therefore sugar is what I need\u201d \u2014 bad explanation.\n   - \u201cThis meal has protein, fiber, and won\u2019t wreck my afternoon energy\u201d \u2014 better explanation.\n\n3. Choose something good enough, not \u201ccertain.\u201d\n\nA decent Deutsch-compatible lunch conjecture would be:\n\n- protein\n- vegetables\n- something starchy if you need energy\n- something you actually like\n\nExample:\n- grilled chicken or tofu\n- rice or potatoes\n- salad or roasted vegetables\n\nIf you want a single concrete answer:\nEat a chicken bowl with rice, beans, vegetables, and some salsa \u2014 or the tofu equivalent.\n\nThat\u2019s not \u201ctrue by authority\u201d; it\u2019s just a reasonably good explanation-backed proposal.\n\nIf you want, I can also answer this in:\n- \u201cDavid Deutsch actually speaking\u201d style\n- \u201cBeginning of Infinity\u201d style\n- or as a more practical lunch recommendation based on what food you have.",
      "retrieved_content": {
        "max_sim": "0.216",
        "max_stars": 5,
        "chunks": []
      },
      "input_tokens": 47,
      "output_tokens": 399,
      "reasoning_tokens": 78,
      "cost_pennies_mycalc": 0.61
    }
  }
}

## clean_requests           Request 2: Complete matching Portal API Gateway test with large context filename
Original: {
  "description": "Complete matching Portal API Gateway test with large context filename",
  "request": {
    "metadata": {
      "large_context_filename": "deutsch_large_context_v1.md"
    }
  }
}
Complete: {
  "description": "Complete matching Portal API Gateway test with large context filename",
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
      },
      "large_context_filename": "deutsch_large_context_v1.md"
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"large_context_filename\": \"deutsch_large_context_v1.md\", \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"A Deutschian answer would be something like:\\n\\nDon\\u2019t ask \\u201cWhat is the correct lunch?\\u201d as if there were an authority or algorithm that can justify it.\\n\\nAsk instead: **what problem is lunch supposed to solve today?**\\n\\nFor example:\\n\\n- **Fuel/health problem:** you want something nutritious that won\\u2019t make you sluggish.\\n- **Time problem:** you need something fast.\\n- **Enjoyment problem:** lunch should also be pleasant.\\n- **Productivity problem:** you want stable energy for the afternoon.\\n- **Experimentation problem:** you may want to try improving your eating habits.\\n\\nSo the rational move is to **conjecture a few options** and **criticize them**.\\n\\nA generally good, hard-to-vary lunch candidate is:\\n\\n**A meal built around protein + vegetables + a slow carb + something you actually like.**\\n\\nExamples:\\n- grilled chicken, rice, salad\\n- omelet with vegetables and toast\\n- beans, quinoa, roasted vegetables\\n- salmon sandwich with fruit\\n- tofu stir-fry with rice\\n\\nWhy this is \\u201cDeutsch-compatible\\u201d:\\n- it solves multiple problems at once\\n- it\\u2019s adaptable without being arbitrary\\n- it avoids both blind rule-following and random impulse\\n- it treats lunch as a problem-solving activity, not obedience to diet authority\\n\\nIf you want one concrete answer:\\n\\n**Eat a bowl with chicken or tofu, rice or potatoes, lots of vegetables, and a flavorful sauce.**\\n\\nIf you want, I can also give you:\\n1. a **David Deutsch-style decision procedure for lunch**, or  \\n2. **3 lunch options based on your actual constraints**.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"large_context_filename\": \"deutsch_large_context_v1.md\", \"input_tokens\": 12573, \"output_tokens\": 388, \"reasoning_tokens\": 49, \"cost_pennies_mycalc\": 3.725}}}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"large_context_filename\": \"deutsch_large_context_v1.md\", \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"A Deutschian answer would be something like:\\n\\nDon\\u2019t ask \\u201cWhat is the correct lunch?\\u201d as if there were an authority or algorithm that can justify it.\\n\\nAsk instead: **what problem is lunch supposed to solve today?**\\n\\nFor example:\\n\\n- **Fuel/health problem:** you want something nutritious that won\\u2019t make you sluggish.\\n- **Time problem:** you need something fast.\\n- **Enjoyment problem:** lunch should also be pleasant.\\n- **Productivity problem:** you want stable energy for the afternoon.\\n- **Experimentation problem:** you may want to try improving your eating habits.\\n\\nSo the rational move is to **conjecture a few options** and **criticize them**.\\n\\nA generally good, hard-to-vary lunch candidate is:\\n\\n**A meal built around protein + vegetables + a slow carb + something you actually like.**\\n\\nExamples:\\n- grilled chicken, rice, salad\\n- omelet with vegetables and toast\\n- beans, quinoa, roasted vegetables\\n- salmon sandwich with fruit\\n- tofu stir-fry with rice\\n\\nWhy this is \\u201cDeutsch-compatible\\u201d:\\n- it solves multiple problems at once\\n- it\\u2019s adaptable without being arbitrary\\n- it avoids both blind rule-following and random impulse\\n- it treats lunch as a problem-solving activity, not obedience to diet authority\\n\\nIf you want one concrete answer:\\n\\n**Eat a bowl with chicken or tofu, rice or potatoes, lots of vegetables, and a flavorful sauce.**\\n\\nIf you want, I can also give you:\\n1. a **David Deutsch-style decision procedure for lunch**, or  \\n2. **3 lunch options based on your actual constraints**.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"large_context_filename\": \"deutsch_large_context_v1.md\", \"input_tokens\": 12573, \"output_tokens\": 388, \"reasoning_tokens\": 49, \"cost_pennies_mycalc\": 3.725}}}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
    },
    "large_context_filename": "deutsch_large_context_v1.md"
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
Result:
{
  "status": "Success",
  "response": {
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
      },
      "large_context_filename": "deutsch_large_context_v1.md",
      "llm_model": "gpt-5.4",
      "reasoning_effort": "low"
    },
    "content": {
      "user_question": "What should I eat for lunch?",
      "route_preamble": "Your question is not addressed in David Deutsch's interviews.",
      "prompt_initial": "Given your knowledge of David Deutsch and his philosophy...",
      "quoted_qa": "",
      "ai_answer": "In a Deutschian spirit: don\u2019t ask for an authority-approved lunch. Treat it as a problem-solving exercise.\n\nA good lunch is one that solves your actual constraints:\n- hunger\n- time\n- energy later\n- enjoyment\n- health\n- cost\n\nSo the best answer is:\n\n**Eat something you\u2019re likely to enjoy, that won\u2019t make your afternoon worse, and that fits your constraints.**\n\nA simple hard-to-vary heuristic:\n1. **Protein**\n2. **Some plants/fiber**\n3. **Not so much junk that you crash after**\n4. **Something easy enough that you\u2019ll actually do it**\n\nSo, if you want a concrete recommendation:\n\n- **If you want the safest default:** a chicken/rice/vegetable bowl, or tofu/grain/vegetable bowl\n- **If you want fast and decent:** sandwich or wrap with protein + salad/fruit\n- **If you want comfort without self-sabotage:** burrito bowl, not a giant greasy meal\n- **If you want cheap:** eggs, beans, rice, yogurt, fruit\n- **If you\u2019re mentally tired:** choose the option with the fewest decisions and highest reliability\n\nIf I were applying Deutsch\u2019s philosophy more explicitly, I\u2019d say:\n- there is no infallible lunch authority;\n- you should make a conjecture about what will work;\n- criticize it using your actual afternoon plans;\n- then eat and update next time.\n\nSo my practical answer is:\n\n**Have a bowl or wrap with protein, vegetables, and a carb you tolerate well.**  \nExample: **chicken or tofu, rice, greens, beans, salsa.**\n\nIf you want, I can turn this into a **\u201cDavid Deutsch-style lunch chooser\u201d** based on your goals: tasty, healthy, cheap, fast, or high-energy.",
      "retrieved_content": {
        "max_sim": "0.216",
        "max_stars": 5,
        "chunks": []
      },
      "large_context_filename": "deutsch_large_context_v1.md",
      "input_tokens": 12573,
      "output_tokens": 441,
      "reasoning_tokens": 57,
      "cached_input_tokens": 12032,
      "cost_pennies_mycalc": 1.098
    }
  }
}

## clean_requests           Request 3: Test retry flag
Original: {
  "description": "Test retry flag",
  "request": {
    "metadata": {
      "is_retry": true
    }
  }
}
Complete: {
  "description": "Test retry flag",
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
      },
      "is_retry": true
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"is_retry\": true, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"none\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"David Deutsch would probably say this is not a question with a single authoritative answer waiting to be \\u201cderived.\\u201d It\\u2019s a problem of **creating good explanations** and then **choosing based on your preferences, constraints, and willingness to correct errors**.\\n\\nSo, in a Deutsch-ish spirit:\\n\\n## Good lunch-choice method\\nAsk:\\n1. **What are your constraints?**\\n   - Hungry now?\\n   - Need cheap?\\n   - Need fast?\\n   - Want healthy?\\n   - Need something that won\\u2019t make you sleepy?\\n2. **What problem are you trying to solve?**\\n   - Pleasure?\\n   - Nutrition?\\n   - Convenience?\\n   - Social lunch?\\n3. **Pick the best current conjecture**, then improve next time if it was wrong.\\n\\n## My best conjecture without more info\\nEat something that is:\\n- **simple**\\n- **nutritious**\\n- **unlikely to cause an afternoon crash**\\n\\nA solid default:\\n- **Grilled chicken or tofu bowl**\\n- with **rice or potatoes**\\n- and **vegetables**\\n- plus water\\n\\nIf you want something more universally practical:\\n- **A sandwich or wrap with protein, vegetables, and fruit on the side**\\n\\n## Deutsch-flavored principle\\nDon\\u2019t seek certainty about lunch.  \\nChoose a **good, testable option**, then if it\\u2019s bad, you\\u2019ve learned something and can improve tomorrow.\\n\\n## Short answer\\n**Have a protein-and-vegetable-based lunch with some carbs: e.g. a chicken/tofu rice bowl or a good sandwich.**\\n\\nIf you want, I can answer this in a **more specifically David Deutsch style**, or help you pick lunch based on:\\n- what food you have\\n- your budget\\n- whether you want healthy vs indulgent\\n- whether you want what Deutsch himself might plausibly choose rhetorically.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 47, \"output_tokens\": 381, \"cost_pennies_mycalc\": 0.583}}}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"is_retry\": true, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"none\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"David Deutsch would probably say this is not a question with a single authoritative answer waiting to be \\u201cderived.\\u201d It\\u2019s a problem of **creating good explanations** and then **choosing based on your preferences, constraints, and willingness to correct errors**.\\n\\nSo, in a Deutsch-ish spirit:\\n\\n## Good lunch-choice method\\nAsk:\\n1. **What are your constraints?**\\n   - Hungry now?\\n   - Need cheap?\\n   - Need fast?\\n   - Want healthy?\\n   - Need something that won\\u2019t make you sleepy?\\n2. **What problem are you trying to solve?**\\n   - Pleasure?\\n   - Nutrition?\\n   - Convenience?\\n   - Social lunch?\\n3. **Pick the best current conjecture**, then improve next time if it was wrong.\\n\\n## My best conjecture without more info\\nEat something that is:\\n- **simple**\\n- **nutritious**\\n- **unlikely to cause an afternoon crash**\\n\\nA solid default:\\n- **Grilled chicken or tofu bowl**\\n- with **rice or potatoes**\\n- and **vegetables**\\n- plus water\\n\\nIf you want something more universally practical:\\n- **A sandwich or wrap with protein, vegetables, and fruit on the side**\\n\\n## Deutsch-flavored principle\\nDon\\u2019t seek certainty about lunch.  \\nChoose a **good, testable option**, then if it\\u2019s bad, you\\u2019ve learned something and can improve tomorrow.\\n\\n## Short answer\\n**Have a protein-and-vegetable-based lunch with some carbs: e.g. a chicken/tofu rice bowl or a good sandwich.**\\n\\nIf you want, I can answer this in a **more specifically David Deutsch style**, or help you pick lunch based on:\\n- what food you have\\n- your budget\\n- whether you want healthy vs indulgent\\n- whether you want what Deutsch himself might plausibly choose rhetorically.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 47, \"output_tokens\": 381, \"cost_pennies_mycalc\": 0.583}}}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
    },
    "is_retry": true
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
Result:
{
  "status": "Success",
  "response": {
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
      },
      "is_retry": true,
      "llm_model": "gpt-5.4",
      "reasoning_effort": "none"
    },
    "content": {
      "user_question": "What should I eat for lunch?",
      "route_preamble": "Your question is not addressed in David Deutsch's interviews.",
      "prompt_initial": "Given your knowledge of David Deutsch and his philosophy...",
      "quoted_qa": "",
      "ai_answer": "David Deutsch would probably reject the idea that there is one authoritative, \u201ccorrect\u201d lunch dictated by expertise or tradition.\n\nA Deutsch-ish answer would be:\n\n- Your lunch choice is a problem-solving task.\n- Good choices come from conjecture and criticism.\n- So: propose some lunch options, then criticize them against your aims.\n\nFor example, ask:\n- Do you want energy for the afternoon?\n- Do you care about health?\n- Speed?\n- Cost?\n- Pleasure?\n- What ingredients do you actually have access to?\n\nThen form a testable guess:\n- \u201cA lunch with protein, vegetables, and something filling will keep me alert better than fast sugar.\u201d\n- \u201cIf I eat something too heavy, I may get sluggish.\u201d\n- \u201cIf I optimize only for health and ignore enjoyment, I may not sustain the habit.\u201d\n\nA reasonable provisional solution:\n- A grain bowl or salad with chicken, beans, tofu, or eggs\n- A sandwich with good protein and vegetables\n- Soup plus bread and fruit\n- Rice, vegetables, and some protein\n\nThe Deutsch angle is not \u201ceat X because authority says so,\u201d but:\n- create options\n- criticize them\n- choose the best current explanation for what will solve your lunch problem\n- be ready to improve next time\n\nSo the most Deutsch-like answer is:\nEat the lunch that best solves your current problem after criticism\u2014probably something nutritious, enjoyable, and unlikely to make you sleepy. If you want, I can make this more specifically Deutsch-like, funny, or actually practical based on what food you have.",
      "retrieved_content": {
        "max_sim": "0.216",
        "max_stars": 5,
        "chunks": []
      },
      "input_tokens": 47,
      "output_tokens": 318,
      "cost_pennies_mycalc": 0.489
    }
  }
}


## ====== schema_invalid_requests for qrag-llm ======

## schema_invalid_requests  Request 1: Exceeds maxLength
Original: {
  "description": "Exceeds maxLength",
  "request": {
    "metadata": {
      "timestamp": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    }
  }
}
Complete: {
  "description": "Exceeds maxLength",
  "request": {
    "metadata": {
      "timestamp": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"David Deutsch would probably say there is no authoritative, final answer to \\u201cwhat should I eat for lunch?\\u201d\\n\\nA Deutsch-style answer would be:\\n\\n- Form a few good conjectures.\\n- Critically evaluate them.\\n- Choose the one that best solves your current problem.\\n\\nSo first ask: what problem is lunch solving today?\\n\\n- **Need sustained energy?** Eat something with protein, fiber, and slow carbs.\\n- **Need speed/convenience?** Choose the simplest decent option you can get quickly.\\n- **Want enjoyment?** Pick something you\\u2019ll actually like.\\n- **Trying to improve your habits?** Treat lunch as an experiment and see what leaves you feeling best afterward.\\n\\nA good fallible-but-decent conjecture is:\\n\\n**A bowl or plate with:**\\n- protein: chicken, tofu, beans, eggs, fish\\n- vegetables\\n- a carb: rice, potatoes, whole grain bread, pasta\\n- something tasty enough that you\\u2019re glad you ate it\\n\\nFor example:\\n- **Chicken rice bowl with vegetables**\\n- **Bean burrito bowl**\\n- **Omelet with salad and toast**\\n- **Salmon, potatoes, and greens**\\n- **Tofu stir-fry with rice**\\n\\nVery Deutschian summary:\\n\\n**There is no perfect lunch, only better explanations for why one lunch may suit your purposes today.**\\n\\nIf you want, I can also give you:\\n1. a **Deutsch-style decision procedure** for lunch, or  \\n2. a **single concrete lunch recommendation** based on your goals.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 47, \"output_tokens\": 375, \"reasoning_tokens\": 56, \"cost_pennies_mycalc\": 0.574}}}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"What should I eat for lunch?\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"David Deutsch would probably say there is no authoritative, final answer to \\u201cwhat should I eat for lunch?\\u201d\\n\\nA Deutsch-style answer would be:\\n\\n- Form a few good conjectures.\\n- Critically evaluate them.\\n- Choose the one that best solves your current problem.\\n\\nSo first ask: what problem is lunch solving today?\\n\\n- **Need sustained energy?** Eat something with protein, fiber, and slow carbs.\\n- **Need speed/convenience?** Choose the simplest decent option you can get quickly.\\n- **Want enjoyment?** Pick something you\\u2019ll actually like.\\n- **Trying to improve your habits?** Treat lunch as an experiment and see what leaves you feeling best afterward.\\n\\nA good fallible-but-decent conjecture is:\\n\\n**A bowl or plate with:**\\n- protein: chicken, tofu, beans, eggs, fish\\n- vegetables\\n- a carb: rice, potatoes, whole grain bread, pasta\\n- something tasty enough that you\\u2019re glad you ate it\\n\\nFor example:\\n- **Chicken rice bowl with vegetables**\\n- **Bean burrito bowl**\\n- **Omelet with salad and toast**\\n- **Salmon, potatoes, and greens**\\n- **Tofu stir-fry with rice**\\n\\nVery Deutschian summary:\\n\\n**There is no perfect lunch, only better explanations for why one lunch may suit your purposes today.**\\n\\nIf you want, I can also give you:\\n1. a **Deutsch-style decision procedure** for lunch, or  \\n2. a **single concrete lunch recommendation** based on your goals.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 47, \"output_tokens\": 375, \"reasoning_tokens\": 56, \"cost_pennies_mycalc\": 0.574}}}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
  "metadata": {
    "timestamp": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
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
Result:
{
  "message": "Invalid request body"
}

## schema_invalid_requests  Request 2: Empty required field
Original: {
  "description": "Empty required field",
  "request": {
    "content": {
      "user_question": ""
    }
  }
}
Complete: {
  "description": "Empty required field",
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
      "user_question": "",
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"It looks like the actual question and quoted Q&A didn\\u2019t come through \\u2014 both sections are empty.\\n\\nPlease paste:\\n\\n1. Your question inside `<USER_QUESTION> ... </USER_QUESTION>`\\n2. The quoted material inside `<QUOTED_QA> ... </QUOTED_QA>`\\n\\nThen I can analyze it in light of David Deutsch\\u2019s views \\u2014 e.g. on:\\n- fallibilism\\n- optimism\\n- explanation vs authority\\n- epistemology / conjecture and criticism\\n- many-worlds\\n- morality and progress\\n- AGI / creativity / universality\\n\\nIf you want, you can also just paste the raw text without the tags.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 40, \"output_tokens\": 196, \"reasoning_tokens\": 51, \"cost_pennies_mycalc\": 0.304}}}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": \"\", \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"It looks like the actual question and quoted Q&A didn\\u2019t come through \\u2014 both sections are empty.\\n\\nPlease paste:\\n\\n1. Your question inside `<USER_QUESTION> ... </USER_QUESTION>`\\n2. The quoted material inside `<QUOTED_QA> ... </QUOTED_QA>`\\n\\nThen I can analyze it in light of David Deutsch\\u2019s views \\u2014 e.g. on:\\n- fallibilism\\n- optimism\\n- explanation vs authority\\n- epistemology / conjecture and criticism\\n- many-worlds\\n- morality and progress\\n- AGI / creativity / universality\\n\\nIf you want, you can also just paste the raw text without the tags.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 40, \"output_tokens\": 196, \"reasoning_tokens\": 51, \"cost_pennies_mycalc\": 0.304}}}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
    "user_question": "",
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
Result:
{
  "message": "Invalid request body"
}

## schema_invalid_requests  Request 3: Invalid data types in content
Original: {
  "description": "Invalid data types in content",
  "request": {
    "content": {
      "user_question": 12345
    }
  }
}
Complete: {
  "description": "Invalid data types in content",
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
      "user_question": 12345,
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": 12345, \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"I don\\u2019t see an actual question there\\u2014just `12345` inside the `<USER_QUESTION>` tags.\\n\\nIf you want, send me the real question and I can answer it in a David Deutsch\\u2013style frame, for example emphasizing:\\n\\n- fallibilism\\n- conjecture and criticism\\n- good explanations\\n- optimism about knowledge creation\\n- the open-endedness of progress\\n- the importance of error correction\\n\\nPaste the actual question and I\\u2019ll take it from there.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 43, \"output_tokens\": 197, \"reasoning_tokens\": 91, \"cost_pennies_mycalc\": 0.306}}}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 200,
  "body": "{\"status\": \"Success\", \"response\": {\"metadata\": {\"timestamp\": \"2024-06-13T11:46:33.651753\", \"user_id\": \"default\", \"vector_index_name\": \"deutsch-transcript-qrag-83f-20250202\", \"bot_version\": \"2.0\", \"routes_info\": {\"routes_flow_name\": \"3 routes, separate route prompts\", \"upper_sim_bound\": 0.9, \"lower_sim_bound\": 0.3, \"max_sim\": \"0.216\", \"max_stars\": 5, \"routes_dict_content\": {\"routes_dict_name\": \"ROUTES_DICT_DEUTSCH_M1\"}}, \"llm_model\": \"gpt-5.4\", \"reasoning_effort\": \"low\"}, \"content\": {\"user_question\": 12345, \"route_preamble\": \"Your question is not addressed in David Deutsch's interviews.\", \"prompt_initial\": \"Given your knowledge of David Deutsch and his philosophy...\", \"quoted_qa\": \"\", \"ai_answer\": \"I don\\u2019t see an actual question there\\u2014just `12345` inside the `<USER_QUESTION>` tags.\\n\\nIf you want, send me the real question and I can answer it in a David Deutsch\\u2013style frame, for example emphasizing:\\n\\n- fallibilism\\n- conjecture and criticism\\n- good explanations\\n- optimism about knowledge creation\\n- the open-endedness of progress\\n- the importance of error correction\\n\\nPaste the actual question and I\\u2019ll take it from there.\", \"retrieved_content\": {\"max_sim\": \"0.216\", \"max_stars\": 5, \"chunks\": []}, \"input_tokens\": 43, \"output_tokens\": 197, \"reasoning_tokens\": 91, \"cost_pennies_mycalc\": 0.306}}}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
    "user_question": 12345,
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
Result:
{
  "message": "Invalid request body"
}


## ====== function_invalid_requests for qrag-llm ======

## function_invalid_requestsRequest 1: Missing required top-level field
Original: {
  "description": "Missing required top-level field",
  "request": {
    "metadata": "__REMOVE_FIELD__"
  }
}
Complete: {
  "description": "Missing required top-level field",
  "request": {
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"'metadata'\", \"error_type\": \"KeyError\", \"traceback\": \"Traceback (most recent call last):\\n  File \\\"/var/task/app.py\\\", line 212, in handle_qrag_llm\\n    raise result['error']\\n  File \\\"/var/task/app.py\\\", line 167, in llm_worker\\n    result['response'] = qrag_llm_call(\\n                         ^^^^^^^^^^^^^^\\n  File \\\"/var/task/chalicelib/rag.py\\\", line 504, in qrag_llm_call\\n    qrag_json_object['metadata']['llm_model'] = llm_model\\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^\\nKeyError: 'metadata'\\n\"}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"'metadata'\", \"error_type\": \"KeyError\", \"traceback\": \"Traceback (most recent call last):\\n  File \\\"/var/task/app.py\\\", line 212, in handle_qrag_llm\\n    raise result['error']\\n  File \\\"/var/task/app.py\\\", line 167, in llm_worker\\n    result['response'] = qrag_llm_call(\\n                         ^^^^^^^^^^^^^^\\n  File \\\"/var/task/chalicelib/rag.py\\\", line 504, in qrag_llm_call\\n    qrag_json_object['metadata']['llm_model'] = llm_model\\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^\\nKeyError: 'metadata'\\n\"}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
Result:
{
  "message": "Invalid request body"
}

## function_invalid_requestsRequest 2: Missing required content field
Original: {
  "description": "Missing required content field",
  "request": {
    "content": {
      "user_question": "__REMOVE_FIELD__"
    }
  }
}
Complete: {
  "description": "Missing required content field",
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"Missing required fields in JSON object: user_question\", \"error_type\": \"ValueError\", \"traceback\": \"Traceback (most recent call last):\\n  File \\\"/var/task/app.py\\\", line 212, in handle_qrag_llm\\n    raise result['error']\\n  File \\\"/var/task/app.py\\\", line 167, in llm_worker\\n    result['response'] = qrag_llm_call(\\n                         ^^^^^^^^^^^^^^\\n  File \\\"/var/task/chalicelib/rag.py\\\", line 496, in qrag_llm_call\\n    raise ValueError(f\\\"Missing required fields in JSON object: {', '.join(missing_fields)}\\\")\\nValueError: Missing required fields in JSON object: user_question\\n\"}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"Missing required fields in JSON object: user_question\", \"error_type\": \"ValueError\", \"traceback\": \"Traceback (most recent call last):\\n  File \\\"/var/task/app.py\\\", line 212, in handle_qrag_llm\\n    raise result['error']\\n  File \\\"/var/task/app.py\\\", line 167, in llm_worker\\n    result['response'] = qrag_llm_call(\\n                         ^^^^^^^^^^^^^^\\n  File \\\"/var/task/chalicelib/rag.py\\\", line 496, in qrag_llm_call\\n    raise ValueError(f\\\"Missing required fields in JSON object: {', '.join(missing_fields)}\\\")\\nValueError: Missing required fields in JSON object: user_question\\n\"}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
Result:
{
  "message": "Invalid request body"
}

## function_invalid_requestsRequest 3: Invalid data types in metadata
Original: {
  "description": "Invalid data types in metadata",
  "request": {
    "metadata": {
      "vector_index_name": [
        "invalid-type"
      ]
    }
  }
}
Complete: {
  "description": "Invalid data types in metadata",
  "request": {
    "metadata": {
      "timestamp": "2024-06-13T11:46:33.651753",
      "user_id": "default",
      "vector_index_name": [
        "invalid-type"
      ],
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"'list' object has no attribute 'startswith'\", \"error_type\": \"AttributeError\", \"traceback\": \"Traceback (most recent call last):\\n  File \\\"/var/task/app.py\\\", line 230, in handle_qrag_llm\\n    if vector_index_name.startswith(\\\"deutsch\\\"):\\n       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\nAttributeError: 'list' object has no attribute 'startswith'\\n\"}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"'list' object has no attribute 'startswith'\", \"error_type\": \"AttributeError\", \"traceback\": \"Traceback (most recent call last):\\n  File \\\"/var/task/app.py\\\", line 230, in handle_qrag_llm\\n    if vector_index_name.startswith(\\\"deutsch\\\"):\\n       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\nAttributeError: 'list' object has no attribute 'startswith'\\n\"}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
  "metadata": {
    "timestamp": "2024-06-13T11:46:33.651753",
    "user_id": "default",
    "vector_index_name": [
      "invalid-type"
    ],
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
Result:
{
  "message": "Invalid request body"
}

## function_invalid_requestsRequest 4: Large context filename not in S3 folder
Original: {
  "description": "Large context filename not in S3 folder",
  "request": {
    "metadata": {
      "large_context_filename": "not-present-filename.md"
    }
  }
}
Complete: {
  "description": "Large context filename not in S3 folder",
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
      },
      "large_context_filename": "not-present-filename.md"
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
}

### DIRECT LAMBDA INVOCATION
Lambda response payload: {
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"Failed to load required large context from not-present-filename.md\", \"error_type\": \"LargeContextLoadError\", \"vector_index\": \"deutsch-transcript-qrag-83f-20250202\"}"
}
Result:
{
  "headers": {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Origin": "https://www.focusonfoundations.org"
  },
  "multiValueHeaders": {},
  "statusCode": 500,
  "body": "{\"error\": \"Failed to load required large context from not-present-filename.md\", \"error_type\": \"LargeContextLoadError\", \"vector_index\": \"deutsch-transcript-qrag-83f-20250202\"}"
}

### API GATEWAY INVOCATION
Request being sent to API Gateway:
{
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
    },
    "large_context_filename": "not-present-filename.md"
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
Result:
{
  "error": "Failed to load required large context from not-present-filename.md",
  "error_type": "LargeContextLoadError",
  "vector_index": "deutsch-transcript-qrag-83f-20250202"
}

## ===== API Gateway Validation Test Summary qrag-llm =====
API Gateway name: qrag-llm
API endpoint URL: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-llm

clean_requests (3 tests):
  Lambda Results: (expected SUCCESS)  ✓
    test 1:  SUCCESS
    test 2:  SUCCESS
    test 3:  SUCCESS
  Gateway Results: (expected SUCCESS)  ✓
    test 1:  SUCCESS
    test 2:  SUCCESS
    test 3:  SUCCESS

schema_invalid_requests (3 tests):
  Lambda Results: (expected SUCCESS)  ✓
    test 1:  SUCCESS
    test 2:  SUCCESS
    test 3:  SUCCESS
  Gateway Results: (expected ERROR)  ✓
    test 1:  ERROR
    test 2:  ERROR
    test 3:  ERROR

function_invalid_requests (4 tests):
  Lambda Results: (expected ERROR)  ✓
    test 1:  ERROR
    test 2:  ERROR
    test 3:  ERROR
    test 4:  ERROR
  Gateway Results: (expected ERROR)  ✓
    test 1:  ERROR
    test 2:  ERROR
    test 3:  ERROR
    test 4:  ERROR

Test Results: 20 passed, 0 failed  ✓
