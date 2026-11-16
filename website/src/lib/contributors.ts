// The people behind timeLink, for the team page: the authors of this repository's commits on GitHub, most commits
// first. Collected once per build, like the progress feed; if GitHub can't be reached, the page says so. Merge
// commits are left out: they credit whoever merged, not who wrote the change.
import { API } from './progress.ts';
const PER_PAGE = 50;

export interface Contributor { name: string; avatar: string | null; profile: string | null; commits: number }

/** A GitHub account if the commit carries one, else one from its noreply address. */
function identify(commit: any): Omit<Contributor, 'commits'> & { key: string } {
  const user = commit.author;
  if (user?.login) {
    return { key: `github:${user.login.toLowerCase()}`, name: user.name || user.login, avatar: user.avatar_url,
      profile: `https://github.com/${encodeURIComponent(user.login)}` };
  }
  const { name = 'Unknown', email = '' } = commit.commit?.author ?? {};
  const github = email.match(/^(?:(\d+)\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$/i);
  if (github) {
    return { key: `github:${github[2].toLowerCase()}`, name: name || github[2],
      avatar: github[1] ? `https://avatars.githubusercontent.com/u/${github[1]}?s=112` : `https://github.com/${github[2]}.png?size=112`,
      profile: `https://github.com/${github[2]}` };
  }
  return { key: `email:${email.toLowerCase() || name}`, name, avatar: null, profile: null };
}

export async function collectContributors({ fetcher = fetch, maxPages = 200, token = '' } = {}): Promise<Contributor[]> {
  const people = new Map<string, Contributor>();
  for (let page = 1; page <= maxPages; page++) {
    const url = `${API}/commits?per_page=${PER_PAGE}&page=${page}`;
    // (unauthenticated GitHub allows 60 requests an hour, far short of a page per 50 commits: the build passes a token)
    const headers = { Accept: 'application/json', 'User-Agent': 'timeLink-website', ...(token ? { Authorization: `Bearer ${token}` } : {}) };
    const response = await fetcher(url, { headers,
      signal: AbortSignal.timeout(20000), redirect: 'error' });
    if (!response.ok) throw new Error(`GitHub commits: HTTP ${response.status}`);
    const commits = await response.json();
    if (!Array.isArray(commits)) throw new Error('Unexpected commits response.');
    for (const commit of commits) {
      if ((commit.parents?.length ?? 1) > 1) continue;
      const { key, ...person } = identify(commit);
      const known = people.get(key);
      if (known) known.commits++;
      else people.set(key, { ...person, commits: 1 });
    }
    if (commits.length < PER_PAGE) break;
  }
  // One person can appear under two identities (a GitHub account and a noreply address): join them by name, keeping
  // the one with a profile and picture.
  const byName = new Map<string, Contributor>();
  for (const person of people.values()) {
    const key = person.name.trim().toLowerCase();
    const known = byName.get(key);
    if (!known) { byName.set(key, { ...person }); continue; }
    known.commits += person.commits;
    if (!known.profile && person.profile) { known.profile = person.profile; known.avatar = person.avatar; }
  }
  return [...byName.values()].sort((a, b) => b.commits - a.commits || a.name.localeCompare(b.name, 'en'));
}

let built: Promise<Contributor[] | null> | undefined;
/** One collection per build (or dev server). */
export function buildContributors() {
  built ??= collectContributors({ token: process.env.GITHUB_TOKEN || process.env.GH_TOKEN || '' }).catch((error) => {
    console.warn(`Contributors unavailable for this build: ${error.message}`);
    return null;
  });
  return built;
}
