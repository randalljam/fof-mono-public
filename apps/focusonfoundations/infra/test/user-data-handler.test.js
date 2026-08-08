const { test } = require('node:test');
const assert = require('node:assert/strict');

const TABLE = 'test-table';
const POOL = 'us-west-2_TESTPOOL';
const BUCKET = 'test-user-files';

// In-memory fakes keyed off the SDK command class names.
function makeFakes() {
  const store = new Map(); // `${PK}|${SK}` -> item
  const cognitoCalls = [];
  const docClient = {
    async send(cmd) {
      const name = cmd.constructor.name;
      const input = cmd.input;
      if (name === 'PutCommand') {
        store.set(`${input.Item.PK}|${input.Item.SK}`, input.Item);
        return {};
      }
      if (name === 'GetCommand') {
        const item = store.get(`${input.Key.PK}|${input.Key.SK}`);
        return item ? { Item: item } : {};
      }
      if (name === 'DeleteCommand') {
        store.delete(`${input.Key.PK}|${input.Key.SK}`);
        return {};
      }
      if (name === 'QueryCommand') {
        const pk = input.ExpressionAttributeValues[':pk'];
        const skPrefix = input.ExpressionAttributeValues[':sk'];
        const items = [...store.values()].filter(
          (item) => item.PK === pk && (!skPrefix || item.SK.startsWith(skPrefix))
        );
        return { Items: items };
      }
      if (name === 'BatchWriteCommand') {
        for (const [tableName, requests] of Object.entries(input.RequestItems)) {
          assert.equal(tableName, TABLE);
          for (const req of requests) {
            if (req.PutRequest) {
              store.set(`${req.PutRequest.Item.PK}|${req.PutRequest.Item.SK}`, req.PutRequest.Item);
            }
            if (req.DeleteRequest) {
              store.delete(`${req.DeleteRequest.Key.PK}|${req.DeleteRequest.Key.SK}`);
            }
          }
        }
        return { UnprocessedItems: {} };
      }
      throw new Error(`Unexpected doc command: ${name}`);
    },
  };
  const cognitoClient = {
    async send(cmd) {
      cognitoCalls.push({ name: cmd.constructor.name, input: cmd.input });
      if (cmd.constructor.name === 'ListUsersCommand') {
        return { Users: [{ Username: 'uuid-username-1' }] };
      }
      return {};
    },
  };
  const s3Objects = new Map(); // key -> {Size, LastModified}
  const s3Client = {
    async send(cmd) {
      const name = cmd.constructor.name;
      const input = cmd.input;
      if (name === 'ListObjectsV2Command') {
        const contents = [...s3Objects.entries()]
          .filter(([key]) => key.startsWith(input.Prefix))
          .map(([key, meta]) => ({ Key: key, Size: meta.Size, LastModified: meta.LastModified }));
        return { Contents: contents, IsTruncated: false };
      }
      if (name === 'ListObjectVersionsCommand') {
        const versions = [...s3Objects.entries()]
          .filter(([key]) => key.startsWith(input.Prefix))
          .map(([key]) => ({ Key: key, VersionId: 'v1' }));
        return { Versions: versions, DeleteMarkers: [], IsTruncated: false };
      }
      if (name === 'DeleteObjectsCommand') {
        for (const obj of input.Delete.Objects) s3Objects.delete(obj.Key);
        return {};
      }
      throw new Error(`Unexpected s3 command: ${name}`);
    },
  };
  const presign = async (client, cmd) =>
    `https://signed.example.com/${cmd.constructor.name}/${encodeURIComponent(cmd.input.Key)}`;
  return { store, cognitoCalls, docClient, cognitoClient, s3Objects, s3Client, presign };
}

async function makeHandler() {
  const { buildHandler } = await import('../lambda/user-data/index.mjs');
  const fakes = makeFakes();
  const handler = buildHandler({
    docClient: fakes.docClient,
    cognitoClient: fakes.cognitoClient,
    s3Client: fakes.s3Client,
    filesBucket: BUCKET,
    presign: fakes.presign,
    tableName: TABLE,
    userPoolId: POOL,
    now: () => '2026-07-17T00:00:00.000Z',
  });
  return { handler, ...fakes };
}

function event(routeKey, { sub = 'user-sub-1', body, pathParameters, queryStringParameters } = {}) {
  return {
    routeKey,
    pathParameters,
    queryStringParameters,
    body: body === undefined ? undefined : JSON.stringify(body),
    requestContext: sub ? { authorizer: { jwt: { claims: { sub } } } } : {},
  };
}

test('rejects requests without a JWT sub claim', async () => {
  const { handler } = await makeHandler();
  const result = await handler(event('GET /user/data', { sub: null }));
  assert.equal(result.statusCode, 401);
});

test('put, list, and delete round-trip within the caller partition', async () => {
  const { handler, store } = await makeHandler();
  const put = await handler(event('PUT /user/data/{app}/{key}', {
    pathParameters: { app: 'qrag', key: 'chat-2026' },
    body: { value: { question: 'What is knowledge?', answer: '42' } },
  }));
  assert.equal(put.statusCode, 200);
  assert.equal(store.size, 1);
  assert.ok(store.has('USER#user-sub-1|APP#qrag#chat-2026'));

  const list = await handler(event('GET /user/data', { queryStringParameters: { app: 'qrag' } }));
  const parsed = JSON.parse(list.body);
  assert.equal(parsed.entries.length, 1);
  assert.deepEqual(parsed.entries[0].value, { question: 'What is knowledge?', answer: '42' });

  const otherApp = await handler(event('GET /user/data', { queryStringParameters: { app: 'mathquiz' } }));
  assert.equal(JSON.parse(otherApp.body).entries.length, 0);

  const del = await handler(event('DELETE /user/data/{app}/{key}', {
    pathParameters: { app: 'qrag', key: 'chat-2026' },
  }));
  assert.equal(del.statusCode, 200);
  assert.equal(store.size, 0);
});

