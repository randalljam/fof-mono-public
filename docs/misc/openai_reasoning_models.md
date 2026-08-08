Reasoning models
================

Explore advanced reasoning and problem-solving models.

**OpenAI o1** series models are new large language models trained with reinforcement learning to perform complex reasoning. o1 models [think before they answer](https://openai.com/index/introducing-openai-o1-preview/), producing a long internal chain of thought before responding to the user. o1 models excel in scientific reasoning, ranking in the 89th percentile on competitive programming questions (Codeforces), placing among the top 500 students in the US in a qualifier for the USA Math Olympiad (AIME), and exceeding human PhD-level accuracy on a benchmark of physics, biology, and chemistry problems (GPQA).

There are two reasoning models available in the API:

1.  `o1`: designed to reason about hard problems using broad general knowledge about the world.
2.  `o1-mini`: a faster and more affordable version of o1, particularly adept at coding, math, and science tasks where extensive general knowledge isn't required.

Quickstart
----------

Both `o1` and `o1-mini` are available through the [chat completions](/docs/api-reference/chat/create) endpoint.

Using the o1 model

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const prompt = `
Write a bash script that takes a matrix represented as a string with 
format '[1,2],[3,4],[5,6]' and prints the transpose in the same format.
`;
 
const completion = await openai.chat.completions.create({
  model: "o1",
  messages: [
    {
      role: "user", 
      content: prompt
    }
  ]
});

console.log(completion.choices[0].message.content);
```

```python
from openai import OpenAI
client = OpenAI()

prompt = """
Write a bash script that takes a matrix represented as a string with 
format '[1,2],[3,4],[5,6]' and prints the transpose in the same format.
"""

response = client.chat.completions.create(
    model="o1",
    messages=[
        {
            "role": "user", 
            "content": prompt
        }
    ]
)

print(response.choices[0].message.content)
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "o1-preview",
    "messages": [
      {
        "role": "user",
        "content": "Write a bash script that takes a matrix represented as a string with format \"[1,2],[3,4],[5,6]\" and prints the transpose in the same format."
      }
    ]
  }'
