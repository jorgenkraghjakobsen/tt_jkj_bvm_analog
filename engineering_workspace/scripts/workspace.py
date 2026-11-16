#!/usr/bin/env python3
"""Read workspace.config and every component's depend.config.

Checks the dependency graph, reports status, and prints a build order.

  python3 scripts/workspace.py           status table + build order
  python3 scripts/workspace.py --graph   dependency graph
  python3 scripts/workspace.py --check   exit non-zero on any problem
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# "descoped" sits first so it never counts toward completion, but it
# is NOT the same as "none": the netlist exists and is verified, the
# block is simply not being laid out for this shuttle.
STATUS_ORDER = ["descoped", "none", "rtl", "netlist", "schematic",
                "layout", "lvs-clean", "signed-off"]


def read_kv(path):
    """Parse a KEY = VALUE file. Repeated keys collect into a list."""
    out = {}
    with open(path) as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            k, v = (s.strip() for s in line.split("=", 1))
            if k in out:
                if not isinstance(out[k], list):
                    out[k] = [out[k]]
                out[k].append(v)
            else:
                out[k] = v
    return out


def as_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return [x for v in val for x in v.split()]
    return val.split()


def load():
    ws = read_kv(os.path.join(ROOT, "workspace.config"))
    paths = as_list(ws.get("COMPONENT"))
    comps = {}
    problems = []

    for rel in paths:
        cfg = os.path.join(ROOT, rel, "depend.config")
        if not os.path.exists(cfg):
            problems.append(f"{rel}: no depend.config")
            continue
        d = read_kv(cfg)
        name = d.get("NAME", os.path.basename(rel))
        d["_path"] = rel
        comps[name] = d

    return ws, comps, problems


def check(comps, problems):
    names = set(comps)
    for name, d in comps.items():
        for dep in as_list(d.get("DEPENDS")):
            if dep not in names:
                problems.append(f"{name}: depends on unknown component '{dep}'")
        st = d.get("STATUS", "none")
        if st not in STATUS_ORDER:
            problems.append(f"{name}: unknown STATUS '{st}'")
        if not d.get("OWNER", "").strip():
            problems.append(f"{name}: no OWNER set")
        for sim in as_list(d.get("SIM")):
            if not os.path.exists(os.path.join(ROOT, d["_path"], sim)):
                problems.append(f"{name}: SIM file missing -- {sim}")
    return problems


def build_order(comps):
    """Kahn topological sort. Returns (order, cycle_members)."""
    indeg = {n: 0 for n in comps}
    adj = {n: [] for n in comps}
    for n, d in comps.items():
        for dep in as_list(d.get("DEPENDS")):
            if dep in comps:
                adj[dep].append(n)
                indeg[n] += 1

    ready = sorted(n for n, v in indeg.items() if v == 0)
    order = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
        ready.sort()

    cycle = sorted(set(comps) - set(order))
    return order, cycle


def main():
    args = sys.argv[1:]
    ws, comps, problems = load()
    problems = check(comps, problems)
    order, cycle = build_order(comps)

    print(f"\n  {ws.get('PROJECT_NAME','?')}  ·  {ws.get('PDK','?')}"
          f"  ·  {ws.get('SHUTTLE','?')}  ·  closes {ws.get('DEADLINE','?')}")
    print(f"  version: {ws.get('VERSION','(unversioned - old tree)')}")
    print(f"  top: {ws.get('TOP','?')}\n")

    if "--graph" in args:
        print("  dependency graph\n")
        for n in order or sorted(comps):
            deps = as_list(comps[n].get("DEPENDS"))
            arrow = "  <- " + ", ".join(deps) if deps else "  (no dependencies)"
            print(f"    {n:<16}{arrow}")
        print()

    print("  " + "-" * 68)
    print(f"  {'component':<16}{'domain':<9}{'status':<12}{'owner':<10}depends on")
    print("  " + "-" * 68)
    for n in (order or sorted(comps)):
        d = comps[n]
        deps = ", ".join(as_list(d.get("DEPENDS"))) or "-"
        owner = d.get("OWNER", "").strip() or "UNSET"
        print(f"  {n:<16}{d.get('DOMAIN','?'):<9}"
              f"{d.get('STATUS','?'):<12}{owner:<10}{deps}")
    print("  " + "-" * 68)

    done = sum(1 for d in comps.values()
               if STATUS_ORDER.index(d.get("STATUS", "none")) >= STATUS_ORDER.index("lvs-clean"))
    print(f"  {len(comps)} components, {done} at lvs-clean or better\n")

    if cycle:
        print(f"  CYCLE in the dependency graph: {', '.join(cycle)}\n")
        problems.append("dependency cycle")
    else:
        print("  build order:")
        print("    " + "  ->  ".join(order) + "\n")

    if problems:
        print("  problems")
        for p in problems:
            print(f"    - {p}")
        print()
    else:
        print("  no problems found\n")

    if "--check" in args and problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