test('users cannot reach another user partition — sub comes from the token only', async () => {
  const { handler, store } = await makeHandler();
  await handler(event('PUT /user/data/{app}/{key}', {
    sub: 'user-a',
    pathParameters: { app: 'qrag', key: 'k1' },
    body: { value: 1 },
  }));
  const listB = await handler(event('GET /user/data', { sub: 'user-b' }));
  assert.equal(JSON.parse(listB.body).entries.length, 0);
  assert.ok(store.has('USER#user-a|APP#qrag#k1'));
});

test('rejects invalid app/key names and oversized values', async () => {
  const { handler } = await makeHandler();
  const badName = await handler(event('PUT /user/data/{app}/{key}', {
    pathParameters: { app: 'qrag', key: 'bad key!' },
    body: { value: 1 },
  }));
  assert.equal(badName.statusCode, 400);
  const tooBig = await handler(event('PUT /user/data/{app}/{key}', {
    pathParameters: { app: 'qrag', key: 'big' },
    body: { value: 'x'.repeat(301 * 1024) },
  }));
  assert.equal(tooBig.statusCode, 400);
});

test('migrate batch-writes valid entries and reports skipped ones', async () => {
  const { handler, store } = await makeHandler();
  const result = await handler(event('POST /user/migrate', {
    body: {
      entries: [
        { app: 'counting-creatures', key: 'state', value: { creatures: 7 } },
        { app: 'logic-gates', key: 'progress', value: { stage: 2 } },
        { app: 'bad app!', key: 'x', value: 1 },
      ],
    },
  }));
  const parsed = JSON.parse(result.body);
  assert.equal(parsed.migrated, 2);
  assert.equal(parsed.skipped.length, 1);
  assert.equal(store.size, 2);
});

test('account deletion sweeps the partition, the file prefix, and the Cognito user', async () => {
  const { handler, store, cognitoCalls, s3Objects } = await makeHandler();
  for (let i = 0; i < 3; i += 1) {
    await handler(event('PUT /user/data/{app}/{key}', {
      pathParameters: { app: 'qrag', key: `chat-${i}` },
      body: { value: i },
    }));
  }
  s3Objects.set('user-files/user-sub-1/math-quiz/working.sqlite', { Size: 1024, LastModified: new Date() });
  s3Objects.set('user-files/other-user/math-quiz/working.sqlite', { Size: 1024, LastModified: new Date() });
  const result = await handler(event('DELETE /user/account'));
  const parsed = JSON.parse(result.body);
  assert.equal(parsed.deleted, true);
  assert.equal(parsed.dataItemsRemoved, 3);
  assert.equal(parsed.filesRemoved, 1);
  assert.equal(store.size, 0);
  assert.equal(s3Objects.size, 1, 'other users\' files must be untouched');
  assert.ok(s3Objects.has('user-files/other-user/math-quiz/working.sqlite'));
  assert.deepEqual(cognitoCalls.map((c) => c.name), ['ListUsersCommand', 'AdminDeleteUserCommand']);
  assert.equal(cognitoCalls[1].input.Username, 'uuid-username-1');
});

test('file routes: presigned upload/download urls, list, and delete are partition-scoped', async () => {
  const { handler, s3Objects } = await makeHandler();
  const up = await handler(event('POST /user/files/{app}/{name}/upload-url', {
    pathParameters: { app: 'math-quiz', name: 'working.sqlite' },
  }));
  const upBody = JSON.parse(up.body);
  assert.equal(up.statusCode, 200);
  assert.equal(upBody.method, 'PUT');
  assert.ok(upBody.url.includes(encodeURIComponent('user-files/user-sub-1/math-quiz/working.sqlite')));

  const down = await handler(event('GET /user/files/{app}/{name}/download-url', {
    pathParameters: { app: 'math-quiz', name: 'working.sqlite' },
  }));
  assert.ok(JSON.parse(down.body).url.includes('GetObjectCommand'));

  const badName = await handler(event('POST /user/files/{app}/{name}/upload-url', {
    pathParameters: { app: 'math-quiz', name: '../escape' },
  }));
  assert.equal(badName.statusCode, 400);

  s3Objects.set('user-files/user-sub-1/math-quiz/working.sqlite', { Size: 94208, LastModified: new Date('2026-07-17T12:00:00Z') });
  s3Objects.set('user-files/user-sub-1/logic-gates/sessions.sqlite', { Size: 2048, LastModified: new Date('2026-07-17T13:00:00Z') });
  s3Objects.set('user-files/another-user/math-quiz/working.sqlite', { Size: 1, LastModified: new Date() });

  const listAll = JSON.parse((await handler(event('GET /user/files'))).body);
  assert.equal(listAll.files.length, 2, 'must only list the caller\'s files');
  const listOne = JSON.parse((await handler(event('GET /user/files', { queryStringParameters: { app: 'math-quiz' } }))).body);
  assert.deepEqual(listOne.files.map((f) => f.name), ['working.sqlite']);
  assert.equal(listOne.files[0].size, 94208);

  const del = await handler(event('DELETE /user/files/{app}/{name}', {
    pathParameters: { app: 'logic-gates', name: 'sessions.sqlite' },
  }));
  assert.equal(JSON.parse(del.body).deleted, true);
  assert.equal(s3Objects.has('user-files/user-sub-1/logic-gates/sessions.sqlite'), false);
});
