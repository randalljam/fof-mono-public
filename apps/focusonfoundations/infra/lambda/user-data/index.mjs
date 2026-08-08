// User-data API handler (API Gateway HTTP API + Cognito JWT authorizer).
// All routes operate on the calling user's own partition (PK USER#<sub>) —
// the sub comes from the validated JWT, never from client input, so no user
// can read or write another user's data.
//
// Routes:
//   GET    /user/data?app=<app>        list entries (optionally one app's)
//   PUT    /user/data/{app}/{key}      upsert one entry ({"value": <json>})
//   DELETE /user/data/{app}/{key}      remove one entry
//   POST   /user/migrate               batch-upsert guest entries ({"entries":[{app,key,value}]})
//   DELETE /user/account               delete every entry, then the Cognito user (GDPR)
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import {
  BatchWriteCommand,
  DeleteCommand,
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  QueryCommand,
} from '@aws-sdk/lib-dynamodb';
import {
  AdminDeleteUserCommand,
  CognitoIdentityProviderClient,
  ListUsersCommand,
} from '@aws-sdk/client-cognito-identity-provider';
import {
  DeleteObjectsCommand,
  GetObjectCommand,
  ListObjectVersionsCommand,
  ListObjectsV2Command,
  PutObjectCommand,
  S3Client,
} from '@aws-sdk/client-s3';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { handleFamilyRoute, removeMembershipOnAccountDelete } from './family.mjs';

const NAME_PATTERN = /^[a-z0-9][a-z0-9_.-]{0,63}$/i;
const MAX_VALUE_BYTES = 300 * 1024;
const MAX_MIGRATE_ENTRIES = 200;
const PRESIGN_TTL_SECONDS = 300;
const filePrefix = (sub) => `user-files/${sub}/`;
const fileKey = (sub, app, name) => `${filePrefix(sub)}${app}/${name}`;