```

Note that depending on the amount of reasoning required by the model to solve the problem, these requests can take significantly longer than other models - sometimes on the order of minutes.

How reasoning works
-------------------

The o1 models introduce **reasoning tokens**. The models use these reasoning tokens to "think", breaking down their understanding of the prompt and considering multiple approaches to generating a response. After generating reasoning tokens, the model produces an answer as visible completion tokens, and discards the reasoning tokens from its context.

Here is an example of a multi-step conversation between a user and an assistant. Input and output tokens from each step are carried over, while reasoning tokens are discarded.

![Reasoning tokens aren't retained in context](https://cdn.openai.com/API/docs/images/context-window.png)

While reasoning tokens are not visible via the API, they still occupy space in the model's context window and are billed as [output tokens](https://openai.com/api/pricing).

### Managing the context window

The o1 and o1-mini models offer a context window of 200,000 and 128,000 tokens respectively. Each completion has an upper limit on the maximum number of output tokens — this includes both the invisible reasoning tokens and the visible completion tokens. The maximum output token limits are:

*   o1: Up to 100,000 tokens
*   o1-mini: Up to 65,536 tokens

It's important to ensure there's enough space in the context window for reasoning tokens when creating completions. Depending on the problem's complexity, the models may generate anywhere from a few hundred to tens of thousands of reasoning tokens. The exact number of reasoning tokens used is visible in the [usage object of the chat completion response object](/docs/api-reference/chat/object), under `completion_tokens_details`:

```json
{
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21,
    "completion_tokens_details": {
      "reasoning_tokens": 0,
      "accepted_prediction_tokens": 0,
      "rejected_prediction_tokens": 0
    }
  }
}
```

### Controlling costs

To manage costs with the o1 series models, you can limit the total number of tokens the model generates (including both reasoning and completion tokens) by using the [`max_completion_tokens`](/docs/api-reference/chat/create#chat-create-max_completion_tokens) parameter.

In previous models, the `max_tokens` parameter controlled both the number of tokens generated and the number of tokens visible to the user, which were always equal. However, with the o1 series, the total tokens generated can exceed the number of visible tokens due to the internal reasoning tokens.

Because some applications might rely on `max_tokens` matching the number of tokens received from the API, the o1 series introduces `max_completion_tokens` to explicitly control the total number of tokens generated by the model, including both reasoning and visible completion tokens. This explicit opt-in ensures no existing applications break when using the new models. The `max_tokens` parameter continues to function as before for all previous models.

### Allocating space for reasoning

If the generated tokens reach the context window limit or the `max_completion_tokens` value you've set, you'll receive a chat completion response with the `finish_reason` set to `length`. This might occur before any visible completion tokens are produced, meaning you could incur costs for input and reasoning tokens without receiving a visible response.

To prevent this, ensure there's sufficient space in the context window or adjust the `max_completion_tokens` value to a higher number. OpenAI recommends reserving at least 25,000 tokens for reasoning and outputs when you start experimenting with these models. As you become familiar with the number of reasoning tokens your prompts require, you can adjust this buffer accordingly.

Advice on prompting
-------------------

These models perform best with straightforward prompts. Some prompt engineering techniques, like few-shot learning or instructing the model to "think step by step," may not enhance performance (and can sometimes hinder it). Here are some best practices:

*   **Developer messages are the new system messages:** Starting with `o1-2024-12-17`, o1 models support `developer` messages rather than `system` messages, to align with the [chain of command behavior described in the model spec](https://cdn.openai.com/spec/model-spec-2024-05-08.html#follow-the-chain-of-command). [Learn more](/docs/guides/text-generation#building-prompts).
*   **Keep prompts simple and direct:** The models excel at understanding and responding to brief, clear instructions without the need for extensive guidance.
*   **Avoid chain-of-thought prompts:** Since these models perform reasoning internally, prompting them to "think step by step" or "explain your reasoning" is unnecessary.
*   **Use delimiters for clarity:** Use delimiters like triple quotation marks, XML tags, or section titles to clearly indicate distinct parts of the input, helping the model interpret different sections appropriately.
*   **Limit additional context in retrieval-augmented generation (RAG):** When providing additional context or documents, include only the most relevant information to prevent the model from overcomplicating its response.
*   **Markdown formatting:** Starting with `o1-2024-12-17`, o1 models in the API will avoid generating responses with markdown formatting. To signal to the model when you **do** want markdown formatting in the response, include the string `Formatting re-enabled` on the first line of your `developer` message.

### Prompt examples

Coding (refactoring)

OpenAI o1 series models are able to implement complex algorithms and produce code. This prompt asks o1 to refactor a React component based on some specific criteria.

Ask o1 models to refactor code

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const prompt = `
Instructions:
- Given the React component below, change it so that nonfiction books have red
  text. 
- Return only the code in your reply
- Do not include any additional formatting, such as markdown code blocks
- For formatting, use four space tabs, and do not allow any lines of code to 
  exceed 80 columns

const books = [
  { title: 'Dune', category: 'fiction', id: 1 },
  { title: 'Frankenstein', category: 'fiction', id: 2 },
  { title: 'Moneyball', category: 'nonfiction', id: 3 },
];

export default function BookList() {
  const listItems = books.map(book =>
    <li>
      {book.title}
    </li>
  );

  return (
    <ul>{listItems}</ul>
  );
}
`.trim();

const completion = await openai.chat.completions.create({
  model: "o1-mini",
  messages: [
    {
      role: "user",
      content: prompt,
    },
  ]
});

console.log(completion.usage.completion_tokens_details);
```

```python
from openai import OpenAI

client = OpenAI()

prompt = """
Instructions:
- Given the React component below, change it so that nonfiction books have red
  text. 
- Return only the code in your reply
- Do not include any additional formatting, such as markdown code blocks
- For formatting, use four space tabs, and do not allow any lines of code to 
  exceed 80 columns

const books = [
  { title: 'Dune', category: 'fiction', id: 1 },
  { title: 'Frankenstein', category: 'fiction', id: 2 },
  { title: 'Moneyball', category: 'nonfiction', id: 3 },
];

export default function BookList() {
  const listItems = books.map(book =>
    <li>
      {book.title}
    </li>
  );

  return (
    <ul>{listItems}</ul>
  );
}
"""

response = client.chat.completions.create(
    model="o1-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
            ],
        }
    ]
)

print(response.choices[0].message.content)
```

