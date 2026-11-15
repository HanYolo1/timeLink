// Where the site and the project live. Pages are served from the root of the site's own domain.
export const siteUrl = 'https://longshot.magicbean.dev';
export const repository = 'https://github.com/HanYolo1/timeLink';
export const issueUrl = `${repository}/issues/new`;
/** A file in the repository on GitHub, on main. (GitHub's shape: /blob/main/, not Forgejo's /src/branch/main/.) */
export const sourceUrl = (file: string) => `${repository}/blob/main/${file}`;
/** GitHub's editor for a file on main: saving it proposes the change as a pull request. (GitHub's shape: /edit/main/, not Forgejo's /_edit/main/.) */
export const editUrl = (file: string) => `${repository}/edit/main/${file}`;