function response(statusCode, body) {
  return {
    statusCode,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}
function badRequest(message) {
  return response(400, { error: message });
}
function validName(value) {
  return typeof value === 'string' && NAME_PATTERN.test(value);
}
function entryItem(sub, app, key, value, now) {
  return {
    PK: `USER#${sub}`,
    SK: `APP#${app}#${key}`,
    app,
    key,
    value,
    updatedAt: now,
  };
}
function toEntry(item) {
  return { app: item.app, key: item.key, value: item.value, updatedAt: item.updatedAt };
}
async function queryAllItems(docClient, tableName, sub, skPrefix, projection) {
  const items = [];
  let lastKey;
  do {
    const result = await docClient.send(new QueryCommand({
      TableName: tableName,
      KeyConditionExpression: skPrefix
        ? 'PK = :pk AND begins_with(SK, :sk)'
        : 'PK = :pk',
      ExpressionAttributeValues: {
        ':pk': `USER#${sub}`,
        ...(skPrefix ? { ':sk': skPrefix } : {}),
      },
      ...(projection ? { ProjectionExpression: projection } : {}),
      ExclusiveStartKey: lastKey,
    }));
    items.push(...(result.Items || []));
    lastKey = result.LastEvaluatedKey;
  } while (lastKey);
  return items;
}
async function batchWriteAll(docClient, tableName, requests) {
  for (let i = 0; i < requests.length; i += 25) {
    let pending = requests.slice(i, i + 25);
    while (pending.length) {
      const result = await docClient.send(new BatchWriteCommand({
        RequestItems: { [tableName]: pending },
      }));
      pending = result.UnprocessedItems?.[tableName] || [];
    }
  }
}

async function deleteAllUserFiles(s3Client, filesBucket, sub) {
  // The bucket is versioned, so GDPR deletion must purge every version and
  // delete marker — a plain delete would leave old copies recoverable.
  const removedKeys = new Set();
  let keyMarker;
  let versionIdMarker;
  do {
    const listing = await s3Client.send(new ListObjectVersionsCommand({
      Bucket: filesBucket,
      Prefix: filePrefix(sub),
      KeyMarker: keyMarker,
      VersionIdMarker: versionIdMarker,
    }));
    const versions = [...(listing.Versions || []), ...(listing.DeleteMarkers || [])];
    if (versions.length) {
      await s3Client.send(new DeleteObjectsCommand({
        Bucket: filesBucket,
        Delete: { Objects: versions.map((v) => ({ Key: v.Key, VersionId: v.VersionId })) },
      }));
      for (const v of listing.Versions || []) removedKeys.add(v.Key);
    }
    keyMarker = listing.IsTruncated ? listing.NextKeyMarker : undefined;
    versionIdMarker = listing.IsTruncated ? listing.NextVersionIdMarker : undefined;
  } while (keyMarker || versionIdMarker);
  return removedKeys.size;
}

export function buildHandler({ docClient, cognitoClient, s3Client, sesClient, filesBucket, presign = getSignedUrl, tableName, userPoolId, sesFromEmail, siteBaseUrl, now = () => new Date().toISOString() }) {
  async function deleteWholeAccount(targetSub) {
    const items = await queryAllItems(docClient, tableName, targetSub, undefined, 'PK, SK');
    await batchWriteAll(docClient, tableName, items.map((item) => ({
      DeleteRequest: { Key: { PK: item.PK, SK: item.SK } },
    })));
    const filesRemoved = await deleteAllUserFiles(s3Client, filesBucket, targetSub);
    // Cognito user goes last so a failed sweep leaves the account intact and retryable.
    const users = await cognitoClient.send(new ListUsersCommand({
      UserPoolId: userPoolId,
      Filter: `sub = "${targetSub}"`,
      Limit: 1,
    }));
    const username = users.Users?.[0]?.Username;
    if (username) {
      await cognitoClient.send(new AdminDeleteUserCommand({
        UserPoolId: userPoolId,
        Username: username,
      }));
    }
    return { dataItemsRemoved: items.length, filesRemoved };
  }
  return async function handler(event) {
    const sub = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!sub) return response(401, { error: 'Unauthorized' });
    const routeKey = event.routeKey;
    let body = {};
    if (event.body) {
      try {
        body = JSON.parse(event.body);
      } catch {
        return badRequest('Body must be valid JSON.');
      }
    }

    const familyCtx = { docClient, cognitoClient, sesClient, sesFromEmail, siteBaseUrl, tableName, userPoolId, now, deleteWholeAccount };
    const familyResponse = await handleFamilyRoute(familyCtx, event, sub, body);
    if (familyResponse) return familyResponse;

    if (routeKey === 'GET /user/data') {
      const app = event.queryStringParameters?.app;
      if (app !== undefined && !validName(app)) return badRequest('Invalid app name.');
      const items = await queryAllItems(docClient, tableName, sub, app ? `APP#${app}#` : 'APP#');
      return response(200, { entries: items.map(toEntry) });
    }

    if (routeKey === 'PUT /user/data/{app}/{key}' || routeKey === 'DELETE /user/data/{app}/{key}') {
      const { app, key } = event.pathParameters || {};
      if (!validName(app) || !validName(key)) return badRequest('Invalid app or key name.');
      if (routeKey.startsWith('DELETE')) {
        await docClient.send(new DeleteCommand({
          TableName: tableName,
          Key: { PK: `USER#${sub}`, SK: `APP#${app}#${key}` },
        }));
        return response(200, { deleted: true });
      }
      if (!('value' in body)) return badRequest('Body must include "value".');
      if (JSON.stringify(body.value).length > MAX_VALUE_BYTES) {
        return badRequest('Value too large — keep entries under 300 KB.');
      }
      const item = entryItem(sub, app, key, body.value, now());
      await docClient.send(new PutCommand({ TableName: tableName, Item: item }));
      return response(200, { saved: toEntry(item) });
    }

    if (routeKey === 'POST /user/migrate') {
      const entries = body.entries;
      if (!Array.isArray(entries) || !entries.length) {
        return badRequest('Body must include a non-empty "entries" array.');
      }
      if (entries.length > MAX_MIGRATE_ENTRIES) {
        return badRequest(`Too many entries — limit ${MAX_MIGRATE_ENTRIES} per call.`);
      }
      const stamp = now();
      const valid = [];
      const skipped = [];
      for (const entry of entries) {
        if (validName(entry?.app) && validName(entry?.key)
          && JSON.stringify(entry.value ?? null).length <= MAX_VALUE_BYTES) {
          valid.push({ PutRequest: { Item: entryItem(sub, entry.app, entry.key, entry.value ?? null, stamp) } });
        } else {
          skipped.push({ app: entry?.app, key: entry?.key });
        }
      }
      await batchWriteAll(docClient, tableName, valid);
      return response(200, { migrated: valid.length, skipped });
    }

    if (routeKey === 'GET /user/files') {
      const app = event.queryStringParameters?.app;
      if (app !== undefined && !validName(app)) return badRequest('Invalid app name.');
      const prefix = app ? `${filePrefix(sub)}${app}/` : filePrefix(sub);
      const files = [];
      let token;
      do {
        const listing = await s3Client.send(new ListObjectsV2Command({
          Bucket: filesBucket,
          Prefix: prefix,
          ContinuationToken: token,
        }));
        for (const obj of listing.Contents || []) {
          const [fileApp, ...nameParts] = obj.Key.slice(filePrefix(sub).length).split('/');
          files.push({
            app: fileApp,
            name: nameParts.join('/'),
            size: obj.Size,
            updatedAt: obj.LastModified instanceof Date ? obj.LastModified.toISOString() : obj.LastModified,
          });
        }
        token = listing.IsTruncated ? listing.NextContinuationToken : undefined;
      } while (token);
      return response(200, { files });
    }

    if (routeKey === 'POST /user/files/{app}/{name}/upload-url'
      || routeKey === 'GET /user/files/{app}/{name}/download-url'
      || routeKey === 'DELETE /user/files/{app}/{name}') {
      const { app, name } = event.pathParameters || {};
      if (!validName(app) || !validName(name)) return badRequest('Invalid app or file name.');
      const key = fileKey(sub, app, name);
      if (routeKey.startsWith('POST')) {
        const url = await presign(s3Client, new PutObjectCommand({
          Bucket: filesBucket,
          Key: key,
          ContentType: 'application/octet-stream',
        }), { expiresIn: PRESIGN_TTL_SECONDS });
        return response(200, { url, method: 'PUT', headers: { 'Content-Type': 'application/octet-stream' } });
      }
      if (routeKey.startsWith('GET')) {
        const url = await presign(s3Client, new GetObjectCommand({
          Bucket: filesBucket,
          Key: key,
        }), { expiresIn: PRESIGN_TTL_SECONDS });
        return response(200, { url, method: 'GET' });
      }
      await s3Client.send(new DeleteObjectsCommand({
        Bucket: filesBucket,
        Delete: { Objects: [{ Key: key }] },
      }));
      return response(200, { deleted: true });
    }

    if (routeKey === 'DELETE /user/account') {
      // Child accounts are deleted by their guardian (consent revocation), not
      // self-serve — a young child shouldn't be able to wipe the family's records
      // of their own work without the guardian.
      const profileResult = await docClient.send(new GetCommand({
        TableName: tableName,
        Key: { PK: `USER#${sub}`, SK: 'PROFILE' },
      }));
      if (profileResult.Item?.familyRole === 'child') {
        return response(403, { error: 'Child accounts are deleted by a family guardian from the family page.' });
      }
      await removeMembershipOnAccountDelete(familyCtx, sub);
      const result = await deleteWholeAccount(sub);
      return response(200, { deleted: true, ...result });
    }

    return response(404, { error: `Unknown route: ${routeKey}` });
  };
}

const defaultDocClient = DynamoDBDocumentClient.from(new DynamoDBClient({}), {
  marshallOptions: { removeUndefinedValues: true },
});
export const handler = buildHandler({
  docClient: defaultDocClient,
  cognitoClient: new CognitoIdentityProviderClient({}),
  s3Client: new S3Client({}),
  sesClient: new SESv2Client({}),
  filesBucket: process.env.FILES_BUCKET,
  tableName: process.env.TABLE_NAME,
  userPoolId: process.env.USER_POOL_ID,
  sesFromEmail: process.env.SES_FROM_EMAIL,
  siteBaseUrl: process.env.SITE_BASE_URL,
});
