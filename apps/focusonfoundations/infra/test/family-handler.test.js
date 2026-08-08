const { test } = require('node:test');
const assert = require('node:assert/strict');

const TABLE = 'test-table';
const POOL = 'us-west-2_TESTPOOL';
const BUCKET = 'test-user-files';

function makeWorld() {
  const store = new Map();
  const cognitoUsers = new Map(); // email -> {sub, username}
  let subCounter = 0;
  const docClient = {
    async send(cmd) {
      const name = cmd.constructor.name;
      const input = cmd.input;
      if (name === 'PutCommand') { store.set(`${input.Item.PK}|${input.Item.SK}`, input.Item); return {}; }
      if (name === 'GetCommand') {
        const item = store.get(`${input.Key.PK}|${input.Key.SK}`);
        return item ? { Item: item } : {};
      }
      if (name === 'DeleteCommand') { store.delete(`${input.Key.PK}|${input.Key.SK}`); return {}; }
      if (name === 'QueryCommand') {
        const pk = input.ExpressionAttributeValues[':pk'];
        const skPrefix = input.ExpressionAttributeValues[':sk'];
        // Mirror real DynamoDB: empty key attribute values are invalid (this
        // masked a live 500 once — keep the fake strict).
        if (skPrefix === '' || pk === '') {
          const err = new Error('The AttributeValue for a key attribute cannot contain an empty string value');
          err.name = 'ValidationException';
          throw err;
        }
        return { Items: [...store.values()].filter((i) => i.PK === pk && (!skPrefix || i.SK.startsWith(skPrefix))) };
      }
      if (name === 'BatchWriteCommand') {
        for (const requests of Object.values(input.RequestItems)) {
          for (const req of requests) {
            if (req.PutRequest) store.set(`${req.PutRequest.Item.PK}|${req.PutRequest.Item.SK}`, req.PutRequest.Item);
            if (req.DeleteRequest) store.delete(`${req.DeleteRequest.Key.PK}|${req.DeleteRequest.Key.SK}`);
          }
        }
        return { UnprocessedItems: {} };
      }
      throw new Error(`Unexpected doc command: ${name}`);
    },
  };
  const cognitoClient = {
    async send(cmd) {
      const name = cmd.constructor.name;
      const input = cmd.input;
      if (name === 'AdminCreateUserCommand') {
        if (cognitoUsers.has(input.Username)) {
          const err = new Error('exists'); err.name = 'UsernameExistsException'; throw err;
        }
        subCounter += 1;
        const sub = `child-sub-${subCounter}`;
        cognitoUsers.set(input.Username, { sub, username: `uuid-${sub}` });
        return { User: { Username: `uuid-${sub}`, Attributes: [{ Name: 'sub', Value: sub }] } };
      }
      if (name === 'AdminSetUserPasswordCommand') return {};
      if (name === 'ListUsersCommand') {
        const match = [...cognitoUsers.values()].find((u) => cmd.input.Filter.includes(u.sub));
        return { Users: match ? [{ Username: match.username }] : [] };
      }
      if (name === 'AdminDeleteUserCommand') {
        for (const [email, u] of cognitoUsers.entries()) {
          if (u.username === input.Username) cognitoUsers.delete(email);
        }
        return {};
      }
      throw new Error(`Unexpected cognito command: ${name}`);
    },
  };
  const s3Client = {
    async send(cmd) {
      if (cmd.constructor.name === 'ListObjectVersionsCommand') return { Versions: [], DeleteMarkers: [], IsTruncated: false };
      if (cmd.constructor.name === 'ListObjectsV2Command') return { Contents: [], IsTruncated: false };
      if (cmd.constructor.name === 'DeleteObjectsCommand') return {};
      throw new Error(`Unexpected s3 command: ${cmd.constructor.name}`);
    },
  };
  const sentEmails = [];
  const sesClient = {
    async send(cmd) {
      if (cmd.constructor.name !== 'SendEmailCommand') throw new Error(`Unexpected ses command: ${cmd.constructor.name}`);
      sentEmails.push(cmd.input);
      return {};
    },
  };
  return { store, cognitoUsers, docClient, cognitoClient, s3Client, sesClient, sentEmails };
}

async function makeHandler() {
  const { buildHandler } = await import('../lambda/user-data/index.mjs');
  const world = makeWorld();
  const handler = buildHandler({
    ...world,
    filesBucket: BUCKET,
    presign: async () => 'https://signed.example.com/x',
    tableName: TABLE,
    userPoolId: POOL,
    sesFromEmail: 'accounts@focusonfoundations.org',
    siteBaseUrl: 'https://staging.focusonfoundations.org',
    now: () => '2026-07-18T00:00:00.000Z',
  });
  return { handler, ...world };
}

