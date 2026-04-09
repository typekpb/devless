import { generateText, tool } from "ai";
import { bedrock } from "@ai-sdk/amazon-bedrock";
import { Bash } from "just-bash";
import { z } from "zod";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { loadOrchestratorSkills } from "./skills.js";
import { getInstallationToken, getOctokit } from "./github-app.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

interface Config {
  model: string;
  maxSteps: number;
}

function loadConfig(): Config {
  const defaults: Config = {
    model: "anthropic.claude-3-haiku-20240307-v1:0",
    maxSteps: 20,
  };

  try {
    const configPath = join(__dirname, "..", "config.yml");
    const content = readFileSync(configPath, "utf-8");

    const modelMatch = content.match(/^model:\s*(.+)$/m);
    if (modelMatch) {
      defaults.model = modelMatch[1].trim().replace(/^bedrock\//, "");
    }

    const stepsMatch = content.match(/^max_steps:\s*(\d+)$/m);
    if (stepsMatch) defaults.maxSteps = parseInt(stepsMatch[1], 10);
  } catch {
    // Use defaults
  }

  return defaults;
}

import { readFileSync, existsSync } from "fs";

function getGitHubAppConfig() {
  let privateKey = process.env.GITHUB_APP_PRIVATE_KEY ?? "";
  
  // Load from file if GITHUB_APP_PRIVATE_KEY_FILE is set
  const keyFile = process.env.GITHUB_APP_PRIVATE_KEY_FILE;
  if (keyFile && !privateKey) {
    const keyPath = keyFile.startsWith("~") 
      ? keyFile.replace("~", process.env.HOME ?? "") 
      : keyFile;
    if (existsSync(keyPath)) {
      privateKey = readFileSync(keyPath, "utf-8");
    }
  }
  
  if (!privateKey) {
    throw new Error("Either GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_FILE must be set");
  }

  return {
    appId: process.env.GITHUB_APP_ID!,
    privateKey,
    installationId: process.env.GITHUB_APP_INSTALLATION_ID!,
  };
}

interface EventPayload {
  eventType: string;
  repo: string;
  issueNumber: number;
  branch?: string;
}

export async function handleEvent(payload: EventPayload): Promise<void> {
  const { eventType, repo, issueNumber } = payload;
  const branch = payload.branch ?? `issue-${issueNumber}`;

  const config = loadConfig();
  const ghAppConfig = getGitHubAppConfig();

  // Get GitHub App installation token (stays outside sandbox)
  const githubToken = await getInstallationToken(ghAppConfig);
  const octokit = await getOctokit(ghAppConfig);
  const [owner, repoName] = repo.split("/");

  // Fetch issue/PR context
  const { data: issue } = await octokit.issues.get({
    owner,
    repo: repoName,
    issue_number: issueNumber,
  });

  // Load orchestrator skills (workflow instructions)
  const skills = await loadOrchestratorSkills();

  // Create sandboxed bash environment
  // NO secrets passed as env vars - credentials injected at network layer only
  const bash = new Bash({
    env: {
      REPO: repo,
      BRANCH: branch,
      ISSUE_NUMBER: String(issueNumber),
      OWNER: owner,
      REPO_NAME: repoName,
    },
    network: {
      allowedUrlPrefixes: [
        // GitHub API - token injected via transform
        {
          url: "https://api.github.com",
          transform: [{ headers: { Authorization: `Bearer ${githubToken}` } }],
        },
        // GitHub (for git clone/push) - token injected via transform
        {
          url: "https://github.com",
          transform: [{ headers: { Authorization: `Bearer ${githubToken}` } }],
        },
      ],
      allowedMethods: ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
    },
  });

  console.log(`==> Handling ${eventType} for ${repo} #${issueNumber}`);
  console.log(`==> Using model: ${config.model}`);

  // Run the agent
  const result = await generateText({
    model: bedrock(config.model),
    maxSteps: config.maxSteps,
    system: `You are an AI coding agent. You have access to a sandboxed bash environment.

${skills}

IMPORTANT:
- Execute commands one at a time and observe the output before proceeding
- If a command fails, analyze the error and try to fix it
- Always check command output before moving to the next step
- Use the environment variables provided ($REPO, $BRANCH, $ISSUE_NUMBER, etc.)
- GitHub authentication is handled automatically at the network layer
- Do NOT use aws cli commands - AWS operations are handled outside the sandbox
`,
    prompt: `Handle this GitHub event:

Event type: ${eventType}
Repository: ${repo}
Issue number: ${issueNumber}
Branch: ${branch}

Issue title: ${issue.title}
Issue body:
${issue.body ?? "(no body)"}

Execute the workflow steps to implement the requested changes and open a PR.`,
    tools: {
      bash: tool({
        description:
          "Execute a bash command in the sandboxed environment. Use this for git, gh, file operations, and other CLI tools. GitHub auth is automatic. Do NOT use aws cli.",
        parameters: z.object({
          command: z.string().describe("The bash command to execute"),
        }),
        execute: async ({ command }: { command: string }) => {
          console.log(`$ ${command}`);
          const result = await bash.exec(command);
          const output = result.stdout + result.stderr;
          console.log(output || "(no output)");
          return {
            exitCode: result.exitCode,
            output: output || "(no output)",
          };
        },
      }),
    },
  });

  console.log("\n==> Agent completed");
  console.log("Final response:", result.text);

  const toolCalls = result.steps.flatMap((s: { toolCalls: unknown[] }) => s.toolCalls);
  console.log(`Total tool calls: ${toolCalls.length}`);
}
