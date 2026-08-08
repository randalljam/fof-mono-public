// Family accounts: guardian/child relations, per-app entitlements, and the
// COPPA/FERPA-aligned child-account flow (guardian-created accounts with a
// recorded consent, guardian review of child data, guardian deletion).
//
// Data model (same table as user data):
//   USER#<sub>   / PROFILE            displayName, familyId, familyRole,
//                                     entitlements, consent, updatedAt
//   FAMILY#<id>  / META               name, createdBy, createdAt
//   FAMILY#<id>  / MEMBER#<sub>       role guardian|child, displayName, email,
//                                     addedAt, consent (children: guardianSub,
//                                     consentVersion, at)
//   FAMILY#<id>  / INVITE#<code>      role, createdBy, expiresAt
//
// Every route derives the caller from the JWT sub; cross-account reads exist
// ONLY as guardian→own-family-member and are checked server-side on each call.
// Entitlements shape (per app, '*' = default): { analysis: bool,
// analysisScope: 'own'|'family' } — resolveEntitlement(profile, app).
import { randomUUID, randomBytes } from 'node:crypto';
import {
  DeleteCommand,
  GetCommand,
  PutCommand,
  QueryCommand,
} from '@aws-sdk/lib-dynamodb';
import {
  AdminCreateUserCommand,
  AdminSetUserPasswordCommand,
} from '@aws-sdk/client-cognito-identity-provider';
import { SendEmailCommand } from '@aws-sdk/client-sesv2';

export const COPPA_CONSENT_VERSION = '2026-07-18';
const INVITE_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const NAME_PATTERN = /^[a-z0-9][a-z0-9_.-]{0,63}$/i;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const DEFAULT_ENTITLEMENTS = {
  guardian: { '*': { analysis: true, analysisScope: 'family' } },
  child: { '*': { analysis: false, analysisScope: 'own' } },
  standalone: { '*': { analysis: true, analysisScope: 'own' } },
};

