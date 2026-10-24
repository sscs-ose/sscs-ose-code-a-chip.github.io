// Native Windows bootstrap. No execution-policy changes or global installations.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, renameSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform !== "win32") {
  throw new Error("This bootstrap targets Windows. Other platforms need a local Python/ngspice setup.");
}
if (Number(process.versions.node.split(".")[0]) < 18) {
  throw new Error("Node.js 18 or later is required for this bootstrap.");
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const env = {
  ...process.env,
  UV_PYTHON_INSTALL_DIR: path.join(root, ".tools", "python"),
  UV_PYTHON_BIN_DIR: path.join(root, ".tools", "python-bin"),
  UV_CACHE_DIR: path.join(root, ".tools", "uv-cache"),
  UV_LINK_MODE: "copy",
  PIP_CACHE_DIR: path.join(root, ".tools", "pip-cache"),
};

function run(executable, args) {
  execFileSync(executable, args, { cwd: root, env, stdio: "inherit" });
}

function checkHash(filename, expected) {
  const actual = createHash("sha256").update(readFileSync(filename)).digest("hex");
  if (actual !== expected) {
    throw new Error(`SHA256 mismatch for ${filename}: expected ${expected}, received ${actual}`);
  }
}

function download(url, filename, checksum) {
  if (!existsSync(filename)) {
    const partial = `${filename}.download`;
    run("curl.exe", [
      "--fail", "--location", "--silent", "--show-error", "--retry", "2",
      "--max-time", "240", url, "--output", partial,
    ]);
    checkHash(partial, checksum);
    renameSync(partial, filename);
  }
  checkHash(filename, checksum);
}

for (const directory of ["downloads", "uv", "ngspice"]) {
  mkdirSync(path.join(root, ".tools", directory), { recursive: true });
}
const uvArchive = path.join(root, ".tools", "downloads", "uv-0.12.17.zip");
download(
  "https://github.com/astral-sh/uv/releases/download/0.12.17/uv-x86_64-pc-windows-msvc.zip",
  uvArchive,
  "a252121d5b59398fcb137c6ea448176459a44010f33f67e0072305a637119ca7",
);
const uv = path.join(root, ".tools", "uv", "uv.exe");
if (!existsSync(uv)) {
  run("tar.exe", ["-xf", uvArchive, "-C", path.join(root, ".tools", "uv")]);
}
checkHash(uv, "2019cdf564cb8f749262f5f021cedc75a99abb1c6081227ca340bbcda972611d");

const python = path.join(root, ".venv", "Scripts", "python.exe");
if (!existsSync(python)) {
  run(uv, ["venv", "--python", "3.12.10", ".venv"]);
}
run(python, ["-c", "import sys; assert sys.version_info[:3] == (3, 12, 10), sys.version"]);
run(python, ["-m", "ensurepip"]);
run(python, [
  "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
  "-r", "requirements-windows.lock", "-e", ".",
]);
run(python, ["-m", "pip", "check"]);

const spiceArchive = path.join(root, ".tools", "downloads", "ngspice-47_64.7z");
download(
  "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47_64.7z",
  spiceArchive,
  "59225971bd68cdd1199443649aa4615a9e6d684933f205ab49006a3942518f5a",
);
const spice = path.join(root, ".tools", "ngspice", "Spice64", "bin", "ngspice_con.exe");
if (!existsSync(spice)) {
  run("tar.exe", ["-xf", spiceArchive, "-C", path.join(root, ".tools", "ngspice")]);
}
checkHash(spice, "22d5cae2bd32b2e39157a8d27bf457122f68285b72a9ebefdf41551b628233ab");
run(python, [path.join("scripts", "setup_models.py")]);
run(spice, ["--version"]);
console.log("Setup complete. Run: .\\.venv\\Scripts\\python.exe -m comparator_atlas run --profile quick");
