// Cognito configuration for site accounts (FofAuthStaging / FofAuthProduction).
// The site ships one static build to both environments, so the environment is
// chosen by hostname at runtime: production domains use the production pool,
// everything else (staging domain, localhost dev/preview) uses staging.
// PUBLIC_* env vars override the selected defaults, same pattern as
// api-endpoints.js. PENDING_DEPLOY placeholders keep isAuthConfigured() false
// (account pages show a "not live yet" notice) until that pool is deployed
// and its stack outputs are recorded here.
const PLACEHOLDER = 'PENDING_DEPLOY';

const DEFAULT_AUTH_BY_ENV = {
  staging: {
    // FofAuthStaging outputs, deployed 2026-07-17
    userPoolId: 'us-west-2_U25uiNhpb',
    userPoolClientId: '1umi8t3jeq2la5mfnigg8gjj3b',
    oauthDomain: 'fof-auth-staging.auth.us-west-2.amazoncognito.com',
    userDataApiUrl: 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com',
    socialProviders: '',
  },
  production: {
    // FofAuthProduction is not deployed yet
    userPoolId: PLACEHOLDER,
    userPoolClientId: PLACEHOLDER,
    oauthDomain: PLACEHOLDER,
    userDataApiUrl: PLACEHOLDER,
    socialProviders: '',
  },
};

const PRODUCTION_HOSTNAMES = ['focusonfoundations.org', 'www.focusonfoundations.org'];

export function selectAuthEnv(hostname) {
  return PRODUCTION_HOSTNAMES.includes(hostname) ? 'production' : 'staging';
}

function readEnv(name, fallback) {
  return import.meta.env?.[name] || fallback;
}

const activeEnv = selectAuthEnv(typeof window !== 'undefined' ? window.location.hostname : '');
const defaults = DEFAULT_AUTH_BY_ENV[activeEnv];

export const AUTH_CONFIG = {
  authEnv: activeEnv,
  userPoolId: readEnv('PUBLIC_AUTH_USER_POOL_ID', defaults.userPoolId),
  userPoolClientId: readEnv('PUBLIC_AUTH_USER_POOL_CLIENT_ID', defaults.userPoolClientId),
  oauthDomain: readEnv('PUBLIC_AUTH_OAUTH_DOMAIN', defaults.oauthDomain),
  userDataApiUrl: readEnv('PUBLIC_AUTH_USER_DATA_API_URL', defaults.userDataApiUrl),
  socialProviders: parseProviders(
    readEnv('PUBLIC_AUTH_SOCIAL_PROVIDERS', defaults.socialProviders)
  ),
};

export function parseProviders(value) {
  return String(value || '')
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean);
}

export function isAuthConfigured(config = AUTH_CONFIG) {
  return (
    Boolean(config.userPoolId && config.userPoolClientId) &&
    config.userPoolId !== PLACEHOLDER &&
    config.userPoolClientId !== PLACEHOLDER
  );
}