function event(routeKey, { sub = 'guardian-1', body, pathParameters, queryStringParameters } = {}) {
  return {
    routeKey,
    pathParameters,
    queryStringParameters,
    body: body === undefined ? undefined : JSON.stringify(body),
    requestContext: sub ? { authorizer: { jwt: { claims: { sub, email: `${sub}@example.com` } } } } : {},
  };
}
const parse = (r) => JSON.parse(r.body);

async function setupFamilyWithChild(handler) {
  await handler(event('POST /family', { body: { name: 'Trues' } }));
  const child = parse(await handler(event('POST /family/children', {
    body: {
      email: 'parent+kid1@example.com',
      displayName: 'Kid One',
      password: 'KidPass2026a',
      consent: { agreed: true },
    },
  })));
  return child; // {childSub, email, displayName}
}

test('create family: creator becomes guardian with family-scope entitlements', async () => {
  const { handler } = await makeHandler();
  const created = parse(await handler(event('POST /family', { body: { name: 'Trues' } })));
  assert.ok(created.familyId);
  const fam = parse(await handler(event('GET /family')));
  assert.equal(fam.family.yourRole, 'guardian');
  assert.equal(fam.family.name, 'Trues');
  assert.equal(fam.family.members.length, 1);
  const profile = parse(await handler(event('GET /user/profile'))).profile;
  assert.deepEqual(profile.entitlements['*'], { analysis: true, analysisScope: 'family' });
});

test('child creation requires explicit guardian consent and records it', async () => {
  const { handler } = await makeHandler();
  await handler(event('POST /family', { body: {} }));
  const noConsent = await handler(event('POST /family/children', {
    body: { email: 'parent+kid@example.com', displayName: 'Kid', password: 'KidPass2026a' },
  }));
  assert.equal(noConsent.statusCode, 400);
  assert.match(parse(noConsent).error, /consent/i);

  const child = parse(await handler(event('POST /family/children', {
    body: { email: 'parent+kid@example.com', displayName: 'Kid', password: 'KidPass2026a', consent: { agreed: true } },
  })));
  assert.ok(child.childSub);
  const fam = parse(await handler(event('GET /family')));
  const kid = fam.family.members.find((m) => m.role === 'child');
  assert.equal(kid.consent.guardianSub, 'guardian-1');
  assert.equal(kid.consent.consentVersion, '2026-07-18');
  const childProfile = parse(await handler(event('GET /user/profile', { sub: child.childSub }))).profile;
  assert.equal(childProfile.familyRole, 'child');
  assert.deepEqual(childProfile.entitlements['*'], { analysis: false, analysisScope: 'own' });
});

test('guardian reads child data; child and outsiders cannot read others', async () => {
  const { handler } = await makeHandler();
  const child = await setupFamilyWithChild(handler);
  await handler(event('PUT /user/data/{app}/{key}', {
    sub: child.childSub,
    pathParameters: { app: 'logic-gates', key: 'session-1' },
    body: { value: { events: 3 } },
  }));
  const read = parse(await handler(event('GET /family/member/{sub}/data', {
    pathParameters: { sub: child.childSub },
    queryStringParameters: { app: 'logic-gates' },
  })));
  assert.equal(read.entries.length, 1);
  assert.deepEqual(read.entries[0].value, { events: 3 });
  assert.deepEqual(read.profile.entitlements['*'], { analysis: false, analysisScope: 'own' });

  const childAttempt = await handler(event('GET /family/member/{sub}/data', {
    sub: child.childSub,
    pathParameters: { sub: 'guardian-1' },
  }));
  assert.equal(childAttempt.statusCode, 403);

  const outsider = await handler(event('GET /family/member/{sub}/data', {
    sub: 'stranger-9',
    pathParameters: { sub: child.childSub },
  }));
  assert.equal(outsider.statusCode, 403);
});

test('guardian updates child entitlements; children cannot self-manage', async () => {
  const { handler } = await makeHandler();
  const child = await setupFamilyWithChild(handler);
  const updated = parse(await handler(event('PUT /family/member/{sub}/entitlements', {
    pathParameters: { sub: child.childSub },
    body: { entitlements: { '*': { analysis: false, analysisScope: 'own' }, 'math-quiz': { analysis: true, analysisScope: 'own' } } },
  })));
  assert.equal(updated.profile.entitlements['math-quiz'].analysis, true);
  const selfAttempt = await handler(event('PUT /user/profile', {
    sub: child.childSub,
    body: { entitlements: { '*': { analysis: true, analysisScope: 'family' } } },
  }));
  assert.equal(selfAttempt.statusCode, 403);
});

