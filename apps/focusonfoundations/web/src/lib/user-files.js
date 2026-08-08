// Per-user file storage client (education-app SQLite databases and other
// binary blobs). Files live in the fof-user-files bucket keyed to the signed-in
// user; the API hands out short-lived presigned URLs and the browser moves the
// bytes directly to/from S3, so file size never passes through the Lambda.
import { callUserDataApi } from './user-data.js';

export async function listUserFiles(app) {
  const query = app ? `?app=${encodeURIComponent(app)}` : '';
  const data = await callUserDataApi('GET', `/user/files${query}`);
  return data.files;
}
export async function uploadUserFile(app, name, bytes) {
  const target = await callUserDataApi(
    'POST',
    `/user/files/${encodeURIComponent(app)}/${encodeURIComponent(name)}/upload-url`
  );
  const response = await fetch(target.url, {
    method: target.method,
    headers: target.headers,
    body: bytes,
  });
  if (!response.ok) {
    throw new Error(`File upload failed (${response.status}).`);
  }
}
/** Returns the file bytes as a Uint8Array, or null if the file doesn't exist. */
export async function downloadUserFile(app, name) {
  const target = await callUserDataApi(
    'GET',
    `/user/files/${encodeURIComponent(app)}/${encodeURIComponent(name)}/download-url`
  );
  const response = await fetch(target.url);
  if (response.status === 404 || response.status === 403) return null;
  if (!response.ok) {
    throw new Error(`File download failed (${response.status}).`);
  }
  return new Uint8Array(await response.arrayBuffer());
}
export async function deleteUserFile(app, name) {
  await callUserDataApi('DELETE', `/user/files/${encodeURIComponent(app)}/${encodeURIComponent(name)}`);
}
