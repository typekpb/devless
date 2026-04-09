import { Dirent, readFileSync, readdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ORCHESTRATOR_SKILLS_DIR = join(__dirname, "..", ".agents", "skills");

/**
 * Load skills from a .agents/skills directory
 */
function loadSkillsFromDir(dir: string): string[] {
  const skills: string[] = [];

  if (!existsSync(dir)) return skills;

  try {
    const skillDirs = readdirSync(dir, { withFileTypes: true })
      .filter((d: Dirent) => d.isDirectory())
      .map((d: Dirent) => d.name);

    for (const skillDir of skillDirs) {
      const skillPath = join(dir, skillDir, "SKILL.md");
      try {
        const content = readFileSync(skillPath, "utf-8");
        skills.push(content);
      } catch {
        // Skip if SKILL.md doesn't exist
      }
    }
  } catch {
    // Directory doesn't exist or can't be read
  }

  return skills;
}

/**
 * Load orchestrator skills (workflow, issue handling, etc.)
 */
export async function loadOrchestratorSkills(): Promise<string> {
  const skills = loadSkillsFromDir(ORCHESTRATOR_SKILLS_DIR);
  return skills.join("\n\n---\n\n");
}

/**
 * Load target repo skills (coding standards, project conventions)
 */
export async function loadTargetRepoSkills(repoPath: string): Promise<string> {
  const targetSkillsDir = join(repoPath, ".agents", "skills");
  const skills = loadSkillsFromDir(targetSkillsDir);
  return skills.join("\n\n---\n\n");
}