Coding (planning)

OpenAI o1 series models are also adept in creating multi-step plans. This example prompt asks o1 to create a filesystem structure for a full solution, along with Python code that implements the desired use case.

Ask o1 models to plan and create a Python project

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const prompt = `
I want to build a Python app that takes user questions and looks 
them up in a database where they are mapped to answers. If there 
is close match, it retrieves the matched answer. If there isn't, 
it asks the user to provide an answer and stores the 
question/answer pair in the database. Make a plan for the directory 
structure you'll need, then return each file in full. Only supply 
your reasoning at the beginning and end, not throughout the code.
`.trim();

const completion = await openai.chat.completions.create({
  model: "o1-mini",
  messages: [
    {
      role: "user",
      content: prompt,
    },
  ]
});

console.log(completion.usage.completion_tokens_details);
```

```python
from openai import OpenAI

client = OpenAI()

prompt = """
I want to build a Python app that takes user questions and looks 
them up in a database where they are mapped to answers. If there 
is close match, it retrieves the matched answer. If there isn't, 
it asks the user to provide an answer and stores the 
question/answer pair in the database. Make a plan for the directory 
structure you'll need, then return each file in full. Only supply 
your reasoning at the beginning and end, not throughout the code.
"""

response = client.chat.completions.create(
    model="o1-preview",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
            ],
        }
    ]
)

print(response.choices[0].message.content)
```

STEM Research

OpenAI o1 series models have shown excellent performance in STEM research. Prompts asking for support of basic research tasks should show strong results.

Ask o1 models questions related to basic scientific research

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const prompt = `
What are three compounds we should consider investigating to 
advance research into new antibiotics? Why should we consider 
them?
`;
 
const completion = await openai.chat.completions.create({
  model: "o1",
  messages: [
    {
      role: "user", 
      content: prompt,
    }
  ]
});

console.log(completion.choices[0].message.content);
```

```python
from openai import OpenAI
client = OpenAI()

prompt = """
What are three compounds we should consider investigating to 
advance research into new antibiotics? Why should we consider 
them?
"""

response = client.chat.completions.create(
    model="o1",
    messages=[
        {
            "role": "user", 
            "content": prompt
        }
    ]
)

print(response.choices[0].message.content)
```

Limitations
-----------

The o1 models are among the newest models from OpenAI, and as such have a few limitations to be aware of:

*   Current `o1` models
    *   Available to [Tier 5 customers only](/docs/guides/rate-limits#usage-tiers)
    *   Streaming support not available in the REST API
    *   Parallel tool calls not yet supported
    *   Not available in the Batch API
    *   Currently unsupported API parameters: `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`, `logprobs`, `top_logprobs`, `logit_bias`

Use case examples
-----------------

Some examples of using o1 for real-world use cases can be found in [the cookbook](https://cookbook.openai.com).

[](https://cookbook.openai.com/examples/o1/using_reasoning_for_data_validation)

[](https://cookbook.openai.com/examples/o1/using_reasoning_for_data_validation)

[Using reasoning for data validation](https://cookbook.openai.com/examples/o1/using_reasoning_for_data_validation)

[](https://cookbook.openai.com/examples/o1/using_reasoning_for_data_validation)

[Evaluate a synthetic medical data set for discrepancies.](https://cookbook.openai.com/examples/o1/using_reasoning_for_data_validation)

[](https://cookbook.openai.com/examples/o1/using_reasoning_for_routine_generation)

[](https://cookbook.openai.com/examples/o1/using_reasoning_for_routine_generation)

[Using reasoning for routine generation](https://cookbook.openai.com/examples/o1/using_reasoning_for_routine_generation)

[](https://cookbook.openai.com/examples/o1/using_reasoning_for_routine_generation)

[Use help center articles to generate actions that an agent could perform.](https://cookbook.openai.com/examples/o1/using_reasoning_for_routine_generation)