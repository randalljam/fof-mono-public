const DEFAULT_ENDPOINTS = {
  hmacHash: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/generate-hash',
  sendEmail: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/send-email',
  hashStore: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/hash-store',
  qragRouting: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/qrag-routing',
  qragLlm: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/qrag-llm',
  vragLlm: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/vrag-llm',
};

function readEnv(name, fallback) {
  return import.meta.env?.[name] || fallback;
}

export const API_ENDPOINTS = {
  hmacHash: readEnv('PUBLIC_HMAC_HASH_API_URL', DEFAULT_ENDPOINTS.hmacHash),
  sendEmail: readEnv('PUBLIC_SEND_EMAIL_API_URL', DEFAULT_ENDPOINTS.sendEmail),
  hashStore: readEnv('PUBLIC_HASH_STORE_API_URL', DEFAULT_ENDPOINTS.hashStore),
  qragRouting: readEnv('PUBLIC_QRAG_ROUTING_API_URL', DEFAULT_ENDPOINTS.qragRouting),
  qragLlm: readEnv('PUBLIC_QRAG_LLM_API_URL', DEFAULT_ENDPOINTS.qragLlm),
  vragLlm: readEnv('PUBLIC_VRAG_LLM_API_URL', DEFAULT_ENDPOINTS.vragLlm),
};