function response(statusCode, body) {
  return {
    statusCode,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}
const badRequest = (message) => response(400, { error: message });
const forbidden = (message) => response(403, { error: message });

export function resolveEntitlement(profile, app) {
  const entitlements = profile?.entitlements || {};
  return entitlements[app] || entitlements['*'] || { analysis: false, analysisScope: 'own' };
}
export function publicProfile(item) {
  if (!item) return null;
  return {
    displayName: item.displayName || null,
    familyId: item.familyId || null,
    familyRole: item.familyRole || null,
    entitlements: item.entitlements || null,
    consent: item.consent || null,
    termsConsent: item.termsConsent || null,
    updatedAt: item.updatedAt || null,
  };
}
async function getProfile(ctx, sub) {
  const result = await ctx.docClient.send(new GetCommand({
    TableName: ctx.tableName,
    Key: { PK: `USER#${sub}`, SK: 'PROFILE' },
  }));
  return result.Item || null;
}
async function putProfile(ctx, sub, attrs) {
  const existing = (await getProfile(ctx, sub)) || {};
  const item = {
    ...existing,
    ...attrs,
    PK: `USER#${sub}`,
    SK: 'PROFILE',
    updatedAt: ctx.now(),
  };
  await ctx.docClient.send(new PutCommand({ TableName: ctx.tableName, Item: item }));
  return item;
}
async function getMember(ctx, familyId, sub) {
  const result = await ctx.docClient.send(new GetCommand({
    TableName: ctx.tableName,
    Key: { PK: `FAMILY#${familyId}`, SK: `MEMBER#${sub}` },
  }));
  return result.Item || null;
}
async function requireGuardian(ctx, sub) {
  const profile = await getProfile(ctx, sub);
  if (!profile?.familyId) return { error: forbidden('You are not in a family.') };
  const member = await getMember(ctx, profile.familyId, sub);
  if (!member || member.role !== 'guardian') {
    return { error: forbidden('Only family guardians can do this.') };
  }
  return { profile, member, familyId: profile.familyId };
}
async function familyItems(ctx, familyId, skPrefix) {
  // DynamoDB rejects empty key values, so an all-items query must omit the
  // begins_with condition rather than pass ''.
  const result = await ctx.docClient.send(new QueryCommand({
    TableName: ctx.tableName,
    KeyConditionExpression: skPrefix ? 'PK = :pk AND begins_with(SK, :sk)' : 'PK = :pk',
    ExpressionAttributeValues: {
      ':pk': `FAMILY#${familyId}`,
      ...(skPrefix ? { ':sk': skPrefix } : {}),
    },
  }));
  return result.Items || [];
}
function memberView(item) {
  return {
    sub: item.SK.slice('MEMBER#'.length),
    role: item.role,
    displayName: item.displayName || null,
    email: item.email || null,
    addedAt: item.addedAt,
    consent: item.consent || null,
  };
}

async function cleanupFamilyIfEmpty(ctx, familyId) {
  const members = await familyItems(ctx, familyId, 'MEMBER#');
  if (members.length) return;
  // Last member gone — remove the META and any outstanding invites so no
  // orphaned family records linger.
  const leftovers = await familyItems(ctx, familyId);
  for (const item of leftovers) {
    await ctx.docClient.send(new DeleteCommand({
      TableName: ctx.tableName,
      Key: { PK: item.PK, SK: item.SK },
    }));
  }
}
export async function removeMembershipOnAccountDelete(ctx, sub) {
  const profile = await getProfile(ctx, sub);
  if (!profile?.familyId) return;
  await ctx.docClient.send(new DeleteCommand({
    TableName: ctx.tableName,
    Key: { PK: `FAMILY#${profile.familyId}`, SK: `MEMBER#${sub}` },
  }));
  await cleanupFamilyIfEmpty(ctx, profile.familyId);
}

export async function handleFamilyRoute(ctx, event, sub, body) {
  const routeKey = event.routeKey;

  if (routeKey === 'GET /user/profile') {
    const profile = await getProfile(ctx, sub);
    return response(200, { profile: publicProfile(profile) });
  }

  if (routeKey === 'PUT /user/profile') {
    const attrs = {};
    if (typeof body.displayName === 'string') attrs.displayName = body.displayName.slice(0, 80);
    if (body.termsConsent && typeof body.termsConsent === 'object') {
      attrs.termsConsent = {
        version: String(body.termsConsent.version || '').slice(0, 20),
        at: ctx.now(),
      };
    }
    if (body.entitlements !== undefined) {
      const current = await getProfile(ctx, sub);
      if (current?.familyRole === 'child') {
        return forbidden('Child account settings are managed by a family guardian.');
      }
      attrs.entitlements = body.entitlements;
    }
    const item = await putProfile(ctx, sub, attrs);
    return response(200, { profile: publicProfile(item) });
  }

  if (routeKey === 'POST /family') {
    const existing = await getProfile(ctx, sub);
    if (existing?.familyId) return badRequest('You are already in a family.');
    const familyId = randomUUID();
    const stamp = ctx.now();
    await ctx.docClient.send(new PutCommand({
      TableName: ctx.tableName,
      Item: {
        PK: `FAMILY#${familyId}`,
        SK: 'META',
        name: String(body.name || 'Our family').slice(0, 80),
        createdBy: sub,
        createdAt: stamp,
      },
    }));
    await ctx.docClient.send(new PutCommand({
      TableName: ctx.tableName,
      Item: {
        PK: `FAMILY#${familyId}`,
        SK: `MEMBER#${sub}`,
        role: 'guardian',
        displayName: body.displayName || existing?.displayName || null,
        email: body.email || null,
        addedAt: stamp,
      },
    }));
    await putProfile(ctx, sub, {
      familyId,
      familyRole: 'guardian',
      entitlements: existing?.entitlements || DEFAULT_ENTITLEMENTS.guardian,
    });
    return response(200, { familyId });
  }

  if (routeKey === 'GET /family') {
    const profile = await getProfile(ctx, sub);
    if (!profile?.familyId) return response(200, { family: null });
    const membership = await getMember(ctx, profile.familyId, sub);
    if (!membership) return response(200, { family: null });
    const metaResult = await ctx.docClient.send(new GetCommand({
      TableName: ctx.tableName,
      Key: { PK: `FAMILY#${profile.familyId}`, SK: 'META' },
    }));
    const members = await familyItems(ctx, profile.familyId, 'MEMBER#');
    return response(200, {
      family: {
        familyId: profile.familyId,
        name: metaResult.Item?.name || null,
        yourRole: membership.role,
        members: members.map(memberView),
      },
    });
  }

  if (routeKey === 'POST /family/invites') {
    const guard = await requireGuardian(ctx, sub);
    if (guard.error) return guard.error;
    const inviteeEmail = body.email ? String(body.email).trim().toLowerCase() : null;
    if (inviteeEmail && !EMAIL_PATTERN.test(inviteeEmail)) {
      return badRequest('Invalid invite email address.');
    }
    const code = randomBytes(6).toString('base64url').replace(/[-_]/g, 'x').slice(0, 8).toUpperCase();
    await ctx.docClient.send(new PutCommand({
      TableName: ctx.tableName,
      Item: {
        PK: `FAMILY#${guard.familyId}`,
        SK: `INVITE#${code}`,
        role: 'guardian',
        createdBy: sub,
        createdAt: ctx.now(),
        expiresAt: Date.now() + INVITE_TTL_MS,
        familyId: guard.familyId,
        inviteeEmail,
      },
    }));
    // The invite code embeds the family id so joiners don't need to know it.
    const fullCode = `${code}.${guard.familyId}`;
    if (!inviteeEmail) {
      return response(200, { code: fullCode, expiresInDays: 7 });
    }
    // Email the invite as a link with the code behind the scenes; optionally cc
    // the inviting guardian so they hold a copy to re-forward if it lands in spam.
    const callerEmail = event.requestContext?.authorizer?.jwt?.claims?.email || null;
    const inviterName = guard.profile?.displayName || callerEmail || 'A family guardian';
    const message = String(body.message || '').slice(0, 500);
    const link = `${ctx.siteBaseUrl}/account/family/?invite=${encodeURIComponent(fullCode)}`;
    const textBody = `${inviterName} invited you to join their family on Focus on Foundations.\n\n`
      + (message ? `Their message:\n${message}\n\n` : '')
      + `Accept the invite (valid for 7 days):\n${link}\n\n`
      + 'You\'ll be asked to sign in or create an account first if you don\'t have one.';
    const htmlMessage = message
      ? `<p>Their message:</p><blockquote>${message.replace(/</g, '&lt;')}</blockquote>`
      : '';
    await ctx.sesClient.send(new SendEmailCommand({
      FromEmailAddress: `Focus on Foundations <${ctx.sesFromEmail}>`,
      Destination: {
        ToAddresses: [inviteeEmail],
        CcAddresses: body.ccSelf === true && callerEmail ? [callerEmail] : [],
      },
      Content: {
        Simple: {
          Subject: { Data: `${inviterName} invited you to their Focus on Foundations family` },
          Body: {
            Text: { Data: textBody },
            Html: {
              Data: `<p>${inviterName} invited you to join their family on Focus on Foundations.</p>`
                + htmlMessage
                + `<p><a href="${link}">Accept the invite</a> (valid for 7 days).</p>`
                + '<p>You\'ll be asked to sign in or create an account first if you don\'t have one.</p>',
            },
          },
        },
      },
    }));
    return response(200, {
      code: fullCode,
      expiresInDays: 7,
      emailedTo: inviteeEmail,
      ccSelf: body.ccSelf === true && Boolean(callerEmail),
    });
  }

  if (routeKey === 'POST /family/join') {
    const raw = String(body.code || '');
    const [code, familyId] = raw.split('.');
    if (!code || !familyId) return badRequest('Invalid invite code.');
    const existing = await getProfile(ctx, sub);
    if (existing?.familyId) return badRequest('You are already in a family.');
    const inviteResult = await ctx.docClient.send(new GetCommand({
      TableName: ctx.tableName,
      Key: { PK: `FAMILY#${familyId}`, SK: `INVITE#${code}` },
    }));
    const invite = inviteResult.Item;
    if (!invite || invite.expiresAt < Date.now()) return badRequest('Invite code is invalid or expired.');
    const stamp = ctx.now();
    await ctx.docClient.send(new PutCommand({
      TableName: ctx.tableName,
      Item: {
        PK: `FAMILY#${familyId}`,
        SK: `MEMBER#${sub}`,
        role: invite.role,
        displayName: existing?.displayName || body.displayName || null,
        email: body.email || null,
        addedAt: stamp,
      },
    }));
    await ctx.docClient.send(new DeleteCommand({
      TableName: ctx.tableName,
      Key: { PK: `FAMILY#${familyId}`, SK: `INVITE#${code}` },
    }));
    await putProfile(ctx, sub, {
      familyId,
      familyRole: invite.role,
      entitlements: existing?.entitlements
        || DEFAULT_ENTITLEMENTS[invite.role === 'guardian' ? 'guardian' : 'standalone'],
    });
    return response(200, { joined: true, familyId, role: invite.role });
  }

  if (routeKey === 'POST /family/children') {
    const guard = await requireGuardian(ctx, sub);
    if (guard.error) return guard.error;
    const email = String(body.email || '').trim().toLowerCase();
    const displayName = String(body.displayName || '').trim().slice(0, 80);
    const password = String(body.password || '');
    if (!EMAIL_PATTERN.test(email)) return badRequest('A valid email for the child account is required (a parent plus-address like you+kid@example.com works).');
    if (!displayName) return badRequest('A display name for the child is required.');
    if (body?.consent?.agreed !== true) {
      return badRequest('Guardian consent is required to create a child account.');
    }
    let created;
    try {
      created = await ctx.cognitoClient.send(new AdminCreateUserCommand({
        UserPoolId: ctx.userPoolId,
        Username: email,
        MessageAction: 'SUPPRESS',
        UserAttributes: [
          { Name: 'email', Value: email },
          { Name: 'email_verified', Value: 'true' },
        ],
      }));
      await ctx.cognitoClient.send(new AdminSetUserPasswordCommand({
        UserPoolId: ctx.userPoolId,
        Username: email,
        Password: password,
        Permanent: true,
      }));
    } catch (error) {
      if (error?.name === 'UsernameExistsException') {
        return badRequest('An account with that email already exists.');
      }
      if (error?.name === 'InvalidPasswordException') {
        return badRequest('Password does not meet the policy (8+ chars with upper, lower, and a digit).');
      }
      throw error;
    }
    const childSub = created.User?.Attributes?.find((a) => a.Name === 'sub')?.Value
      || created.User?.Username;
    const stamp = ctx.now();
    const consent = {
      guardianSub: sub,
      consentVersion: COPPA_CONSENT_VERSION,
      at: stamp,
    };
    await ctx.docClient.send(new PutCommand({
      TableName: ctx.tableName,
      Item: {
        PK: `FAMILY#${guard.familyId}`,
        SK: `MEMBER#${childSub}`,
        role: 'child',
        displayName,
        email,
        addedAt: stamp,
        consent,
      },
    }));
    await putProfile(ctx, childSub, {
      displayName,
      familyId: guard.familyId,
      familyRole: 'child',
      entitlements: DEFAULT_ENTITLEMENTS.child,
      consent,
    });
    return response(200, { childSub, email, displayName });
  }

  if (routeKey === 'GET /family/member/{sub}/data') {
    const guard = await requireGuardian(ctx, sub);
    if (guard.error) return guard.error;
    const targetSub = event.pathParameters?.sub;
    const app = event.queryStringParameters?.app;
    if (app !== undefined && !NAME_PATTERN.test(app)) return badRequest('Invalid app name.');
    const targetMember = await getMember(ctx, guard.familyId, targetSub);
    if (!targetMember) return forbidden('That user is not in your family.');
    const scope = resolveEntitlement(guard.profile, app || '*');
    if (!scope.analysis || scope.analysisScope !== 'family') {
      return forbidden('Your account does not have family-scope analysis access.');
    }
    const result = await ctx.docClient.send(new QueryCommand({
      TableName: ctx.tableName,
      KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
      ExpressionAttributeValues: {
        ':pk': `USER#${targetSub}`,
        ':sk': app ? `APP#${app}#` : 'APP#',
      },
    }));
    const targetProfile = await getProfile(ctx, targetSub);
    return response(200, {
      member: memberView(targetMember),
      profile: publicProfile(targetProfile),
      entries: (result.Items || []).map((item) => ({
        app: item.app, key: item.key, value: item.value, updatedAt: item.updatedAt,
      })),
    });
  }

  if (routeKey === 'PUT /family/member/{sub}/entitlements') {
    const guard = await requireGuardian(ctx, sub);
    if (guard.error) return guard.error;
    const targetSub = event.pathParameters?.sub;
    const targetMember = await getMember(ctx, guard.familyId, targetSub);
    if (!targetMember) return forbidden('That user is not in your family.');
    if (targetMember.role !== 'child') {
      return badRequest('Only child-account entitlements are managed by guardians.');
    }
    if (!body.entitlements || typeof body.entitlements !== 'object') {
      return badRequest('Body must include an "entitlements" object.');
    }
    const item = await putProfile(ctx, targetSub, { entitlements: body.entitlements });
    return response(200, { profile: publicProfile(item) });
  }

  if (routeKey === 'DELETE /family/member/{sub}') {
    const targetSub = event.pathParameters?.sub;
    if (targetSub === sub) {
      // Leave the family (any role except a child; children are managed by guardians).
      const profile = await getProfile(ctx, sub);
      if (!profile?.familyId) return badRequest('You are not in a family.');
      if (profile.familyRole === 'child') {
        return forbidden('Child accounts are managed by a family guardian.');
      }
      await ctx.docClient.send(new DeleteCommand({
        TableName: ctx.tableName,
        Key: { PK: `FAMILY#${profile.familyId}`, SK: `MEMBER#${sub}` },
      }));
      await putProfile(ctx, sub, { familyId: null, familyRole: null });
      await cleanupFamilyIfEmpty(ctx, profile.familyId);
      return response(200, { left: true });
    }
    const guard = await requireGuardian(ctx, sub);
    if (guard.error) return guard.error;
    const targetMember = await getMember(ctx, guard.familyId, targetSub);
    if (!targetMember) return forbidden('That user is not in your family.');
    if (targetMember.role !== 'child') {
      return forbidden('Guardians can only remove child accounts; other guardians must leave themselves.');
    }
    if (body.deleteAccount === true) {
      // Consent-revocation path: full deletion of the child account and data.
      const result = await ctx.deleteWholeAccount(targetSub);
      await ctx.docClient.send(new DeleteCommand({
        TableName: ctx.tableName,
        Key: { PK: `FAMILY#${guard.familyId}`, SK: `MEMBER#${targetSub}` },
      }));
      return response(200, { deleted: true, ...result });
    }
    return badRequest('Removing a child requires {"deleteAccount": true} — child accounts cannot exist outside a family.');
  }

  return null;
}
