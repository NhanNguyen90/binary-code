from collections import Counter
from itertools import combinations
from pathlib import Path
from random import Random

HERE = Path(__file__).resolve().parent
REPORT_PATH = HERE / "discovery_results.txt"
G = (
    (1, 0, 0, 0, 2, 1, 1, 1),
    (0, 1, 0, 0, 1, 2, 1, 3),
    (0, 0, 1, 0, 1, 3, 2, 1),
    (0, 0, 0, 1, 1, 1, 3, 2),
)
PACKED_GRAY = (0b00, 0b10, 0b11, 0b01)
BASE_HOLES = (0x24E7, 0x60AC, 0x8026, 0xC0CF, 0x4444)
WARM = {
    0:0, 13:2, 17:4, 21:8, 23:4, 24:12, 25:2, 28:2, 30:4, 31:12,
    42:9, 45:9, 61:1, 63:8, 66:12, 69:8, 72:9, 74:11, 75:12, 76:11,
    78:9, 80:12, 88:6, 90:2, 93:12, 97:1, 100:5, 104:8, 105:11, 111:11,
    130:12, 136:9, 138:8, 143:9, 146:4, 148:8, 150:4, 152:7, 154:2, 155:3,
    157:9, 158:2, 159:2, 162:5, 173:11, 176:13, 183:8, 185:13, 186:9,
    190:6, 192:12, 198:8, 200:2, 201:9, 202:2, 204:2, 205:10, 207:11,
    208:4, 210:4, 221:2, 223:6, 234:11, 236:8, 248:8, 253:9,
}
RESTARTS = 20
ITERATIONS = 15000
RANDOM_MOVE = 0.02
PERTURB_INTERVAL = 3000
PERTURB_COUNT = 5


def distance(x, y):
    return (x ^ y).bit_count()


def nordstrom_robinson():
    code = []
    for key in range(256):
        a = tuple((key >> (2 * r)) & 3 for r in range(4))
        z = tuple(sum(a[r] * G[r][j] for r in range(4)) % 4 for j in range(8))
        code.append(sum(PACKED_GRAY[zj] << (2 * j) for j, zj in enumerate(z)))
    return code


def deep_holes(nr):
    result = []
    for x in range(1 << 16):
        distances = [distance(x, word) for word in nr]
        if min(distances) == 4:
            neighborhood = tuple(k for k, d in enumerate(distances) if d == 4)
            if len(neighborhood) != 20 or 5 in distances:
                raise RuntimeError("deep-hole census failed")
            result.append((x, neighborhood))
    return result


def domains_for(nr, holes, parent_union):
    domains = {}
    for k in sorted(parent_union):
        values = [b for b in range(16) if all(distance(nr[k] ^ (1 << b), h) >= 5 for h in holes)]
        if not values:
            return None
        domains[k] = values
    return domains


def solve(nr, domains, warm, seed):
    variables = sorted(domains)
    neighbors = [[] for _ in variables]
    for i in range(len(variables)):
        for j in range(i):
            if distance(nr[variables[i]], nr[variables[j]]) == 6:
                neighbors[i].append(j)
                neighbors[j].append(i)

    def conflict(i, bi, j, bj):
        return distance(nr[variables[i]] ^ (1 << bi), nr[variables[j]] ^ (1 << bj)) < 6

    rng = Random(seed)
    for restart in range(RESTARTS):
        assignment = []
        for k in variables:
            if restart == 0 and k in warm and warm[k] in domains[k]:
                assignment.append(warm[k])
            else:
                assignment.append(rng.choice(domains[k]))

        def count(i):
            return sum(conflict(i, assignment[i], j, assignment[j]) for j in neighbors[i])

        counts = [count(i) for i in range(len(variables))]
        total = sum(counts) // 2
        if total == 0:
            return {variables[i]: assignment[i] for i in range(len(variables))}, restart, 0, neighbors

        for iteration in range(ITERATIONS):
            conflicted = [i for i, c in enumerate(counts) if c]
            if not conflicted:
                return {variables[i]: assignment[i] for i in range(len(variables))}, restart, iteration, neighbors
            i = rng.choice(conflicted)
            scored = []
            for b in domains[variables[i]]:
                score = sum(conflict(i, b, j, assignment[j]) for j in neighbors[i])
                scored.append((score, b))
            minimum = min(score for score, _ in scored)
            best = [b for score, b in scored if score == minimum]
            new_value = rng.choice(domains[variables[i]]) if rng.random() < RANDOM_MOVE else rng.choice(best)
            if new_value != assignment[i]:
                assignment[i] = new_value
                counts[i] = count(i)
                for j in neighbors[i]:
                    counts[j] = count(j)
                total = sum(counts) // 2
                if total == 0:
                    return {variables[q]: assignment[q] for q in range(len(variables))}, restart, iteration + 1, neighbors
            if (iteration + 1) % PERTURB_INTERVAL == 0:
                for q in rng.sample(conflicted, min(PERTURB_COUNT, len(conflicted))):
                    assignment[q] = rng.choice(domains[variables[q]])
                counts = [count(q) for q in range(len(variables))]
    return None, None, None, neighbors


