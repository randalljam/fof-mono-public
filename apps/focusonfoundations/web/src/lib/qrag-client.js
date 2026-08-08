import { API_ENDPOINTS } from './api-endpoints.js';
import { getAuthHeaders } from './validation.js';

const MAX_QRAG_LLM_RETRIES = 3;

export function qragRouting(userInput, vector_index_name, route_dict_name, numChunksValue, userEmailHmacHash, userContext) {
  if (!userInput || userInput.trim() === '') {
    return Promise.reject(new Error('Empty input submitted'));
  }

  const startDate = sessionStorage.getItem('qrag-start-date');
  const endDate = sessionStorage.getItem('qrag-end-date');

  if ((startDate && !endDate) || (!startDate && endDate)) {
    return Promise.reject(new Error('Invalid date range: both start and end dates must be provided together'));
  }

  const requestBody = {
    user_question: userInput,
    vector_index_name,
    num_chunks: numChunksValue,
    route_dict_name,
    user_id: userEmailHmacHash,
    ...userContext,
  };

  if (startDate && endDate) {
    requestBody.start_date = startDate;
    requestBody.end_date = endDate;
  }

  return fetch(API_ENDPOINTS.qragRouting, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(requestBody),
  })
    .then((httpResponse) => {
      if (!httpResponse.ok) {
        return httpResponse.json()
          .catch(() => null)
          .then((errorData) => {
            const apiErrorDetail = errorData && errorData.error ? `: ${errorData.error}` : '';
            throw new Error(`qrag-routing - API Error (${httpResponse.status}): ${httpResponse.statusText}${apiErrorDetail}`);
          });
      }
      return httpResponse.json();
    })
    .then((apiResponse) => {
      if (!apiResponse.response) {
        throw new Error('qrag-routing - No data in API Response');
      }
      return apiResponse.response;
    })
    .catch((error) => {
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        throw new Error('NETWORK_CHANGED_OR_UNREACHABLE');
      }
      throw error;
    });
}

export function qragLLM(routingJsonData, large_context_filename, onRetryMessage) {
  if (!routingJsonData.metadata) {
    routingJsonData.metadata = {};
  }
  if (routingJsonData.metadata.retry_count === undefined) {
    routingJsonData.metadata.retry_count = 0;
  }
  routingJsonData.metadata.is_retry = routingJsonData.metadata.retry_count > 0;

  if (routingJsonData.metadata.retry_count > MAX_QRAG_LLM_RETRIES) {
    const timeoutMessage = `Sorry, the AI models failed to respond after ${MAX_QRAG_LLM_RETRIES + 1} attempts. We've been notified about this issue and will look into it. If you want to try again, copy your question, refresh the webpage, and paste your question back in.`;
    routingJsonData.content.ai_answer = timeoutMessage;
    return Promise.resolve({
      status: 'Error',
      message: timeoutMessage,
      response: routingJsonData,
    });
  }

  if (large_context_filename) {
    routingJsonData.metadata.large_context_filename = large_context_filename;
  }

  return fetch(API_ENDPOINTS.qragLlm, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(routingJsonData),
  })
    .then((httpResponse) => {
      if (!httpResponse.ok) {
        return httpResponse.json().then((errorData) => {
          if (errorData.error_type === 'LargeContextLoadError') {
            throw new Error(`Failed to load context data: ${errorData.error}`);
          }
          throw new Error(`HTTP error! status: ${httpResponse.status}, message: ${errorData.error}`);
        });
      }
      return httpResponse.json();
    })
    .then((apiResponse) => {
      if (!apiResponse.response) {
        throw new Error('qrag-llm - No data in API Response');
      }
      if (apiResponse.status === 'Retry') {
        if (onRetryMessage) {
          onRetryMessage(apiResponse.response);
        }
        routingJsonData.metadata.retry_count += 1;
        return qragLLM(routingJsonData, large_context_filename, onRetryMessage);
      }
      return apiResponse.response;
    });
}

export function vragLLM(userInput, vector_index_name) {
  return fetch(API_ENDPOINTS.vragLlm, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      user_question: userInput,
      vector_index_name,
    }),
  })
    .then((httpResponse) => {
      if (!httpResponse.ok) {
        throw new Error(`vrag-routing - HTTP error! status: ${httpResponse.status}`);
      }
      return httpResponse.json();
    })
    .then((apiResponse) => {
      if (!apiResponse.response) {
        throw new Error('vrag-routing - No data in API Response');
      }
      return apiResponse.response;
    });
}

export const ragFunctions = {
  qragRouting,
  qragLLM,
  vragLLM,
};
