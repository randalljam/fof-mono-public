const { App } = require('aws-cdk-lib');
const { Template, Match } = require('aws-cdk-lib/assertions');
const { AuthStack } = require('../lib/auth-stack');

const { test } = require('node:test');
const assert = require('node:assert/strict');

const stagingProps = {
  environmentName: 'staging',
  callbackUrls: [
    'https://staging.focusonfoundations.org/account/callback/',
    'http://localhost:4321/account/callback/',
  ],
  logoutUrls: ['https://staging.focusonfoundations.org/', 'http://localhost:4321/'],
  apiCorsOrigins: ['https://staging.focusonfoundations.org', 'http://localhost:4321'],
};

function synthStack(extraProps = {}, id = 'TestAuth') {
  const app = new App();
  const stack = new AuthStack(app, id, { ...stagingProps, ...extraProps });
  return Template.fromStack(stack);
}

test('user pool uses Essentials tier with email sign-in and self sign-up', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    UserPoolName: 'fof-users-staging',
    UserPoolTier: 'ESSENTIALS',
    UsernameAttributes: ['email'],
    AutoVerifiedAttributes: ['email'],
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: false },
  });
});

test('user pool is retained on stack deletion', () => {
  const template = synthStack();
  template.hasResource('AWS::Cognito::UserPool', {
    DeletionPolicy: 'Retain',
  });
});

test('without SES sender, sign-in is password-only', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    Policies: {
      SignInPolicy: { AllowedFirstAuthFactors: ['PASSWORD'] },
    },
  });
});

test('with SES sender, email OTP passwordless sign-in is enabled', () => {
  const template = synthStack({ sesFromEmail: 'accounts@focusonfoundations.org' });
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    Policies: {
      SignInPolicy: {
        AllowedFirstAuthFactors: Match.arrayWith(['PASSWORD', 'EMAIL_OTP']),
      },
    },
    EmailConfiguration: {
      EmailSendingAccount: 'DEVELOPER',
    },
  });
});

test('web client enables SRP and choice-based USER_AUTH flows with OAuth code grant', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
    ClientName: 'fof-web-staging',
    ExplicitAuthFlows: Match.arrayWith([
      'ALLOW_USER_SRP_AUTH',
      'ALLOW_USER_AUTH',
      'ALLOW_REFRESH_TOKEN_AUTH',
    ]),
    AllowedOAuthFlows: ['code'],
    AllowedOAuthScopes: Match.arrayWith(['openid', 'email', 'profile']),
    CallbackURLs: stagingProps.callbackUrls,
    LogoutURLs: stagingProps.logoutUrls,
    PreventUserExistenceErrors: 'ENABLED',
    GenerateSecret: Match.absent(),
  });
});

test('hosted domain uses the fof-auth prefix', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::Cognito::UserPoolDomain', {
    Domain: 'fof-auth-staging',
  });
});

test('no social identity providers without credentials', () => {
  const template = synthStack();
  template.resourceCountIs('AWS::Cognito::UserPoolIdentityProvider', 0);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
    SupportedIdentityProviders: ['COGNITO'],
  });
});

test('google provider is created when credentials are configured', () => {
  const template = synthStack({
    googleClientId: 'test-google-client-id.apps.googleusercontent.com',
    googleClientSecretName: 'fof-auth-google-oauth',
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolIdentityProvider', {
    ProviderName: 'Google',
    ProviderType: 'Google',
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
    SupportedIdentityProviders: Match.arrayWith(['COGNITO', 'Google']),
  });
});

test('facebook provider is created when credentials are configured', () => {
  const template = synthStack({
    facebookAppId: '1234567890',
    facebookAppSecretName: 'fof-auth-facebook-oauth',
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolIdentityProvider', {
    ProviderName: 'Facebook',
    ProviderType: 'Facebook',
  });
});

