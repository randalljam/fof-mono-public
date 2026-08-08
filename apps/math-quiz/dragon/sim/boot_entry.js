// Boot entry rules for Dragon Baby.
//
// Hard refresh / cold open always shows "Who's playing?" — sticky ?user= and
// localStorage must not skip the picker. Only an explicit handoff resume
// (?resume=1&user=…) skips the picker (Take over / auto-claim reload).
//
// A pending Go-quiz is restored only on claim or handoff resume — not when the
// owner hard-refreshes an ordinary session.

/** @deprecated Documents the sticky-user bug — do not use in the game. */
export function brokenResolveBootEntry({
  urlUser = '',
  urlFolder = '',
  rememberedUser = '',
  rememberedFolder = '',
} = {}) {
  const folder = urlFolder || rememberedFolder || 'tlkids';
  const user = urlUser || rememberedUser || '';
  return {
    folder,
    user,
    needsPlayerPicker: !user,
    handoffResume: false,
  };
}

export function resolveBootEntry({
  urlUser = '',
  urlFolder = '',
  urlResume = '',
  rememberedUser = '',
  rememberedFolder = '',
} = {}) {
  const folder = urlFolder || rememberedFolder || 'tlkids';
  const resumeFlag = urlResume === true
    || urlResume === 1
    || urlResume === '1'
    || String(urlResume).toLowerCase() === 'true';
  if (resumeFlag && urlUser) {
    return {
      folder,
      user: String(urlUser),
      needsPlayerPicker: false,
      handoffResume: true,
    };
  }
  return {
    folder,
    user: '',
    needsPlayerPicker: true,
    handoffResume: false,
    // rememberedUser kept only for callers that want a picker default hint
    rememberedUser: rememberedUser || '',
  };
}

/** Destination of a transfer resumes immediately; source keeps the Transferred card. */
export function shouldAutoResumeHandoff({ canClaim = false, isOwner = false } = {}) {
  return !!(canClaim || isOwner);
}

/** Only claim / explicit handoff resume may reopen a Go-gate quiz. */
export function pendingQuizForBoot({
  pendingQuiz = null,
  claimed = false,
  handoffResume = false,
} = {}) {
  if (!pendingQuiz || !pendingQuiz.items || !pendingQuiz.items.length) return null;
  if (claimed || handoffResume) return pendingQuiz;
  return null;
}

export function gamePageUrl({
  user = '',
  folder = 'tlkids',
  resume = false,
  hostname = '127.0.0.1',
  port = '8907',
  pathname = '/dragon/index.html',
} = {}) {
  const params = new URLSearchParams();
  if (folder && folder !== 'tlkids') params.set('folder', folder);
  if (user) params.set('user', user);
  if (resume) params.set('resume', '1');
  const q = params.toString();
  return `http://${hostname}:${port}${pathname}${q ? `?${q}` : ''}`;
}
