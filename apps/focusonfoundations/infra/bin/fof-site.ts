#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { StaticSiteStack } from '../lib/static-site-stack';
import { AuthStack } from '../lib/auth-stack';

const app = new cdk.App();

const env = process.env.CDK_DEFAULT_ACCOUNT
  ? {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: 'us-east-1',
    }
  : undefined;

const hostedZoneId = app.node.tryGetContext('hostedZoneId');
const hostedZoneName = app.node.tryGetContext('hostedZoneName') || 'focusonfoundations.org';
const stagingCertArn = app.node.tryGetContext('stagingCertArn');
const prodCertArn = app.node.tryGetContext('prodCertArn');

new StaticSiteStack(app, 'FofSiteStaging', {
  env,
  environmentName: 'staging',
  domainNames: ['staging.focusonfoundations.org'],
  hostedZoneId,
  hostedZoneName,
  createDnsRecords: Boolean(hostedZoneId),
  certificateArn: stagingCertArn,
  description: 'Focus on Foundations staging static site (S3 + CloudFront)',
});

new StaticSiteStack(app, 'FofSiteProduction', {
  env,
  environmentName: 'production',
  domainNames: ['focusonfoundations.org', 'www.focusonfoundations.org'],
  hostedZoneId,
  hostedZoneName,
  createDnsRecords: false,
  certificateArn: prodCertArn,
  description: 'Focus on Foundations production static site (S3 + CloudFront)',
});

// Auth stacks live in us-west-2 with the rest of the Lambda/API/data infrastructure
// (the site stacks are us-east-1 only because CloudFront requires us-east-1 ACM certs).
const authEnv = process.env.CDK_DEFAULT_ACCOUNT
  ? {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: 'us-west-2',
    }
  : undefined;

// One Google/Facebook developer app can serve both environments (each allows
// multiple redirect URIs), so the credential context keys are shared.
const sesFromEmail = app.node.tryGetContext('authSesFromEmail');
const googleClientId = app.node.tryGetContext('authGoogleClientId');
const googleClientSecretName = app.node.tryGetContext('authGoogleClientSecretName');
const facebookAppId = app.node.tryGetContext('authFacebookAppId');
const facebookAppSecretName = app.node.tryGetContext('authFacebookAppSecretName');

new AuthStack(app, 'FofAuthStaging', {
  env: authEnv,
  environmentName: 'staging',
  callbackUrls: [
    'https://staging.focusonfoundations.org/account/callback/',
    'http://localhost:4321/account/callback/',
  ],
  logoutUrls: [
    'https://staging.focusonfoundations.org/',
    'http://localhost:4321/',
  ],
  apiCorsOrigins: [
    'https://staging.focusonfoundations.org',
    'http://localhost:4321',
  ],
  siteBaseUrl: 'https://staging.focusonfoundations.org',
  sesFromEmail,
  googleClientId,
  googleClientSecretName,
  facebookAppId,
  facebookAppSecretName,
  description: 'Focus on Foundations staging auth (Cognito user pool + user-data DynamoDB)',
});

new AuthStack(app, 'FofAuthProduction', {
  env: authEnv,
  environmentName: 'production',
  callbackUrls: [
    'https://focusonfoundations.org/account/callback/',
    'https://www.focusonfoundations.org/account/callback/',
  ],
  logoutUrls: [
    'https://focusonfoundations.org/',
    'https://www.focusonfoundations.org/',
  ],
  apiCorsOrigins: [
    'https://focusonfoundations.org',
    'https://www.focusonfoundations.org',
  ],
  siteBaseUrl: 'https://focusonfoundations.org',
  sesFromEmail,
  googleClientId,
  googleClientSecretName,
  facebookAppId,
  facebookAppSecretName,
  description: 'Focus on Foundations production auth (Cognito user pool + user-data DynamoDB)',
});
