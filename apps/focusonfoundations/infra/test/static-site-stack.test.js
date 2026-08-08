const { App } = require('aws-cdk-lib');
const { Template } = require('aws-cdk-lib/assertions');
const { StaticSiteStack } = require('../lib/static-site-stack');

const testCertArn = 'arn:aws:acm:us-east-1:[AWS-ACCOUNT-ID]:certificate/4582158a-ecb4-4902-b32c-4434c1bf4deb';

function synthExternalDomainStack() {
  const app = new App();
  const stack = new StaticSiteStack(app, 'TestStagingExternalDns', {
    environmentName: 'staging',
    domainNames: ['staging.focusonfoundations.org'],
    certificateArn: testCertArn,
  });
  return Template.fromStack(stack);
}

const { test } = require('node:test');
const assert = require('node:assert/strict');

test('external cert mode attaches staging alias to CloudFront', () => {
  const template = synthExternalDomainStack();
  template.hasResourceProperties('AWS::CloudFront::Distribution', {
    DistributionConfig: {
      Aliases: ['staging.focusonfoundations.org'],
      ViewerCertificate: {
        AcmCertificateArn: testCertArn,
        SslSupportMethod: 'sni-only',
      },
    },
  });
});

test('external cert mode does not create Route 53 records', () => {
  const template = synthExternalDomainStack();
  template.resourceCountIs('AWS::Route53::RecordSet', 0);
});

const prodTestCertArn = 'arn:aws:acm:us-east-1:[AWS-ACCOUNT-ID]:certificate/ce92bf3f-2f1d-4bdc-814e-2533499cca13';

function synthProductionExternalDomainStack() {
  const app = new App();
  const stack = new StaticSiteStack(app, 'TestProductionExternalDns', {
    environmentName: 'production',
    domainNames: ['focusonfoundations.org', 'www.focusonfoundations.org'],
    createDnsRecords: false,
    certificateArn: prodTestCertArn,
  });
  return Template.fromStack(stack);
}

test('production external cert mode attaches apex and www aliases', () => {
  const template = synthProductionExternalDomainStack();
  template.hasResourceProperties('AWS::CloudFront::Distribution', {
    DistributionConfig: {
      Aliases: ['focusonfoundations.org', 'www.focusonfoundations.org'],
      ViewerCertificate: {
        AcmCertificateArn: prodTestCertArn,
        SslSupportMethod: 'sni-only',
      },
    },
  });
});

test('production external cert mode does not create Route 53 records', () => {
  const template = synthProductionExternalDomainStack();
  template.resourceCountIs('AWS::Route53::RecordSet', 0);
});
