// Where the site and the project live. Pages are served from the root of the site's own domain.
//
// The site's own address is not decided yet: this fork has no domain of its own, and the upstream one is not ours to
// claim. Astro's `site:` turns this into a <link rel="canonical"> and the sitemap on every page, so it must not name a
// domain this fork does not control. Set DOCS_SITE_URL when the site is deployed somewhere; until then `siteUrl` is
// empty, Astro is given no `site`, and no page claims a canonical address.
const configured = (process.env.DOCS_SITE_URL || '').replace(/\/+$/, '');
/** The site's public origin, or '' when it has none yet. */
export const siteUrl = configured;
/** A base for resolving the site's own relative links while building and checking; never published. */
export const siteBase = configured || 'http://localhost';
export const repository = 'https://github.com/HanYolo1/timeLink';
export const issueUrl = `${repository}/issues/new`;
/** A file in the repository on GitHub, on main. (GitHub's shape: /blob/main/, not Forgejo's /src/branch/main/.) */
export const sourceUrl = (file: string) => `${repository}/blob/main/${file}`;
/** GitHub's editor for a file on main: saving it proposes the change as a pull request. (GitHub's shape: /edit/main/, not Forgejo's /_edit/main/.) */
export const editUrl = (file: string) => `${repository}/edit/main/${file}`;
