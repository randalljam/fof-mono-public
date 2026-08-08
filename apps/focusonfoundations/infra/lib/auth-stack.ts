import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpUserPoolAuthorizer } from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface AuthStackProps extends cdk.StackProps {
  environmentName: 'staging' | 'production';
  /** Exact allowed OAuth redirect URIs, e.g. https://staging.focusonfoundations.org/account/callback/ */
  callbackUrls: string[];
  /** Exact allowed post-signout URIs. */
  logoutUrls: string[];
  /** Browser origins allowed to call the user-data API (CORS). */
  apiCorsOrigins: string[];
  /** Public site base URL for links in emails (family invites), e.g. https://staging.focusonfoundations.org */
  siteBaseUrl: string;
  /**
   * SES-verified sender for account emails (verification codes, OTP sign-in, resets).
   * Required for email-OTP passwordless sign-in — Cognito's built-in mailer does not
   * support OTP-as-first-factor. Without it the pool falls back to the Cognito default
   * mailer and password-only sign-in.
   */
  sesFromEmail?: string;
  /** Google OAuth client id; provider is created only when both id and secret name are set. */
  googleClientId?: string;
  /** Secrets Manager secret name whose value (field `clientSecret`) is the Google OAuth client secret. */
  googleClientSecretName?: string;
  /** Facebook app id; provider is created only when both id and secret name are set. */
  facebookAppId?: string;
  /** Secrets Manager secret name whose value (field `clientSecret`) is the Facebook app secret. */
  facebookAppSecretName?: string;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly userDataTable: dynamodb.TableV2;
  public userFilesBucket: s3.Bucket;
  public httpApi: apigwv2.HttpApi;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    const envLabel = props.environmentName;
    const emailOtpEnabled = Boolean(props.sesFromEmail);

    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `fof-users-${envLabel}`,
      featurePlan: cognito.FeaturePlan.ESSENTIALS,
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      signInCaseSensitive: false,
      autoVerify: { email: true },
      keepOriginal: { email: true },
      standardAttributes: {
        email: { required: true, mutable: true },
      },
      signInPolicy: {
        allowedFirstAuthFactors: {
          password: true,
          emailOtp: emailOtpEnabled,
        },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      mfa: cognito.Mfa.OPTIONAL,
      // Email is deliberately NOT an MFA second factor: with EMAIL_ONLY account
      // recovery Cognito rejects it (same-channel recovery would defeat MFA).
      // Email OTP as a passwordless FIRST factor (signInPolicy above) is separate.
      mfaSecondFactor: { sms: false, otp: true },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      email: props.sesFromEmail
        ? cognito.UserPoolEmail.withSES({
            fromEmail: props.sesFromEmail,
            fromName: 'Focus on Foundations',
            sesRegion: 'us-west-2',
            // The SES-verified identity is the domain, not each individual address.
            sesVerifiedDomain: props.sesFromEmail.split('@')[1],
          })
        : cognito.UserPoolEmail.withCognito(),
      userVerification: {
        emailSubject: 'Your Focus on Foundations verification code',
        emailBody: 'Your Focus on Foundations verification code is {####}.',
        emailStyle: cognito.VerificationEmailStyle.CODE,
      },
      deletionProtection: envLabel === 'production',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.userPoolDomain = this.userPool.addDomain('AuthDomain', {
      cognitoDomain: {
        domainPrefix: `fof-auth-${envLabel}`,
      },
    });

    const identityProviders: cognito.UserPoolClientIdentityProvider[] = [
      cognito.UserPoolClientIdentityProvider.COGNITO,
    ];
    const providerConstructs: cdk.IResource[] = [];

    if (props.googleClientId && props.googleClientSecretName) {
      const google = new cognito.UserPoolIdentityProviderGoogle(this, 'GoogleIdP', {
        userPool: this.userPool,
        clientId: props.googleClientId,
        clientSecretValue: cdk.SecretValue.secretsManager(props.googleClientSecretName, {
          jsonField: 'clientSecret',
        }),
        scopes: ['openid', 'email', 'profile'],
        attributeMapping: {
          email: cognito.ProviderAttribute.GOOGLE_EMAIL,
          fullname: cognito.ProviderAttribute.GOOGLE_NAME,
        },
      });
      identityProviders.push(cognito.UserPoolClientIdentityProvider.GOOGLE);
      providerConstructs.push(google);
    }

    if (props.facebookAppId && props.facebookAppSecretName) {
      const facebook = new cognito.UserPoolIdentityProviderFacebook(this, 'FacebookIdP', {
        userPool: this.userPool,
        clientId: props.facebookAppId,
        clientSecret: cdk.SecretValue.secretsManager(props.facebookAppSecretName, {
          jsonField: 'clientSecret',
        }).unsafeUnwrap(),
        scopes: ['public_profile', 'email'],
        attributeMapping: {
          email: cognito.ProviderAttribute.FACEBOOK_EMAIL,
          fullname: cognito.ProviderAttribute.FACEBOOK_NAME,
        },
      });
      identityProviders.push(cognito.UserPoolClientIdentityProvider.FACEBOOK);
      providerConstructs.push(facebook);
    }

    this.userPoolClient = this.userPool.addClient('WebClient', {
      userPoolClientName: `fof-web-${envLabel}`,
      authFlows: {
        userSrp: true,
        user: true,
      },
      preventUserExistenceErrors: true,
      supportedIdentityProviders: identityProviders,
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: props.callbackUrls,
        logoutUrls: props.logoutUrls,
      },
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
    });
    for (const provider of providerConstructs) {
      this.userPoolClient.node.addDependency(provider);
    }

    this.userDataTable = new dynamodb.TableV2(this, 'UserDataTable', {
      tableName: `fof-user-data-${envLabel}`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billing: dynamodb.Billing.onDemand(),
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Per-user file storage (e.g. education-app SQLite databases) — objects live
    // under user-files/<sub>/<app>/<name>; the browser reaches them only through
    // short-lived presigned URLs issued by the user-data lambda, so bucket CORS
    // must allow direct PUT/GET from the site origins.
    this.userFilesBucket = new s3.Bucket(this, 'UserFilesBucket', {
      bucketName: `fof-user-files-${envLabel}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      cors: [{
        allowedOrigins: props.apiCorsOrigins,
        allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT],
        allowedHeaders: ['content-type'],
        exposedHeaders: ['ETag'],
        maxAge: 3600,
      }],
    });

    const userDataFn = new lambda.Function(this, 'UserDataFn', {
      functionName: `fof-user-data-api-${envLabel}`,
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'user-data')),
      memorySize: 256,
      timeout: cdk.Duration.seconds(10),
      environment: {
        TABLE_NAME: this.userDataTable.tableName,
        USER_POOL_ID: this.userPool.userPoolId,
        FILES_BUCKET: this.userFilesBucket.bucketName,
        SITE_BASE_URL: props.siteBaseUrl,
        SES_FROM_EMAIL: props.sesFromEmail || '',
      },
    });
    if (props.sesFromEmail) {
      // Family-invite emails, sent from the same SES-verified domain as the
      // Cognito account emails.
      userDataFn.addToRolePolicy(new iam.PolicyStatement({
        actions: ['ses:SendEmail'],
        resources: [
          `arn:aws:ses:us-west-2:${this.account}:identity/${props.sesFromEmail.split('@')[1]}`,
        ],
      }));
    }
    this.userDataTable.grantReadWriteData(userDataFn);
    this.userFilesBucket.grantReadWrite(userDataFn);
    userDataFn.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'cognito-idp:ListUsers',
        'cognito-idp:AdminDeleteUser',
        // Guardian-created child accounts (COPPA flow) — created with a
        // guardian-supplied email + permanent password, no invite email.
        'cognito-idp:AdminCreateUser',
        'cognito-idp:AdminSetUserPassword',
      ],
      resources: [this.userPool.userPoolArn],
    }));

    const authorizer = new HttpUserPoolAuthorizer('UserPoolAuthorizer', this.userPool, {
      userPoolClients: [this.userPoolClient],
    });
    const integration = new HttpLambdaIntegration('UserDataIntegration', userDataFn);
    this.httpApi = new apigwv2.HttpApi(this, 'UserDataApi', {
      apiName: `fof-user-data-${envLabel}`,
      corsPreflight: {
        allowOrigins: props.apiCorsOrigins,
        allowMethods: [
          apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.PUT,
          apigwv2.CorsHttpMethod.POST,
          apigwv2.CorsHttpMethod.DELETE,
        ],
        allowHeaders: ['authorization', 'content-type'],
        maxAge: cdk.Duration.hours(1),
      },
      defaultAuthorizer: authorizer,
    });
    const routes: Array<[apigwv2.HttpMethod, string]> = [
      [apigwv2.HttpMethod.GET, '/user/data'],
      [apigwv2.HttpMethod.PUT, '/user/data/{app}/{key}'],
      [apigwv2.HttpMethod.DELETE, '/user/data/{app}/{key}'],
      [apigwv2.HttpMethod.POST, '/user/migrate'],
      [apigwv2.HttpMethod.DELETE, '/user/account'],
      [apigwv2.HttpMethod.GET, '/user/files'],
      [apigwv2.HttpMethod.POST, '/user/files/{app}/{name}/upload-url'],
      [apigwv2.HttpMethod.GET, '/user/files/{app}/{name}/download-url'],
      [apigwv2.HttpMethod.DELETE, '/user/files/{app}/{name}'],
      [apigwv2.HttpMethod.GET, '/user/profile'],
      [apigwv2.HttpMethod.PUT, '/user/profile'],
      [apigwv2.HttpMethod.POST, '/family'],
      [apigwv2.HttpMethod.GET, '/family'],
      [apigwv2.HttpMethod.POST, '/family/invites'],
      [apigwv2.HttpMethod.POST, '/family/join'],
      [apigwv2.HttpMethod.POST, '/family/children'],
      [apigwv2.HttpMethod.GET, '/family/member/{sub}/data'],
      [apigwv2.HttpMethod.PUT, '/family/member/{sub}/entitlements'],
      [apigwv2.HttpMethod.DELETE, '/family/member/{sub}'],
    ];
    for (const [method, routePath] of routes) {
      this.httpApi.addRoutes({ path: routePath, methods: [method], integration, authorizer });
    }

    new cdk.CfnOutput(this, 'UserDataApiUrl', {
      value: this.httpApi.apiEndpoint,
      exportName: `fof-auth-${envLabel}-user-data-api-url`,
    });
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      exportName: `fof-auth-${envLabel}-user-pool-id`,
    });
    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      exportName: `fof-auth-${envLabel}-web-client-id`,
    });
    new cdk.CfnOutput(this, 'AuthDomain', {
      value: `${this.userPoolDomain.domainName}.auth.${this.region}.amazoncognito.com`,
      exportName: `fof-auth-${envLabel}-domain`,
    });
    new cdk.CfnOutput(this, 'UserDataTableName', {
      value: this.userDataTable.tableName,
      exportName: `fof-auth-${envLabel}-user-data-table`,
    });
    new cdk.CfnOutput(this, 'UserFilesBucketName', {
      value: this.userFilesBucket.bucketName,
      exportName: `fof-auth-${envLabel}-user-files-bucket`,
    });
    new cdk.CfnOutput(this, 'EmailOtpEnabled', {
      value: String(emailOtpEnabled),
    });
    new cdk.CfnOutput(this, 'SocialProviders', {
      value: identityProviders
        .map((p) => p.name)
        .filter((n) => n !== 'COGNITO')
        .join(', ') || 'none',
    });
  }
}