test('emailed invite sends a link with the code and optional cc to the guardian', async () => {
  const { handler, sentEmails } = await makeHandler();
  await handler(event('POST /family', { body: {} }));
  const invite = parse(await handler(event('POST /family/invites', {
    body: { email: 'Other.Parent@Example.com', message: 'Join us!', ccSelf: true },
  })));
  assert.equal(invite.emailedTo, 'other.parent@example.com');
  assert.equal(invite.ccSelf, true);
  assert.equal(sentEmails.length, 1);
  const sent = sentEmails[0];
  assert.deepEqual(sent.Destination.ToAddresses, ['other.parent@example.com']);
  assert.deepEqual(sent.Destination.CcAddresses, ['guardian-1@example.com']);
  const text = sent.Content.Simple.Body.Text.Data;
  assert.ok(text.includes(`/account/family/?invite=${encodeURIComponent(invite.code)}`), 'link carries the code');
  assert.ok(text.includes('Join us!'), 'custom message included');

  const joined = parse(await handler(event('POST /family/join', {
    sub: 'guardian-9',
    body: { code: invite.code },
  })));
  assert.equal(joined.role, 'guardian');

  const badEmail = await handler(event('POST /family/invites', { body: { email: 'not-an-email' } }));
  assert.equal(badEmail.statusCode, 400);
});

test('profile records terms consent via PUT', async () => {
  const { handler } = await makeHandler();
  const updated = parse(await handler(event('PUT /user/profile', {
    body: { termsConsent: { version: '2024-12-17' } },
  })));
  assert.deepEqual(updated.profile.termsConsent, { version: '2024-12-17', at: '2026-07-18T00:00:00.000Z' });
});

test('invite round-trip adds a second guardian', async () => {
  const { handler } = await makeHandler();
  await handler(event('POST /family', { body: {} }));
  const invite = parse(await handler(event('POST /family/invites')));
  assert.match(invite.code, /^[A-Z0-9]+\./);
  const joined = parse(await handler(event('POST /family/join', {
    sub: 'guardian-2',
    body: { code: invite.code },
  })));
  assert.equal(joined.role, 'guardian');
  const fam = parse(await handler(event('GET /family', { sub: 'guardian-2' })));
  assert.equal(fam.family.members.length, 2);
  const reuse = await handler(event('POST /family/join', { sub: 'guardian-3', body: { code: invite.code } }));
  assert.equal(reuse.statusCode, 400, 'invites are single-use');
});

test('guardian deletes child account fully; child cannot self-delete', async () => {
  const { handler, cognitoUsers, store } = await makeHandler();
  const child = await setupFamilyWithChild(handler);
  await handler(event('PUT /user/data/{app}/{key}', {
    sub: child.childSub,
    pathParameters: { app: 'logic-gates', key: 'session-1' },
    body: { value: 1 },
  }));
  const selfDelete = await handler(event('DELETE /user/account', { sub: child.childSub }));
  assert.equal(selfDelete.statusCode, 403);

  const noFlag = await handler(event('DELETE /family/member/{sub}', {
    pathParameters: { sub: child.childSub },
    body: {},
  }));
  assert.equal(noFlag.statusCode, 400);

  const deleted = parse(await handler(event('DELETE /family/member/{sub}', {
    pathParameters: { sub: child.childSub },
    body: { deleteAccount: true },
  })));
  assert.equal(deleted.deleted, true);
  assert.equal(cognitoUsers.size, 0, 'child cognito user removed');
  assert.equal([...store.keys()].filter((k) => k.startsWith(`USER#${child.childSub}|`)).length, 0);
  assert.equal([...store.keys()].filter((k) => k.includes(`MEMBER#${child.childSub}`)).length, 0);
});

test('last guardian deleting their account removes the whole family record', async () => {
  const { handler, store } = await makeHandler();
  await handler(event('POST /family', { body: {} }));
  await handler(event('POST /family/invites'));
  await handler(event('DELETE /user/account'));
  assert.equal([...store.keys()].filter((k) => k.startsWith('FAMILY#')).length, 0,
    'META, MEMBER, and INVITE items all cleaned up');
});
