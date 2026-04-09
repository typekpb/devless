import { createAppAuth } from "@octokit/auth-app";
import { Octokit } from "@octokit/rest";

interface GitHubAppConfig {
  appId: string;
  privateKey: string;
  installationId: string;
}

let cachedToken: string | null = null;
let expiresAt = 0;

/**
 * Get a GitHub App installation token, caching and refreshing as needed.
 */
export async function getInstallationToken(config: GitHubAppConfig): Promise<string> {
  const now = Date.now();
  if (cachedToken && now < expiresAt) {
    return cachedToken;
  }

  console.log("==> Minting new GitHub App installation token");

  const auth = createAppAuth({
    appId: config.appId,
    privateKey: config.privateKey,
    installationId: config.installationId,
  });

  const { token, expiresAt: expiry } = await auth({ type: "installation" });
  cachedToken = token;
  // Expire 5 minutes early to avoid edge cases
  expiresAt = new Date(expiry!).getTime() - 5 * 60 * 1000;

  return token;
}

/**
 * Get an authenticated Octokit client using GitHub App credentials.
 */
export async function getOctokit(config: GitHubAppConfig): Promise<Octokit> {
  const token = await getInstallationToken(config);
  return new Octokit({ auth: token });
}
