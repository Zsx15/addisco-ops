#!/usr/bin/env node
// ════════════════════════════════════════════════════════════════════════
//  🏭 APP FACTORY — task.mjs v2.2
//
//  Workflow scalable inspiré de la méthode App Factory de Nicolas Deligne.
//  Generic, configurable, cross-platform (Windows / macOS / Linux).
//
//  Commands:
//    brief               — Briefing journalier complet (read-only)
//    status              — Vue d'ensemble (read-only)
//    doctor              — Diagnostic complet de l'environnement (read-only)
//    log                 — Stats de productivité (read-only)
//    prompt   <id>       — Affiche le prompt à coller dans Claude Code
//    expand   <id>       — Affiche le prompt d'expansion en sous-tâches
//    review   <id>       — Lance typecheck + lint + tests + build (read-only)
//    claim    <id>       — Pull + mark in-progress + commit (write, with GO)
//    ship     <id>       — Stage + commit (write, with GO multi-niveaux)
//    done     <id>       — Mark done + propose push (write, with GO)
//    init-config         — Génère interactivement un .taskrc.json
//
//  Config : .taskrc.json à la racine du repo (voir README).
//  Zero dependencies. Node 20+.
// ════════════════════════════════════════════════════════════════════════

import { execSync, spawnSync } from "node:child_process";
import {
  readFileSync,
  writeFileSync,
  existsSync,
  appendFileSync,
  mkdirSync,
} from "node:fs";
import { dirname } from "node:path";
import { createInterface } from "node:readline";

// ─── Constants ──────────────────────────────────────────────────────────

const SCRIPT_VERSION = "2.2.0";
const CONFIG_FILE = ".taskrc.json";
const LOG_FILE = ".taskmaster/log.jsonl";
const TASKS_FILE = ".taskmaster/tasks/tasks.json";

// ─── ANSI Colors (zero deps) ────────────────────────────────────────────

const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  gray: "\x1b[90m",
};

const ok = (s) => `${C.green}✅${C.reset} ${s}`;
const warn = (s) => `${C.yellow}⚠️  ${s}${C.reset}`;
const err = (s) => `${C.red}❌ ${s}${C.reset}`;
const info = (s) => `${C.blue}ℹ️  ${s}${C.reset}`;
const star = (s) => `${C.cyan}🎯${C.reset} ${s}`;
const fire = (s) => `${C.magenta}🔥${C.reset} ${s}`;
const rocket = (s) => `${C.magenta}🚀${C.reset} ${s}`;
const dim = (s) => `${C.dim}${s}${C.reset}`;
const bold = (s) => `${C.bold}${s}${C.reset}`;
const cyan = (s) => `${C.cyan}${s}${C.reset}`;
const heading = (s) => `\n${C.bold}${C.cyan}━━━ ${s} ━━━${C.reset}\n`;
const arrow = (s) => `${C.dim}↳${C.reset} ${s}`;

// ─── Helpers ────────────────────────────────────────────────────────────

function sh(cmd, opts = {}) {
  return execSync(cmd, {
    stdio: opts.silent ? "pipe" : "inherit",
    encoding: "utf8",
    shell: true,
    ...opts,
  });
}

function shOut(cmd, opts = {}) {
  try {
    return execSync(cmd, {
      stdio: ["ignore", "pipe", "pipe"],
      encoding: "utf8",
      shell: true,
      ...opts,
    }).trim();
  } catch (e) {
    if (opts.allowFail) return "";
    throw e;
  }
}

function shTry(cmd, opts = {}) {
  const r = spawnSync(cmd, {
    stdio: opts.silent ? "pipe" : "inherit",
    encoding: "utf8",
    shell: true,
    ...opts,
  });
  return {
    code: r.status ?? 1,
    stdout: r.stdout ?? "",
    stderr: r.stderr ?? "",
  };
}

function die(msg) {
  console.error(`\n${err(msg)}\n`);
  process.exit(1);
}

