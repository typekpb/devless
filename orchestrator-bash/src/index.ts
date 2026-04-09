// Bun loads .env automatically
import { handleEvent } from "./handler.js";
import {
  SQSClient,
  ReceiveMessageCommand,
  DeleteMessageCommand,
} from "@aws-sdk/client-sqs";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

interface Config {
  pollInterval: number;
}

function loadConfig(): Config {
  const defaults: Config = { pollInterval: 10 };
  try {
    const configPath = join(__dirname, "..", "config.yml");
    const content = readFileSync(configPath, "utf-8");
    const match = content.match(/^poll_interval:\s*(\d+)$/m);
    if (match) defaults.pollInterval = parseInt(match[1], 10);
  } catch {
    // Use defaults
  }
  return defaults;
}

interface SQSPayload {
  event_type: string;
  repository_full_name: string;
  issue_number: number;
  branch?: string;
}

async function pollSQS(): Promise<void> {
  const queueUrl = process.env.SQS_QUEUE_URL;
  if (!queueUrl) {
    console.error("SQS_QUEUE_URL not set");
    process.exit(1);
  }

  const config = loadConfig();
  const sqs = new SQSClient({ region: process.env.AWS_REGION ?? "eu-central-1" });

  console.log(`==> Starting SQS polling (interval: ${config.pollInterval}s)`);
  console.log(`==> Queue: ${queueUrl}`);

  while (true) {
    try {
      const response = await sqs.send(
        new ReceiveMessageCommand({
          QueueUrl: queueUrl,
          MaxNumberOfMessages: 1,
          WaitTimeSeconds: 20,
          VisibilityTimeout: 600, // 10 minutes
        })
      );

      if (response.Messages && response.Messages.length > 0) {
        const msg = response.Messages[0];
        const payload: SQSPayload = JSON.parse(msg.Body ?? "{}");

        console.log(`\n==> Received message: ${payload.event_type} for ${payload.repository_full_name} #${payload.issue_number}`);

        try {
          await handleEvent({
            eventType: payload.event_type,
            repo: payload.repository_full_name,
            issueNumber: payload.issue_number,
            branch: payload.branch,
          });

          // Delete message on success
          await sqs.send(
            new DeleteMessageCommand({
              QueueUrl: queueUrl,
              ReceiptHandle: msg.ReceiptHandle,
            })
          );
          console.log("==> Message deleted from queue");
        } catch (err) {
          console.error("==> Error handling event:", err);
          // Message will return to queue after visibility timeout
        }
      }
    } catch (err) {
      console.error("==> SQS polling error:", err);
      await new Promise((r) => setTimeout(r, config.pollInterval * 1000));
    }
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // If no args, run in SQS polling mode
  if (args.length === 0) {
    await pollSQS();
    return;
  }

  // CLI mode: <event_type> <repo> <issue_number>
  const [eventType, repo, issueNumber] = args;

  if (!eventType || !repo || !issueNumber) {
    console.error("Usage:");
    console.error("  SQS mode: node dist/index.js");
    console.error("  CLI mode: node dist/index.js <event_type> <repo> <issue_number>");
    console.error("");
    console.error("  event_type: issue, issue_comment, pr_comment, pr_review, pr_issue_comment");
    console.error("  repo: owner/repo (e.g., typekpb/devless-demo)");
    console.error("  issue_number: GitHub issue or PR number");
    process.exit(1);
  }

  await handleEvent({
    eventType,
    repo,
    issueNumber: parseInt(issueNumber, 10),
  });
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
