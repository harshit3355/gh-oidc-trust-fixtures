"""Run each scanner over fixtures/ and score its verdicts against fixtures/labels.json.

Usage (Linux/WSL, after scripts/setup.sh):  python3 eval/run.py
Writes results/results.json and results/report.md. Exits 1 if the proposed configuration
(checkov + PR #7610 + CKV_GHOIDC_1) has any false positive or misses a security/apply-failure case.
"""
import datetime
import json
import os
import platform
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
TOOLS = Path(os.environ.get("TOOLS_DIR", Path.home() / ".cache/gh-oidc-trust-fixtures"))
BUILTIN = "CKV_AWS_358,CKV_AWS_393,CKV_AZURE_249"
KICS_RELEVANT = ("oidc", "federat", "assumerolewithwebidentity", "github")  # query names/descriptions
PROPOSED = "proposed: checkov 3.3.21 + PR #7610 + CKV_GHOIDC_1"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def checkov(venv, checks, extra=()):
    exe = str(TOOLS / venv / "bin/checkov")
    cmd = [exe, "-d", str(FIX), "--framework", "terraform", "-o", "json", "--compact", "--check", checks, *extra]
    data = json.loads(sh(cmd).stdout)
    verdicts = {}
    for report in data if isinstance(data, list) else [data]:
        for verdict, key in (("PASS", "passed_checks"), ("FAIL", "failed_checks")):
            for r in report.get("results", {}).get(key, []):
                case = r["file_path"].strip("/").split("/")[0]
                k = (case, r["resource"].removeprefix("data."))
                if verdicts.get(k) != "FAIL":
                    verdicts[k] = verdict
    return verdicts, " ".join(cmd[1:]).replace(str(ROOT) + "/", "")


def kics():
    k = TOOLS / "kics"
    with tempfile.TemporaryDirectory() as out:
        cmd = [str(k / "bin/kics"), "scan", "-p", str(FIX), "-q", str(k / "assets/queries"), "-o", out,
               "--report-formats", "json", "--output-name", "kics", "--type", "Terraform",
               "--disable-secrets", "--no-progress", "--silent"]
        sh(cmd)  # KICS exits non-zero when it finds anything
        data = json.loads((Path(out) / "kics.json").read_text())
    verdicts, hits = {}, {}
    for q in data.get("queries", []):
        relevant = any(s in (q["query_name"] + " " + q.get("description", "")).lower() for s in KICS_RELEVANT)
        for f in q.get("files", []):
            case = Path(f["file_name"]).parent.name
            hits.setdefault(case, set()).add(q["query_name"])
            if relevant:
                verdicts[case] = "FAIL"
    return verdicts, hits, " ".join(cmd[1:]).replace(str(k) + "/", "$KICS/").replace(str(ROOT) + "/", "")


def score(labels, lookup):
    cases = {}
    for case, lab in labels.items():
        verdict = lookup(case, lab["target"]) or "NONE"
        flagged, want_fail = verdict == "FAIL", lab["expect"] == "FAIL"
        outcome = ("TP" if flagged else "FN") if want_fail else ("FP" if flagged else "TN")
        cases[case] = {"verdict": verdict, "outcome": outcome}
    summary = Counter(c["outcome"] for c in cases.values())
    by_kind = {}
    for case, c in cases.items():
        by_kind.setdefault(labels[case]["kind"], Counter())[c["outcome"]] += 1
    return {"cases": cases, "summary": dict(summary), "by_kind": {k: dict(v) for k, v in by_kind.items()}}


def main():
    labels = json.loads((FIX / "labels.json").read_text())
    tools, commands = {}, {}

    kv, khits, commands["kics v2.2.0"] = kics()
    tools["kics v2.2.0"] = score(labels, lambda c, t: kv.get(c))
    tools["kics v2.2.0"]["unrelated_queries_hit"] = sorted({q for qs in khits.values() for q in qs})

    for name, venv, checks, extra in [
        ("checkov 3.3.21 (built-in)", "checkov", BUILTIN, ()),
        ("checkov 3.3.21 + PR #7610", "checkov-pr7610", BUILTIN, ()),
        (PROPOSED, "checkov-pr7610", BUILTIN + ",CKV_GHOIDC_1", ("--external-checks-dir", str(ROOT / "checks"))),
    ]:
        v, commands[name] = checkov(venv, checks, extra)
        tools[name] = score(labels, lambda c, t, v=v: v.get((c, t)))

    commit = sh(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]).stdout.strip() or "uncommitted"
    manifest = {
        "run_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "fixtures_commit": commit,
        "dirty": bool(sh(["git", "-C", str(ROOT), "status", "--porcelain", "fixtures", "checks"]).stdout.strip()),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "checkov": sh([str(TOOLS / "checkov/bin/checkov"), "--version"]).stdout.strip(),
        "kics": sh([str(TOOLS / "kics/bin/kics"), "version"]).stdout.strip(),
        "cases": len(labels),
        "commands": commands,
    }
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps({"manifest": manifest, "tools": tools}, indent=2) + "\n")
    (out / "report.md").write_text(report(labels, tools, manifest))
    print((out / "report.md").read_text())

    bad = [c for c, r in tools[PROPOSED]["cases"].items()
           if r["outcome"] == "FP" or (r["outcome"] == "FN" and labels[c]["kind"] in ("security", "apply-failure"))]
    if bad:
        sys.exit(f"proposed configuration wrong on: {', '.join(bad)}")


def report(labels, tools, manifest):
    names = list(tools)
    lines = ["# Results", "",
             f"Run {manifest['run_at_utc']} · fixtures `{manifest['fixtures_commit']}`{' (dirty)' if manifest['dirty'] else ''}"
             f" · {manifest['cases']} cases · checkov {manifest['checkov']} · {manifest['kics'] or 'kics'}", "",
             "## Summary", "", "| Tool | TP | FN | FP | TN |", "|---|---|---|---|---|"]
    for n in names:
        s = tools[n]["summary"]
        lines.append(f"| {n} | {s.get('TP', 0)} | {s.get('FN', 0)} | {s.get('FP', 0)} | {s.get('TN', 0)} |")
    lines += ["", "TP/FN count cases labelled FAIL; FP/TN count cases labelled PASS. `NONE` = the tool did not evaluate the resource.", "",
              "## Per case", "", "| Case | Kind | Expect | " + " | ".join(names) + " |", "|---|---|---|" + "---|" * len(names)]
    mark = {"TP": "✅", "TN": "✅", "FP": "❌ FP", "FN": "❌ FN"}
    for case, lab in labels.items():
        cells = [f"{tools[n]['cases'][case]['verdict']} {mark[tools[n]['cases'][case]['outcome']]}" for n in names]
        lines.append(f"| `{case}` | {lab['kind']} | {lab['expect']} | " + " | ".join(cells) + " |")
    lines += ["", "## Commands", ""] + [f"- **{n}**: `{c}`" for n, c in manifest["commands"].items()]
    lines += ["", "## What this result does not establish", "",
              "- Prevalence: the cases are synthetic; nothing here measures how often these patterns occur in real repositories.",
              "- Runtime behaviour: no tokens were minted and no cloud API was called; Entra/AWS acceptance is taken from official docs.",
              "- Coverage beyond the listed resources: GCP, GitLab, Terraform plan JSON and modules with unresolved variables are not tested.",
              "- `policy` cases (org-wide wildcards) encode this corpus's stance; some tools allow them by design.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
