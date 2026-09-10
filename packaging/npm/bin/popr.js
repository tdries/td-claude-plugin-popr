#!/usr/bin/env node
// Thin shim: npm carries the bash engine in payload/ and hands it the argv.
const { spawnSync } = require("child_process");
const { join } = require("path");
const r = spawnSync(join(__dirname, "..", "payload", "bin", "popr"), process.argv.slice(2), { stdio: "inherit" });
process.exit(r.status === null ? 1 : r.status);