def main():
    nr = nordstrom_robinson()
    deep = deep_holes(nr)
    dmap = {h: d for h, d in deep}
    base_union = set().union(*(set(dmap[h]) for h in BASE_HOLES))
    candidates = []

    for h, neighborhood in deep:
        if h in BASE_HOLES:
            continue
        minimum_hole_distance = min(distance(h, g) for g in BASE_HOLES)
        if minimum_hole_distance < 6:
            continue
        parent_union = base_union | set(neighborhood)
        holes = BASE_HOLES + (h,)
        domains = domains_for(nr, holes, parent_union)
        if domains is None:
            continue
        minimum_domain = min(len(v) for v in domains.values())
        candidates.append((len(parent_union), -minimum_domain, h, domains, parent_union))

    candidates.sort(key=lambda row: (row[0], row[1], row[2]))
    union_distribution = Counter(row[0] for row in candidates)
    minimum_union = min(union_distribution)
    minimum_count = union_distribution[minimum_union]
    selected = candidates[0]
    union_size, _, hole, domains, parent_union = selected
    seed = 202608120000 + hole
    solution, restart, iteration, neighbors = solve(nr, domains, WARM, seed)
    if solution is None:
        raise RuntimeError("search failed")

    holes = BASE_HOLES + (hole,)
    replacements = [nr[k] ^ (1 << solution[k]) for k in sorted(solution)]
    code = [nr[k] for k in range(256) if k not in parent_union] + list(holes) + replacements
    if len(code) != 262 or len(set(code)) != 262:
        raise RuntimeError("invalid discovered code")
    minimum_distance = min(distance(a, b) for a, b in combinations(code, 2))
    if minimum_distance != 5:
        raise RuntimeError("invalid discovered minimum distance")

    domain_distribution = Counter(len(v) for v in domains.values())
    edge_count = sum(len(v) for v in neighbors) // 2
    degrees = [len(v) for v in neighbors]
    lines = [
        "DISCOVERY OF A SIXTH OVERLAPPING NORDSTROM--ROBINSON TRADE",
        f"deep holes enumerated: {len(deep)}",
        f"compatible viable sixth holes: {len(candidates)}",
        f"minimum union size: {minimum_union}",
        f"number attaining minimum: {minimum_count}",
        f"selected sixth hole: {hole:04X}",
        "holes: " + " ".join(f"{h:04X}" for h in holes),
        f"union size: {union_size}",
        f"sixth overlap with five-hole union: {len(set(dmap[hole]) & base_union)}",
        "domain-size distribution: " + " ".join(f"{k}:{domain_distribution[k]}" for k in sorted(domain_distribution)),
        f"conflict graph edges: {edge_count}",
        f"conflict graph degree range: {min(degrees)}..{max(degrees)}",
        f"seed: {seed}",
        f"maximum restarts: {RESTARTS}",
        f"iterations per restart: {ITERATIONS}",
        f"solution restart (zero based): {restart}",
        f"iterations completed: {iteration}",
        f"discovered code size: {len(code)}",
        f"discovered minimum distance: {minimum_distance}",
        "",
        "replacement certificate:",
    ]
    lines.extend(f"{k}:{solution[k]}" for k in sorted(solution))
    lines.extend(["", "PASS"])
    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_bytes(report.encode("ascii"))
    print(report, end="")


if __name__ == "__main__":
    main()
