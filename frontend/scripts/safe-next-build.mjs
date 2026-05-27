import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";

const env = { ...process.env };
const isolateDockerDevBuild = env.BIDALS_DOCKER_DEV === "1";
const generatedConfigFiles = ["next-env.d.ts", "tsconfig.json"];
const snapshots = new Map();

function restoreGeneratedConfigFiles() {
  for (const [file, contents] of snapshots) {
    writeFileSync(file, contents);
  }
}

if (isolateDockerDevBuild) {
  env.NODE_ENV = "production";
  env.NEXT_DIST_DIR = env.NEXT_DIST_DIR || ".next-build";
  for (const file of generatedConfigFiles) {
    if (existsSync(file)) {
      snapshots.set(file, readFileSync(file, "utf8"));
    }
  }
  console.log(
    `Using ${env.NEXT_DIST_DIR} for this one-off build so the dev .next volume remains untouched.`,
  );
}

const result = spawnSync("next", ["build"], {
  env,
  shell: process.platform === "win32",
  stdio: "inherit",
});

if (result.error) {
  restoreGeneratedConfigFiles();
  console.error(result.error.message);
  process.exit(1);
}

restoreGeneratedConfigFiles();

process.exit(result.status ?? 1);