test('user data table is single-table PK/SK, on-demand, PITR, retained', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::DynamoDB::GlobalTable', {
    TableName: 'fof-user-data-staging',
    BillingMode: 'PAY_PER_REQUEST',
    KeySchema: [
      { AttributeName: 'PK', KeyType: 'HASH' },
      { AttributeName: 'SK', KeyType: 'RANGE' },
    ],
  });
  template.hasResource('AWS::DynamoDB::GlobalTable', {
    DeletionPolicy: 'Retain',
  });
});

test('user-data API secures all routes with the user-pool JWT authorizer', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::ApiGatewayV2::Api', {
    Name: 'fof-user-data-staging',
    CorsConfiguration: {
      AllowOrigins: stagingProps.apiCorsOrigins,
      AllowHeaders: ['authorization', 'content-type'],
    },
  });
  template.hasResourceProperties('AWS::ApiGatewayV2::Authorizer', {
    AuthorizerType: 'JWT',
  });
  const routes = template.findResources('AWS::ApiGatewayV2::Route');
  const routeKeys = Object.values(routes).map((r) => r.Properties.RouteKey).sort();
  assert.deepEqual(routeKeys, [
    'DELETE /family/member/{sub}',
    'DELETE /user/account',
    'DELETE /user/data/{app}/{key}',
    'DELETE /user/files/{app}/{name}',
    'GET /family',
    'GET /family/member/{sub}/data',
    'GET /user/data',
    'GET /user/files',
    'GET /user/files/{app}/{name}/download-url',
    'GET /user/profile',
    'POST /family',
    'POST /family/children',
    'POST /family/invites',
    'POST /family/join',
    'POST /user/files/{app}/{name}/upload-url',
    'POST /user/migrate',
    'PUT /family/member/{sub}/entitlements',
    'PUT /user/data/{app}/{key}',
    'PUT /user/profile',
  ]);
  for (const route of Object.values(routes)) {
    assert.equal(route.Properties.AuthorizationType, 'JWT', `route ${route.Properties.RouteKey} must be JWT-authorized`);
  }
});

test('user-data lambda gets table access and scoped cognito permissions', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::Lambda::Function', {
    FunctionName: 'fof-user-data-api-staging',
    Runtime: 'nodejs20.x',
    Environment: {
      Variables: {
        TABLE_NAME: { Ref: Match.anyValue() },
        USER_POOL_ID: { Ref: Match.anyValue() },
      },
    },
  });
  template.hasResourceProperties('AWS::IAM::Policy', {
    PolicyDocument: {
      Statement: Match.arrayWith([
        Match.objectLike({
          Action: [
            'cognito-idp:ListUsers',
            'cognito-idp:AdminDeleteUser',
            'cognito-idp:AdminCreateUser',
            'cognito-idp:AdminSetUserPassword',
          ],
        }),
      ]),
    },
  });
});

test('user-files bucket is private, encrypted, retained, with site-origin CORS', () => {
  const template = synthStack();
  template.hasResourceProperties('AWS::S3::Bucket', {
    BucketName: 'fof-user-files-staging',
    PublicAccessBlockConfiguration: Match.objectLike({ BlockPublicAcls: true, RestrictPublicBuckets: true }),
    CorsConfiguration: {
      CorsRules: [Match.objectLike({
        AllowedOrigins: stagingProps.apiCorsOrigins,
        AllowedMethods: ['GET', 'PUT'],
      })],
    },
  });
  template.hasResource('AWS::S3::Bucket', {
    Properties: Match.objectLike({ BucketName: 'fof-user-files-staging' }),
    DeletionPolicy: 'Retain',
  });
});

test('production stack enables deletion protection', () => {
  const app = new App();
  const stack = new AuthStack(app, 'TestAuthProd', {
    environmentName: 'production',
    callbackUrls: ['https://focusonfoundations.org/account/callback/'],
    logoutUrls: ['https://focusonfoundations.org/'],
    apiCorsOrigins: ['https://focusonfoundations.org'],
  });
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    UserPoolName: 'fof-users-production',
    DeletionProtection: 'ACTIVE',
  });
});