function readJSON(path, fallback = null) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJSON(path, data) {
  const dir = dirname(path);
  if (dir && !existsSync(dir)) mkdirSync(dir, { recursive: true });
  writeFileSync(path, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function logEvent(action, taskId, meta = {}) {
  try {
    const dir = dirname(LOG_FILE);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const line =
      JSON.stringify({
        ts: new Date().toISOString(),
        action,
        task: taskId ?? null,
        ...meta,
      }) + "\n";
    appendFileSync(LOG_FILE, line, "utf8");
  } catch {
    // Silently ignore log failures
  }
}

// ─── Interactive prompt (readline) ──────────────────────────────────────

async function ask(question) {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function confirm(question, defaultYes = false) {
  const hint = defaultYes ? "[Y/n]" : "[y/N]";
  const a = (await ask(`${question} ${dim(hint)} `)).toLowerCase();
  if (!a) return defaultYes;
  return a === "y" || a === "yes" || a === "o" || a === "oui";
}

async function choice(question, options) {
  console.log(question);
  options.forEach((opt) => {
    console.log(`  ${C.cyan}[${opt.key}]${C.reset} ${opt.label}`);
  });
  const a = (await ask(`Choix : `)).toLowerCase();
  return options.find((o) => o.key.toLowerCase() === a) ?? null;
}

// ─── Config loading ─────────────────────────────────────────────────────

function loadConfig() {
  if (!existsSync(CONFIG_FILE)) {
    die(
      `Aucun ${CONFIG_FILE} trouvé.\n   ` +
        `Lance ${bold("npm run task init-config")} pour le créer en mode interactif.\n   ` +
        `Ou copie un ${CONFIG_FILE} existant depuis un autre projet.`,
    );
  }
  const cfg = readJSON(CONFIG_FILE);
  if (!cfg) die(`${CONFIG_FILE} est invalide ou illisible. Vérifie le JSON.`);
  return normalizeConfig(cfg);
}

function normalizeConfig(cfg) {
  return {
    version: cfg.version ?? "1.0",
    docs: {
      prd: cfg.docs?.prd ?? "prd.md",
      context: cfg.docs?.context ?? "CLAUDE.md",
    },
    git: {
      mainBranch: cfg.git?.mainBranch ?? "main",
      commitTemplate:
        cfg.git?.commitTemplate ?? "feat(task-{taskId}): {description}",
      coAuthor: cfg.git?.coAuthor ?? null,
    },
    review: {
      targets: normalizeTargets(cfg.review),
    },
    prompt: {
      extraInstructions: cfg.prompt?.extraInstructions ?? [],
    },
  };
}

function normalizeTargets(reviewCfg) {
  if (!reviewCfg) {
    return [{ name: "root", cwd: ".", steps: {} }];
  }
  if (!reviewCfg.targets) {
    return [
      {
        name: "root",
        cwd: ".",
        steps: {
          typecheck: reviewCfg.typecheck,
          lint: reviewCfg.lint,
          format: reviewCfg.format,
          test: reviewCfg.test,
          build: reviewCfg.build,
        },
      },
    ];
  }
  return reviewCfg.targets.map((t) => ({
    name: t.name ?? "target",
    cwd: t.cwd ?? ".",
    steps: t.steps ?? {},
  }));
}

// ─── Git guards ─────────────────────────────────────────────────────────

function getCurrentBranch() {
  return shOut("git rev-parse --abbrev-ref HEAD", { allowFail: true });
}

function ensureOnMain(cfg) {
  const branch = getCurrentBranch();
  if (branch !== cfg.git.mainBranch) {
    die(
      `Tu es sur '${branch}', branche attendue : '${cfg.git.mainBranch}'.\n   ` +
        `Si ta branche par défaut est différente, change ${CONFIG_FILE} (git.mainBranch).\n   ` +
        `Pour switcher : ${bold(`git checkout ${cfg.git.mainBranch}`)}`,
    );
  }
}

function ensureClean() {
  const s = shOut("git status --porcelain", { allowFail: true });
  if (s) {
    die(
      `Working tree non clean. Commit ou stash tes changements avant de continuer.\n   ` +
        `Lance ${bold("git status")} pour voir l'état détaillé.\n   ` +
        `Astuce : ${bold("git stash")} met de côté, ${bold("git stash pop")} récupère.`,
    );
  }
}

function isGitRepo() {
  const r = shTry("git rev-parse --is-inside-work-tree", { silent: true });
  return r.code === 0;
}

// ─── TaskMaster helpers ─────────────────────────────────────────────────

function taskMasterAvailable() {
  const r = shTry("task-master --version", { silent: true });
  return r.code === 0;
}

function getTasksData() {
  return readJSON(TASKS_FILE, null);
}

function findTask(tasks, taskId) {
  if (!tasks) return null;
  const list = tasks.tasks ?? tasks.master?.tasks ?? [];
  const parts = String(taskId).split(".");
  let current = list.find((t) => String(t.id) === parts[0]);
  for (let i = 1; i < parts.length && current; i++) {
    current = (current.subtasks ?? []).find(
      (st) =>
        String(st.id).endsWith(`.${parts[i]}`) || String(st.id) === parts[i],
    );
  }
  return current;
}

function findInProgressTasks(tasks) {
  if (!tasks) return [];
  const list = tasks.tasks ?? tasks.master?.tasks ?? [];
  const out = [];
  function walk(items) {
    for (const t of items) {
      if (t.status === "in-progress") {
        out.push({ id: t.id, title: t.title });
      }
      if (t.subtasks?.length) walk(t.subtasks);
    }
  }
  walk(list);
  return out;
}

function getTaskStatus(taskId) {
  const tasks = getTasksData();
  const t = findTask(tasks, taskId);
  return t?.status ?? null;
}

function commitTaskmaster(msg) {
  if (!existsSync(TASKS_FILE)) {
    console.log(info(`${TASKS_FILE} introuvable — skip commit taskmaster.`));
    return;
  }
  sh(`git add ${TASKS_FILE}`);
  const staged = shOut("git diff --cached --name-only", { allowFail: true });
  if (!staged) {
    console.log(info("Aucun changement taskmaster à committer."));
    return;
  }
  const safeMsg = msg.replace(/"/g, '\\"');
  sh(`git commit -m "${safeMsg}"`);
}

// ─── Changed files ──────────────────────────────────────────────────────

function listChangedFiles() {
  const unstaged = shOut("git diff --name-only", { allowFail: true });
  const staged = shOut("git diff --cached --name-only", { allowFail: true });
  const untracked = shOut("git ls-files --others --exclude-standard", {
    allowFail: true,
  });
  return {
    unstaged: unstaged ? unstaged.split("\n").filter(Boolean) : [],
    staged: staged ? staged.split("\n").filter(Boolean) : [],
    untracked: untracked ? untracked.split("\n").filter(Boolean) : [],
  };
}

// ─── Narrative flair (energetic + pragmatic mix) ────────────────────────

function flairFirstClaim() {
  const msgs = [
    "☕ Premier claim du jour. On chauffe les neurones.",
    "☀️  Première mission. Café en main, focus en tête.",
    "🌅 Top départ de la journée. Une tâche, un focus.",
    "🎬 Action ! Première scène du jour.",
  ];
  return msgs[Math.floor(Math.random() * msgs.length)];
}

function flairLateNight() {
  const msgs = [
    "🌙 Code de nuit — respect. Mais pense à dormir.",
    "🦉 L'heure des artisans. Bon code.",
    "🌃 Encore là ? Discipline absolue. Mais limite à 1-2 tâches.",
  ];
  return msgs[Math.floor(Math.random() * msgs.length)];
}

function flairShipDone() {
  const msgs = [
    "Encore une de pliée. Le système avance.",
    "Commit propre, conscience propre.",
    "Une brique de plus dans le mur.",
    "Done. Suivante.",
  ];
  return msgs[Math.floor(Math.random() * msgs.length)];
}

function flairStreak(days) {
  if (days >= 30) return `🏆 ${days} jours de streak. Légendaire.`;
  if (days >= 14) return `🏆 ${days} jours de streak. Niveau senior atteint.`;
  if (days >= 7) return `🔥 ${days} jours d'affilée. Tu es en feu.`;
  if (days >= 3) return `✨ ${days} jours consécutifs. La régularité paie.`;
  return null;
}

function flairManyDoneToday(count) {
  if (count >= 5) return `🔥 ${count} tâches done aujourd'hui. Tu es dans la zone.`;
  if (count >= 3) return `💪 ${count} tâches done. Belle journée.`;
  return null;
}

function getCurrentHour() {
  return new Date().getHours();
}

function isFirstActionToday() {
  if (!existsSync(LOG_FILE)) return true;
  try {
    const today = new Date().toISOString().slice(0, 10);
    const lines = readFileSync(LOG_FILE, "utf8").trim().split("\n").reverse();
    for (const l of lines) {
      try {
        const e = JSON.parse(l);
        if (e.ts.slice(0, 10) === today) return false;
      } catch {}
    }
    return true;
  } catch {
    return true;
  }
}

function countDoneToday() {
  if (!existsSync(LOG_FILE)) return 0;
  try {
    const today = new Date().toISOString().slice(0, 10);
    let count = 0;
    for (const l of readFileSync(LOG_FILE, "utf8").trim().split("\n")) {
      try {
        const e = JSON.parse(l);
        if (e.action === "done" && e.ts.slice(0, 10) === today) count++;
      } catch {}
    }
    return count;
  } catch {
    return 0;
  }
}

function computeStreak() {
  if (!existsSync(LOG_FILE)) return 0;
  try {
    const days = new Set();
    for (const l of readFileSync(LOG_FILE, "utf8").trim().split("\n")) {
      try {
        const e = JSON.parse(l);
        if (e.action === "done") days.add(e.ts.slice(0, 10));
      } catch {}
    }
    const sorted = [...days].sort().reverse();
    let streak = 0;
    const today = new Date();
    for (let i = 0; i < sorted.length; i++) {
      const expected = new Date(today);
      expected.setDate(today.getDate() - i);
      if (sorted[i] === expected.toISOString().slice(0, 10)) streak++;
      else break;
    }
    return streak;
  } catch {
    return 0;
  }
}

// ─── Next-action suggester (le côté GPS du système) ─────────────────────

function suggestNext(context) {
  console.log();
  console.log(star(bold("Next move :")));
  for (const line of context) {
    if (typeof line === "string") {
      console.log(`   ${line}`);
    } else if (line.cmd) {
      console.log(`   ${bold(line.cmd)}`);
      if (line.hint) console.log(`   ${arrow(dim(line.hint))}`);
    }
  }
  console.log();
}

// ─── COMMAND: status ────────────────────────────────────────────────────

async function cmdStatus() {
  const cfg = loadConfig();
  console.log(heading("STATUS"));

  if (!isGitRepo()) {
    die("Pas dans un repo Git. Lance " + bold("git init") + " d'abord.");
  }

  const branch = getCurrentBranch();
  const branchOk = branch === cfg.git.mainBranch;
  console.log(
    `Branche : ${branchOk ? C.green : C.yellow}${branch}${C.reset} ` +
      `${branchOk ? "" : dim(`(attendue : ${cfg.git.mainBranch})`)}`,
  );

  const { unstaged, staged, untracked } = listChangedFiles();
  const totalChanges = unstaged.length + staged.length + untracked.length;
  if (totalChanges === 0) {
    console.log(`Working tree : ${C.green}clean ✨${C.reset}`);
  } else {
    console.log(
      `Working tree : ${C.yellow}${totalChanges} fichier(s) modifié(s)${C.reset} ` +
        dim(
          `(${untracked.length} nouveaux, ${unstaged.length} modifiés, ${staged.length} stagés)`,
        ),
    );
  }

  const tasks = getTasksData();
  const inProgress = findInProgressTasks(tasks);

  if (inProgress.length === 0) {
    console.log(`\n${dim("Aucune tâche in-progress.")}`);
    if (totalChanges > 0) {
      suggestNext([
        {
          cmd: "git status",
          hint: "Tu as des changements non commités, regarde ce qui traîne.",
        },
      ]);
    } else {
      suggestNext([
        {
          cmd: "task-master list",
          hint: "Voir toutes les tâches du projet.",
        },
        {
          cmd: "task-master next",
          hint: "Voir la prochaine tâche à attaquer.",
        },
      ]);
    }
  } else if (inProgress.length === 1) {
    const t = inProgress[0];
    console.log(`\n${star(`En cours : ${bold(`${t.id} — ${t.title}`)}`)}`);
    if (totalChanges > 0) {
      suggestNext([
        {
          cmd: `npm run task review ${t.id}`,
          hint: "Vérifier ton code (typecheck + lint + tests + build).",
        },
        {
          cmd: `npm run task ship ${t.id}`,
          hint: "Si review OK, commit + push.",
        },
      ]);
    } else {
      suggestNext([
        {
          cmd: `npm run task prompt ${t.id}`,
          hint: "Coller dans Claude Code pour démarrer / continuer.",
        },
      ]);
    }
  } else {
    console.log(`\n${warn(`${inProgress.length} tâches in-progress :`)}`);
    inProgress.forEach((t) => console.log(`  🔵 ${t.id} — ${t.title}`));
    console.log(
      `\n${warn("Une tâche à la fois : termine ou repends celles qui traînent.")}`,
    );
  }

  const streak = computeStreak();
  const streakMsg = flairStreak(streak);
  if (streakMsg) console.log(`\n${streakMsg}`);
  console.log();
}

// ─── COMMAND: doctor ────────────────────────────────────────────────────

async function cmdDoctor() {
  console.log(heading("DOCTOR — Diagnostic complet"));

  let score = 100;
  const deductions = [];

  console.log(`${bold("Environment")} :`);
  const checks = [
    { name: "Node       ", cmd: "node --version", critical: true },
    { name: "npm        ", cmd: "npm --version", critical: true },
    { name: "Git        ", cmd: "git --version", critical: true },
    { name: "task-master", cmd: "task-master --version", critical: false },
    { name: "Claude Code", cmd: "claude --version", critical: false },
  ];
  for (const c of checks) {
    const r = shTry(c.cmd, { silent: true });
    if (r.code === 0) {
      const ver = r.stdout.trim().split("\n")[0];
      console.log(`   ${ok(`${c.name} ${dim(ver)}`)}`);
    } else {
      console.log(`   ${err(`${c.name} introuvable`)}`);
      const cost = c.critical ? 20 : 10;
      score -= cost;
      deductions.push(`${c.name.trim()} manquant (-${cost})`);
    }
  }

  console.log(`\n${bold("Project files")} :`);
  const cfg = readJSON(CONFIG_FILE);
  if (!cfg) {
    console.log(
      `   ${err(
        `${CONFIG_FILE} introuvable — lance ${bold("npm run task init-config")}`,
      )}`,
    );
    score -= 20;
    deductions.push(`${CONFIG_FILE} manquant (-20)`);
  } else {
    console.log(`   ${ok(`${CONFIG_FILE}`)}`);
    const normCfg = normalizeConfig(cfg);
    const prdPath = normCfg.docs.prd;
    const ctxPath = normCfg.docs.context;
    if (existsSync(prdPath)) {
      const size = readFileSync(prdPath, "utf8").length;
      console.log(
        `   ${ok(`${prdPath} ${dim(`(${size.toLocaleString()} chars)`)}`)}`,
      );
    } else {
      console.log(`   ${warn(`${prdPath} introuvable`)}`);
      score -= 15;
      deductions.push(`PRD manquant (-15)`);
    }
    if (existsSync(ctxPath)) {
      const size = readFileSync(ctxPath, "utf8").length;
      const sizeWarn =
        size > 40000
          ? warn(`(${size.toLocaleString()} chars, > 40k ⚠️)`)
          : dim(`(${size.toLocaleString()} chars)`);
      console.log(`   ${ok(`${ctxPath} ${sizeWarn}`)}`);
      if (size > 40000) {
        score -= 5;
        deductions.push("Context file > 40k chars (-5)");
      }
    } else {
      console.log(`   ${warn(`${ctxPath} introuvable`)}`);
      score -= 15;
      deductions.push(`Context manquant (-15)`);
    }
  }

  if (existsSync(TASKS_FILE)) {
    const data = readJSON(TASKS_FILE);
    const list = data?.tasks ?? data?.master?.tasks ?? [];
    let subCount = 0;
    list.forEach((t) => (subCount += (t.subtasks ?? []).length));
    console.log(
      `   ${ok(
        `${TASKS_FILE} ${dim(`(${list.length} tâches, ${subCount} sous-tâches)`)}`,
      )}`,
    );
  } else {
    console.log(`   ${warn(`${TASKS_FILE} introuvable`)}`);
    score -= 10;
    deductions.push("tasks.json manquant (-10)");
  }

  console.log(`\n${bold("Git state")} :`);
  if (isGitRepo()) {
    const branch = getCurrentBranch();
    console.log(`   ${ok(`Branche : ${branch}`)}`);
    const clean = !shOut("git status --porcelain", { allowFail: true });
    console.log(
      `   ${clean ? ok("Working tree clean") : warn("Working tree non clean")}`,
    );
    const remote = shOut("git remote -v", { allowFail: true });
    if (remote) {
      const url = remote.split("\n")[0].split(/\s+/)[1] ?? "";
      console.log(`   ${ok(`Remote : ${dim(url)}`)}`);
    } else {
      console.log(`   ${warn("Aucun remote configuré")}`);
      score -= 5;
      deductions.push("Pas de remote Git (-5)");
    }
    const ahead = shOut("git rev-list --count @{u}..HEAD 2>/dev/null", {
      allowFail: true,
    });
    if (ahead && parseInt(ahead) > 0) {
      console.log(`   ${warn(`${ahead} commit(s) non pushé(s)`)}`);
    } else if (remote) {
      console.log(`   ${ok("Tout est pushé")}`);
    }
  } else {
    console.log(`   ${err("Pas un repo Git")}`);
    score -= 30;
    deductions.push("Pas un repo Git (-30)");
  }

  const scoreColor = score >= 90 ? C.green : score >= 70 ? C.yellow : C.red;
  console.log(
    `\n${bold("Health score")} : ${scoreColor}${C.bold}${score}/100${C.reset}`,
  );
  if (deductions.length) {
    console.log(dim("Détail :"));
    deductions.forEach((d) => console.log(dim(`   • ${d}`)));
  }

  // Suggestion next
  if (score >= 90) {
    suggestNext([
      `${ok("Tout est en ordre.")}`,
      {
        cmd: "npm run task status",
        hint: "Voir l'état du projet.",
      },
    ]);
  } else if (score >= 70) {
    suggestNext([
      `${warn("Quelques alertes mineures. Regarde les déductions ci-dessus.")}`,
    ]);
  } else {
    suggestNext([
      `${err("Plusieurs problèmes critiques. Corrige avant de continuer.")}`,
      {
        cmd: "npm run task init-config",
        hint: "Si .taskrc.json est manquant.",
      },
    ]);
  }
}

// ─── COMMAND: log ───────────────────────────────────────────────────────

async function cmdLog() {
  console.log(heading("LOG — Stats de productivité"));

  if (!existsSync(LOG_FILE)) {
    console.log(
      info(
        `Aucun log encore. Lance quelques tâches pour générer ${LOG_FILE}.`,
      ),
    );
    return;
  }

  const lines = readFileSync(LOG_FILE, "utf8").trim().split("\n");
  const events = lines
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  if (events.length === 0) {
    console.log(info("Aucun event valide dans le log."));
    return;
  }

  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const recent = events.filter((e) => new Date(e.ts) >= sevenDaysAgo);

  const done7d = recent.filter((e) => e.action === "done");
  const ship7d = recent.filter((e) => e.action === "ship");
  const claim7d = recent.filter((e) => e.action === "claim");

  console.log(`${bold("7 derniers jours")} :`);
  console.log(`   Tâches done     : ${cyan(done7d.length)}`);
  console.log(`   Tâches shipped  : ${cyan(ship7d.length)}`);
  console.log(`   Tâches claimed  : ${cyan(claim7d.length)}`);

  const durations = computeTaskDurations(events);
  if (durations.length > 0) {
    const avg = durations.reduce((a, b) => a + b.minutes, 0) / durations.length;
    const longest = [...durations]
      .sort((a, b) => b.minutes - a.minutes)
      .slice(0, 3);
    console.log(`   Durée moyenne   : ${cyan(formatDuration(Math.round(avg)))}`);

    if (longest.length > 0) {
      console.log(`\n${bold("Top 3 plus longues tâches")} :`);
      longest.forEach((d) => {
        const flag = d.minutes > 180 ? warn(" ⚠️  scope à analyser") : "";
        console.log(
          `   ${d.task.padEnd(8)} ${C.dim}${formatDuration(d.minutes)}${C.reset}${flag}`,
        );
      });
    }
  }

  const streak = computeStreak();
  if (streak > 0) {
    console.log(
      `\n${fire(
        `Streak actuel : ${bold(`${streak} jour${streak > 1 ? "s" : ""}`)}`,
      )}`,
    );
  }

  const doneToday = countDoneToday();
  const todayMsg = flairManyDoneToday(doneToday);
  if (todayMsg) console.log(todayMsg);
  console.log();
}

function computeTaskDurations(events) {
  const claims = new Map();
  const out = [];
  for (const e of events) {
    if (e.action === "claim" && e.task) {
      claims.set(e.task, new Date(e.ts));
    } else if (e.action === "done" && e.task && claims.has(e.task)) {
      const start = claims.get(e.task);
      const minutes = (new Date(e.ts) - start) / 60000;
      out.push({ task: e.task, minutes: Math.round(minutes) });
      claims.delete(e.task);
    }
  }
  return out;
}

function formatDuration(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  return `${h}h${String(m).padStart(2, "0")}`;
}

// ─── COMMAND: brief (briefing journalier) ───────────────────────────────

async function cmdBrief() {
  const cfg = loadConfig();
  console.log(heading("BRIEF — Briefing journalier"));

  const hour = getCurrentHour();
  let greeting = "Bonjour";
  if (hour < 5) greeting = "Salut, encore là à cette heure";
  else if (hour < 12) greeting = "☀️  Bonjour";
  else if (hour < 18) greeting = "👋 Salut";
  else if (hour < 22) greeting = "🌆 Bonsoir";
  else greeting = "🌙 Salut, code de nuit";

  console.log(`${bold(greeting)}, voici ton point de la journée.\n`);

  // ── 1. État Git
  if (!isGitRepo()) {
    die("Pas dans un repo Git.");
  }
  const branch = getCurrentBranch();
  const branchOk = branch === cfg.git.mainBranch;
  const { unstaged, staged, untracked } = listChangedFiles();
  const totalChanges = unstaged.length + staged.length + untracked.length;

  console.log(`${bold("📍 Où tu en es")}`);
  console.log(`   Branche : ${branchOk ? C.green : C.yellow}${branch}${C.reset}`);
  if (totalChanges === 0) {
    console.log(`   Working tree : ${C.green}clean ✨${C.reset}`);
  } else {
    console.log(
      `   Working tree : ${C.yellow}${totalChanges} fichier(s) modifié(s)${C.reset}`,
    );
  }

  // ── 2. Tâches in-progress
  const tasks = getTasksData();
  const inProgress = findInProgressTasks(tasks);
  if (inProgress.length === 0) {
    console.log(`   ${dim("Aucune tâche in-progress.")}`);
  } else if (inProgress.length === 1) {
    const t = inProgress[0];
    console.log(`   ${star(`En cours : ${bold(`${t.id} — ${t.title}`)}`)}`);
  } else {
    console.log(`   ${warn(`${inProgress.length} tâches in-progress`)}`);
  }

  // ── 3. Stats de la semaine
  console.log(`\n${bold("📊 Ta semaine")}`);
  if (existsSync(LOG_FILE)) {
    const lines = readFileSync(LOG_FILE, "utf8").trim().split("\n");
    const events = lines
      .map((l) => {
        try {
          return JSON.parse(l);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const recent = events.filter((e) => new Date(e.ts) >= sevenDaysAgo);
    const done7d = recent.filter((e) => e.action === "done").length;
    const ship7d = recent.filter((e) => e.action === "ship").length;
    console.log(`   ${done7d} tâche(s) done, ${ship7d} shipped`);

    const streak = computeStreak();
    if (streak > 0) {
      console.log(`   ${fire(`Streak : ${bold(`${streak} jour${streak > 1 ? "s" : ""}`)}`)}`);
    }
    const doneToday = countDoneToday();
    if (doneToday > 0) {
      console.log(`   Aujourd'hui : ${cyan(doneToday)} done`);
    }
  } else {
    console.log(dim("   Pas encore de stats. Lance des tâches pour les générer."));
  }

  // ── 4. Health check rapide
  console.log(`\n${bold("🩺 Santé du projet")}`);
  let health = 100;
  if (!existsSync(cfg.docs.prd)) {
    console.log(`   ${err(`PRD manquant : ${cfg.docs.prd}`)}`);
    health -= 30;
  } else {
    console.log(`   ${ok(`PRD présent`)}`);
  }
  if (!existsSync(cfg.docs.context)) {
    console.log(`   ${err(`Contexte manquant : ${cfg.docs.context}`)}`);
    health -= 20;
  } else {
    console.log(`   ${ok(`Contexte présent`)}`);
  }
  if (!existsSync(TASKS_FILE)) {
    console.log(`   ${warn(`tasks.json manquant`)}`);
    health -= 20;
  } else {
    console.log(`   ${ok(`tasks.json présent`)}`);
  }

  if (health < 70) {
    console.log(`   ${err(`Santé basse (${health}/100)`)}`);
    console.log(`   ${arrow(dim("Lance " + bold("npm run task doctor") + " pour le détail"))}`);
  } else {
    console.log(`   ${ok(`Santé : ${health}/100`)}`);
  }

  // ── 5. Suggestion de prochaine action
  console.log(`\n${bold("🎯 Ce que je te recommande")}`);
  if (totalChanges > 0 && inProgress.length > 0) {
    const t = inProgress[0];
    console.log(`   Tu as du code en cours sur ${bold(t.id)}.`);
    suggestNext([
      {
        cmd: `npm run task review ${t.id}`,
        hint: "Vérifier ton code avant ship.",
      },
    ]);
  } else if (inProgress.length === 1) {
    const t = inProgress[0];
    console.log(`   Tu as une tâche en cours mais pas de code modifié.`);
    suggestNext([
      {
        cmd: `npm run task prompt ${t.id}`,
        hint: "Reprends avec Claude Code.",
      },
    ]);
  } else if (inProgress.length > 1) {
    suggestNext([
      `${warn("Tu as plusieurs tâches in-progress.")}`,
      `${arrow(dim("Une seule à la fois : termine ou repends celles qui traînent."))}`,
    ]);
  } else {
    suggestNext([
      {
        cmd: "task-master next",
        hint: "Voir quelle tâche attaquer maintenant.",
      },
    ]);
  }
}

// ─── COMMAND: prompt ────────────────────────────────────────────────────

async function cmdPrompt(taskId) {
  const cfg = loadConfig();
  const extra = cfg.prompt.extraInstructions.length
    ? "\n\nInstructions additionnelles :\n" +
      cfg.prompt.extraInstructions.map((s) => `- ${s}`).join("\n")
    : "";

  console.log(heading(`PROMPT — Task ${taskId}`));
  console.log(
    dim(
      "Copie-colle le bloc ci-dessous dans Claude Code.\n" +
        "Claude lira la tâche, le PRD et le CLAUDE.md, puis te présentera\n" +
        "un plan en 7 points AVANT toute action.\n",
    ),
  );
  console.log(`${C.cyan}${"═".repeat(70)}${C.reset}\n`);

  console.log(
    `Lis ${cfg.docs.context} en entier.
Lis ${cfg.docs.prd} en entier.
Exécute : task-master show ${taskId}

Établis d'abord la baseline tests pour pouvoir détecter les régressions.
Note les échecs pré-existants éventuels. Ne pas continuer si tu ne peux
pas établir la baseline.

Résume en suivant ce format EXACT (les 7 points) :

1. Objectif
2. Contraintes PRD (§ concernés)
3. Fichiers à lire (liste les chemins exacts AVANT de les lire)
4. Deliverables (fichiers à créer/modifier)
5. Risques archi + invariants impactés
6. Tests à prévoir
7. Sous-tâches dans l'ordre (si applicable)

Suis Reading Protocol + Semi-Auto Mode strictement.
NE CODE RIEN sans mon GO explicite après avoir présenté ce plan.${extra}`,
  );

  console.log(`\n${C.cyan}${"═".repeat(70)}${C.reset}`);

  suggestNext([
    `${arrow("Colle dans Claude Code, lis son plan, valide ou ajuste.")}`,
    `${arrow("Quand Claude a fini de coder, reviens ici :")}`,
    {
      cmd: `npm run task review ${taskId}`,
      hint: "Vérifier le code (typecheck + lint + tests + build).",
    },
    {
      cmd: `npm run task ship ${taskId}`,
      hint: "Si review OK, commit + push.",
    },
  ]);
}

// ─── COMMAND: expand ────────────────────────────────────────────────────

async function cmdExpand(taskId) {
  const cfg = loadConfig();
  console.log(heading(`EXPAND — Task ${taskId}`));
  console.log(
    dim(
      "Copie-colle le bloc ci-dessous dans Claude Code pour décomposer\n" +
        "la tâche en sous-tâches. Claude proposera un plan ; tu valides\n" +
        "AVANT qu'il écrive dans tasks.json.\n",
    ),
  );
  console.log(`${C.cyan}${"═".repeat(70)}${C.reset}\n`);

  console.log(
    `Lis ${cfg.docs.context} en entier.
Lis ${cfg.docs.prd} en entier.
Exécute : task-master show ${taskId}

Propose un découpage de cette tâche en 3 à 7 sous-tâches précises.

Pour CHAQUE sous-tâche, donne :
  - id (ex : ${taskId}.1, ${taskId}.2, ...)
  - title (clair, actionnable, verbe + objet)
  - description (1-2 phrases)
  - priority (high / medium / low)
  - dependencies (ids des sous-tâches prérequises dans ce découpage)
  - deliverables (fichiers à créer/modifier)
  - tests à prévoir (cas obligatoires selon CLAUDE.md §TESTING_REQUIREMENTS)

Présente d'abord ton plan dans un tableau clair pour validation.
N'écris RIEN dans tasks.json sans mon GO explicite.

Une fois validé, utilise les commandes task-master appropriées
(task-master add-subtask, etc.) pour créer les sous-tâches.`,
  );

  console.log(`\n${C.cyan}${"═".repeat(70)}${C.reset}`);

  suggestNext([
    `${arrow("Colle dans Claude Code, valide le découpage proposé.")}`,
    `${arrow("Une fois les sous-tâches créées, vérifie :")}`,
    {
      cmd: "task-master list",
      hint: "Voir l'arbre complet des tâches.",
    },
    {
      cmd: `npm run task claim ${taskId}.1`,
      hint: "Démarrer la première sous-tâche.",
    },
  ]);
}

// ─── COMMAND: review ────────────────────────────────────────────────────

async function cmdReview(taskId) {
  const cfg = loadConfig();
  console.log(heading(`REVIEW — Task ${taskId}`));

  let failed = false;
  let failedStep = null;
  for (const target of cfg.review.targets) {
    const steps = target.steps;
    const stepEntries = Object.entries(steps).filter(([, cmd]) => cmd);
    if (stepEntries.length === 0) continue;

    console.log(
      `${bold(`📂 Target : ${target.name}`)} ${dim(`(${target.cwd})`)}\n`,
    );
    const cwdPrefix =
      target.cwd && target.cwd !== "." ? `cd ${target.cwd} && ` : "";

    let stepNum = 1;
    for (const [name, cmd] of stepEntries) {
      const label = `[${stepNum}/${stepEntries.length}] ${name.padEnd(11)}`;
      process.stdout.write(`   ${label} ${C.dim}Running...${C.reset}`);
      const start = Date.now();
      const r = shTry(`${cwdPrefix}${cmd}`, { silent: true });
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      process.stdout.write("\r\x1b[K");
      if (r.code === 0) {
        console.log(`   ${label} ${ok(`OK ${dim(`(${elapsed}s)`)}`)}`);
      } else {
        console.log(`   ${label} ${err(`FAIL ${dim(`(${elapsed}s)`)}`)}`);
        failed = true;
        failedStep = name;
        const lines = (r.stderr || r.stdout).trim().split("\n").slice(-15);
        lines.forEach((l) => console.log(`      ${dim(l)}`));
        break;
      }
      stepNum++;
    }
    console.log();
    if (failed) break;
  }

  if (failed) {
    console.log(err(bold("Review failed.")));
    logEvent("review", taskId, { result: "fail", step: failedStep });

    const hints = {
      typecheck: "Erreurs TypeScript — relis les diagnostics au-dessus.",
      lint: "Erreurs ESLint — souvent fixables avec `npm run lint -- --fix`.",
      format: "Format non conforme — `npm run format` corrige automatiquement.",
      test: "Tests qui échouent — lance ton runner en mode focus pour itérer.",
      build: "Erreur de build — souvent une dépendance ou un import cassé.",
    };
    suggestNext([
      `${arrow(hints[failedStep] || "Regarde les logs ci-dessus pour identifier le souci.")}`,
      `${arrow("Une fois fixé, relance :")}`,
      {
        cmd: `npm run task review ${taskId}`,
      },
    ]);
    process.exit(1);
  } else {
    console.log(ok(bold("Review passed !")));
    logEvent("review", taskId, { result: "pass" });
    suggestNext([
      `${arrow("Code propre, tests verts. Tu peux ship en confiance.")}`,
      {
        cmd: `npm run task ship ${taskId}`,
        hint: "Stage + commit + push (3 GO consécutifs).",
      },
    ]);
  }
}

// ─── COMMAND: claim ─────────────────────────────────────────────────────

async function cmdClaim(taskId) {
  const cfg = loadConfig();
  console.log(heading(`CLAIM — Task ${taskId}`));

  const tasks = getTasksData();
  const inProgress = findInProgressTasks(tasks).filter(
    (t) => String(t.id) !== String(taskId),
  );

  if (inProgress.length > 0) {
    console.log(warn("Tu as déjà des tâches in-progress :"));
    inProgress.forEach((t) => console.log(`   🔵 ${t.id} — ${t.title}`));
    console.log(
      `\n${dim(
        "Principe App Factory : une tâche à la fois. Multitasking = perte de focus.",
      )}\n`,
    );

    const c = await choice("Que veux-tu faire ?", [
      { key: "c", label: "Continue avec les tâches existantes (annule ce claim)" },
      { key: "s", label: "Switch : remet les autres en 'pending' et claim celle-ci" },
      { key: "f", label: "Force : claim en plus (NON recommandé)" },
    ]);
    if (!c || c.key === "c") {
      console.log(info("Claim annulé."));
      return;
    }
    if (c.key === "s") {
      for (const t of inProgress) {
        sh(`task-master set-status --id=${t.id} --status=pending`);
      }
    }
  }

  ensureOnMain(cfg);
  ensureClean();

  console.log(info("Pulling latest..."));
  sh("git pull --rebase");

  console.log(info(`Marquage in-progress de ${taskId}...`));
  if (taskMasterAvailable()) {
    sh(`task-master set-status --id=${taskId} --status=in-progress`);
  } else {
    console.log(warn("task-master non disponible — skip set-status."));
  }
  commitTaskmaster(`taskmaster: mark ${taskId} as in-progress`);

  logEvent("claim", taskId);

  const hour = getCurrentHour();
  let flair = "";
  if (isFirstActionToday()) flair = flairFirstClaim();
  else if (hour >= 22 || hour < 5) flair = flairLateNight();

  console.log(`\n${ok(bold(`Task ${taskId} verrouillée. À toi de jouer !`))}`);
  if (flair) console.log(`\n${flair}`);

  suggestNext([
    {
      cmd: `npm run task prompt ${taskId}`,
      hint: "Génère le prompt à coller dans Claude Code.",
    },
    `${arrow(dim("Claude lira la tâche, le PRD, le CLAUDE.md."))}`,
    `${arrow(dim("Il présentera un plan en 7 points. Tu valides → il code."))}`,
  ]);
}

// ─── COMMAND: ship ──────────────────────────────────────────────────────

async function cmdShip(taskId) {
  const cfg = loadConfig();
  console.log(heading(`SHIP — Task ${taskId}`));

  ensureOnMain(cfg);

  // Guard : warn if taskId is not in-progress
  const currentStatus = getTaskStatus(taskId);
  if (currentStatus && currentStatus !== "in-progress") {
    console.log(
      warn(
        `Task ${taskId} a le statut "${currentStatus}" (pas "in-progress").\n` +
          `   Tu n'as probablement pas fait ${bold(`npm run task claim ${taskId}`)} avant de coder.`,
      ),
    );
    const cont = await confirm("Continuer quand même ?", false);
    if (!cont) {
      console.log(info("Ship annulé."));
      return;
    }
  }

  const { unstaged, staged, untracked } = listChangedFiles();
  const toCommit = [...new Set([...untracked, ...unstaged])].filter(
    (f) => !f.endsWith("tasks.json") && !f.endsWith("package-lock.json"),
  );

  console.log(`${bold("📂 Changements détectés")} :`);
  if (toCommit.length === 0 && staged.length === 0) {
    console.log(`   ${dim("(aucun)")}`);
    console.log(`\n${warn("Rien à ship. Code d'abord, puis reviens.")}`);
    suggestNext([
      {
        cmd: `npm run task prompt ${taskId}`,
        hint: "Si tu n'as pas encore lancé Claude Code sur cette tâche.",
      },
    ]);
    return;
  }
  toCommit.forEach((f) => console.log(`   ${C.yellow}M${C.reset} ${f}`));
  staged.forEach((f) =>
    console.log(`   ${C.green}+${C.reset} ${f} ${dim("(déjà stagé)")}`),
  );

  const all = [...unstaged, ...staged, ...untracked];
  if (all.some((f) => f.endsWith("package-lock.json"))) {
    console.log(
      `\n${warn("package-lock.json modifié. Si non voulu, revert avant ship.")}`,
    );
  }

  console.log();
  const proceed1 = await confirm("Stager tous ces fichiers et continuer ?", true);
  if (!proceed1) {
    console.log(info("Ship annulé. Aucun changement appliqué."));
    return;
  }
  if (toCommit.length > 0) {
    const safe = toCommit.map((f) => `"${f}"`).join(" ");
    sh(`git add ${safe}`);
  }

  console.log();
  const description = await ask(`${bold("Description courte du commit :")} `);
  if (!description.trim()) {
    console.log(info("Description vide — ship annulé."));
    return;
  }
  const subjectTemplate = cfg.git.commitTemplate;
  const subject = subjectTemplate
    .replace("{taskId}", taskId)
    .replace("{description}", description.trim());

  console.log(`\n${bold("✍️  Commit proposé")} :`);
  console.log(`   ${cyan(subject)}`);
  if (cfg.git.coAuthor) {
    console.log(`   ${dim(`Co-Authored-By: ${cfg.git.coAuthor}`)}`);
  }
  console.log();

  const c = await choice("Que faire ?", [
    { key: "y", label: "Commit avec ce message" },
    { key: "d", label: "Voir le diff stagé avant de décider" },
    { key: "n", label: "Annule (fichiers restent stagés)" },
  ]);
  if (!c || c.key === "n") {
    console.log(info("Ship annulé. Les fichiers sont stagés, à toi de voir."));
    return;
  }
  if (c.key === "d") {
    sh("git diff --staged");
    const go = await confirm("\nCommit maintenant ?", true);
    if (!go) {
      console.log(info("Ship annulé. Les fichiers sont stagés."));
      return;
    }
  }

  const msgFile = ".git/COMMIT_EDITMSG_APPFACTORY";
  const fullMsg = cfg.git.coAuthor
    ? `${subject}\n\nCo-Authored-By: ${cfg.git.coAuthor}\n`
    : `${subject}\n`;
  writeFileSync(msgFile, fullMsg, "utf8");
  sh(`git commit -F ${msgFile}`);

  console.log(`\n${ok(bold("Commit créé."))}`);
  logEvent("ship", taskId, { description });

  console.log();
  const c2 = await choice("Et maintenant ?", [
    { key: "a", label: "Done + push automatique" },
    { key: "d", label: "Done seulement (push plus tard)" },
    { key: "n", label: "Rien faire (je gère manuellement)" },
  ]);
  if (!c2 || c2.key === "n") {
    suggestNext([
      {
        cmd: `npm run task done ${taskId}`,
        hint: "Marquer la tâche done.",
      },
      {
        cmd: "git push",
        hint: "Pousser sur le remote.",
      },
    ]);
    return;
  }
  if (taskMasterAvailable()) {
    sh(`task-master set-status --id=${taskId} --status=done`);
  }
  commitTaskmaster(`taskmaster: mark ${taskId} as done`);
  logEvent("done", taskId);

  if (c2.key === "a") {
    sh("git push");
    console.log(`\n${rocket(bold("Pushed !"))}`);
  } else {
    console.log(`\n${ok("Marked done. Tu pushras quand tu veux.")}`);
  }

  const flair = flairShipDone();
  console.log(`\n${dim(flair)}`);

  suggestNext([
    {
      cmd: "task-master next",
      hint: "Voir la prochaine tâche à attaquer.",
    },
  ]);
}

// ─── COMMAND: done ──────────────────────────────────────────────────────

async function cmdDone(taskId) {
  const cfg = loadConfig();
  console.log(heading(`DONE — Task ${taskId}`));

  ensureOnMain(cfg);

  const { unstaged } = listChangedFiles();
  if (unstaged.length > 0) {
    die(
      `Tu as des changements unstaged. Commit d'abord (${bold(
        `npm run task ship ${taskId}`,
      )}).`,
    );
  }

  if (taskMasterAvailable()) {
    sh(`task-master set-status --id=${taskId} --status=done`);
  }
  commitTaskmaster(`taskmaster: mark ${taskId} as done`);
  logEvent("done", taskId);

  console.log(`\n${ok(bold(`Task ${taskId} marked done.`))}`);

  const go = await confirm(`\nPusher maintenant ?`, true);
  if (go) {
    sh("git push");
    console.log(`\n${rocket(bold("Pushed !"))}`);
  } else {
    console.log(info(`Pense à ${bold("git push")} quand tu es prêt.`));
  }

  suggestNext([
    {
      cmd: "task-master next",
      hint: "Voir la prochaine tâche à attaquer.",
    },
  ]);
}

// ─── COMMAND: init-config ───────────────────────────────────────────────

async function cmdInitConfig() {
  console.log(heading("INIT-CONFIG — Création de .taskrc.json"));

  if (existsSync(CONFIG_FILE)) {
    const overwrite = await confirm(
      `${CONFIG_FILE} existe déjà. Écraser ?`,
      false,
    );
    if (!overwrite) {
      console.log(info("Annulé. Le fichier existant est préservé."));
      return;
    }
  }

  console.log(
    dim("Quelques questions pour scaffolder ta config (~1 min).\n"),
  );

  const prd =
    (await ask(`Nom du fichier PRD ? ${dim("(défaut: prd.md)")} `)) || "prd.md";
  const context =
    (await ask(
      `Nom du fichier de contexte IA ? ${dim("(défaut: CLAUDE.md)")} `,
    )) || "CLAUDE.md";
  const mainBranch =
    (await ask(`Branche Git principale ? ${dim("(défaut: main)")} `)) ||
    "main";

  const stackChoice = await choice(`\nQuel est ton stack principal ?`, [
    { key: "1", label: "Node.js / TypeScript (npm scripts)", value: "node" },
    { key: "2", label: "Python (pytest, ruff, mypy)", value: "python" },
    { key: "3", label: "Go (go test, go vet)", value: "go" },
    { key: "4", label: "Rust (cargo)", value: "rust" },
    { key: "5", label: "Custom (j'édite à la main après)", value: "custom" },
  ]);
  const stack = stackChoice?.value ?? "node";

  const review = buildReviewForStack(stack);

  const isMonorepo = await confirm(
    `\nC'est un monorepo (plusieurs cibles backend/frontend) ?`,
    false,
  );

  let reviewConfig;
  if (isMonorepo) {
    const targets = [];
    let i = 1;
    while (true) {
      const name = await ask(
        `\nNom de la cible #${i} ? ${dim("(ex: backend, vide pour finir)")} `,
      );
      if (!name) break;
      const cwd =
        (await ask(`   Dossier de la cible ? ${dim("(défaut: " + name + ")")} `)) ||
        name;
      targets.push({ name, cwd, steps: { ...review } });
      i++;
    }
    reviewConfig = { targets };
  } else {
    reviewConfig = review;
  }

  const useCoAuthor = await confirm(
    `\nAjouter Claude comme Co-Author dans les commits ?`,
    true,
  );
  const coAuthor = useCoAuthor ? "Claude <noreply@anthropic.com>" : null;

  const config = {
    $schema: "./taskrc.schema.json",
    version: "1.0",
    docs: { prd, context },
    git: {
      mainBranch,
      commitTemplate: "feat(task-{taskId}): {description}",
      coAuthor,
    },
    review: reviewConfig,
    prompt: { extraInstructions: [] },
  };

  writeJSON(CONFIG_FILE, config);
  console.log(`\n${ok(bold(`${CONFIG_FILE} créé !`))}`);
  console.log(dim("Tu peux l'éditer manuellement à tout moment."));

  const hasPrd = existsSync(prd);
  const hasContext = existsSync(context);

  if (!hasPrd) {
    suggestNext([
      `${arrow("Étape suivante : rédige ton PRD avec une IA.")}`,
      `${arrow(dim("Ouvre ChatGPT ou claude.ai, brainstorme ton produit."))}`,
      `${arrow(dim(`Sauvegarde le résultat dans ${prd}.`))}`,
    ]);
  } else if (!hasContext) {
    suggestNext([
      `${arrow("Étape suivante : génère ton CLAUDE.md avec Claude Code.")}`,
      {
        cmd: "claude",
        hint: `Demande-lui : "Lis ${prd} et génère ${context} selon App Factory."`,
      },
    ]);
  } else {
    suggestNext([
      `${arrow("Tout est prêt. Lance le diagnostic complet :")}`,
      {
        cmd: "npm run task doctor",
      },
    ]);
  }
}

function buildReviewForStack(stack) {
  switch (stack) {
    case "python":
      return {
        typecheck: "mypy .",
        lint: "ruff check .",
        format: "ruff format --check .",
        test: "pytest",
        build: "",
      };
    case "go":
      return {
        typecheck: "go vet ./...",
        lint: "golangci-lint run",
        format: "gofmt -l .",
        test: "go test ./...",
        build: "go build ./...",
      };
    case "rust":
      return {
        typecheck: "cargo check",
        lint: "cargo clippy -- -D warnings",
        format: "cargo fmt -- --check",
        test: "cargo test",
        build: "cargo build",
      };
    case "custom":
      return { typecheck: "", lint: "", format: "", test: "", build: "" };
    case "node":
    default:
      return {
        typecheck: "npx tsc --noEmit",
        lint: "npm run lint",
        format: "npm run format -- --check",
        test: "npm run test",
        build: "npm run build",
      };
  }
}

// ─── Help ───────────────────────────────────────────────────────────────

function printHelp() {
  console.log(`
${bold(`🏭 App Factory task.mjs v${SCRIPT_VERSION}`)}

${bold("Usage")} :
  npm run task <command> [taskId]

${bold("Read-only commands")} ${dim("(zero risque)")} :
  ${cyan("brief")}                 Briefing journalier (où tu en es + recommandation)
  ${cyan("status")}                Vue d'ensemble (tâche en cours, Git, streak)
  ${cyan("doctor")}                Diagnostic environnement + projet
  ${cyan("log")}                   Stats de productivité (7 derniers jours)
  ${cyan("prompt")}   <id>         Affiche le prompt pour Claude Code (7 points)
  ${cyan("expand")}   <id>         Affiche le prompt d'expansion en sous-tâches
  ${cyan("review")}   <id>         Lance typecheck + lint + tests + build

${bold("Write commands")} ${dim("(avec confirmation GO)")} :
  ${cyan("claim")}    <id>         Pull + mark in-progress + commit taskmaster
  ${cyan("ship")}     <id>         Stage + commit (3 GO consécutifs)
  ${cyan("done")}     <id>         Mark done + propose push

${bold("Setup")} :
  ${cyan("init-config")}           Scaffold interactif de ${CONFIG_FILE}
  ${cyan("help")}                  Affiche cette aide

${bold("Workflow type")} :
  ${dim("1.")} npm run task claim 18.3
  ${dim("2.")} npm run task prompt 18.3   ${dim("# colle dans Claude Code")}
  ${dim("3.")} ${dim("[Claude propose plan en 7 points → tu valides → il code]")}
  ${dim("4.")} npm run task review 18.3
  ${dim("5.")} npm run task ship 18.3

${bold("Commandes task-master utiles")} :
  ${cyan("task-master list")}              Liste toutes les tâches
  ${cyan("task-master next")}              Prochaine tâche à attaquer
  ${cyan("task-master show <id>")}         Détail d'une tâche/sous-tâche

${dim("Documentation complète : voir APP_FACTORY_QUICKSTART.md")}
`);
}

// ─── Main ───────────────────────────────────────────────────────────────

const [, , rawAction, taskId] = process.argv;
const action = (rawAction ?? "").toLowerCase();

if (!action || action === "help" || action === "--help" || action === "-h") {
  printHelp();
  process.exit(action ? 0 : 1);
}

if (action === "version" || action === "--version" || action === "-v") {
  console.log(`task.mjs v${SCRIPT_VERSION}`);
  process.exit(0);
}

const commands = {
  status: () => cmdStatus(),
  doctor: () => cmdDoctor(),
  log: () => cmdLog(),
  brief: () => cmdBrief(),
  "init-config": () => cmdInitConfig(),
};

const taskCommands = {
  prompt: (id) => cmdPrompt(id),
  expand: (id) => cmdExpand(id),
  review: (id) => cmdReview(id),
  claim: (id) => cmdClaim(id),
  ship: (id) => cmdShip(id),
  done: (id) => cmdDone(id),
};

(async () => {
  try {
    if (commands[action]) {
      await commands[action]();
    } else if (taskCommands[action]) {
      if (!taskId)
        die(
          `L'action '${action}' nécessite un taskId.\n   Ex: npm run task ${action} 18.3`,
        );
      await taskCommands[action](taskId);
    } else {
      die(
        `Action inconnue : '${action}'.\n   Lance ${bold(
          "npm run task help",
        )} pour la liste.`,
      );
    }
  } catch (e) {
    if (e && e.status !== undefined) {
      process.exit(e.status);
    }
    die(`Erreur inattendue : ${e?.message ?? e}`);
  }
})();
