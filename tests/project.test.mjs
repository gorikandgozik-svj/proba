import assert from "node:assert/strict";
import test from "node:test";
import { projectName } from "../lib/project.mjs";

test("project metadata is available", () => {
  assert.equal(projectName, "NEXUS");
});
