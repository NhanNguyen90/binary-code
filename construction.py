from collections import Counter
from hashlib import sha256
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEX_PATH = HERE / "hex_16_262_5_code.txt"
CERT_PATH = HERE / "replacement_certificate_76.txt"
TABLE_I_PATH = HERE / "table_I_code_16_262_5.tex"
TABLE_II_PATH = HERE / "table_II_neighborhoods_16_262_5.tex"
TABLE_III_PATH = HERE / "table_III_replacements_16_262_5.tex"

G = (
    (1, 0, 0, 0, 2, 1, 1, 1),
    (0, 1, 0, 0, 1, 2, 1, 3),
    (0, 0, 1, 0, 1, 3, 2, 1),
    (0, 0, 0, 1, 1, 1, 3, 2),
)
PACKED_GRAY = (0b00, 0b10, 0b11, 0b01)
HOLES = (0x24E7, 0x60AC, 0x8026, 0xC0CF, 0x4444, 0x1085)
PARENT_BIT = {
    0:9, 13:12, 15:4, 17:11, 21:5, 23:11, 24:2, 25:4, 28:10, 30:2, 31:11,
    42:12, 45:10, 59:2, 61:8, 63:2, 66:8, 67:11, 69:3, 71:9, 72:4, 74:2,
    75:8, 76:8, 77:11, 78:4, 80:11, 88:9, 90:13, 93:3, 95:4, 97:8, 100:15,
    104:0, 105:2, 111:2, 114:9, 127:8, 130:7, 136:9, 138:4, 143:11, 146:11,
    147:8, 148:12, 150:9, 152:4, 154:7, 155:2, 157:12, 158:3, 159:9, 162:9,
    173:8, 176:13, 183:9, 185:8, 186:2, 188:2, 190:8, 192:14, 198:13, 200:4,
    201:15, 202:6, 204:4, 205:9, 207:11, 208:9, 210:11, 221:4, 223:10, 234:1,
    236:7, 248:15, 253:2,
}
EXPECTED_ENUMERATOR = {
    5:2540, 6:8533, 7:4113, 8:3413, 9:5163,
    10:7754, 11:2244, 12:303, 15:76, 16:52,
}
EXPECTED_HASH = "c3a3c9947da9ee43278cf0eeddb798db0d4cdb2bce6280a944270e7f998d5fef"


def distance(x, y):
    return (x ^ y).bit_count()


def nordstrom_robinson():
    code = []
    for key in range(256):
        a = tuple((key >> (2 * r)) & 3 for r in range(4))
        z = tuple(sum(a[r] * G[r][j] for r in range(4)) % 4 for j in range(8))
        code.append(sum(PACKED_GRAY[zj] << (2 * j) for j, zj in enumerate(z)))
    return code


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def construct():
    nr = nordstrom_robinson()
    neighborhoods = []
    for hole in HOLES:
        distances = [distance(hole, word) for word in nr]
        require(min(distances) == 4, "invalid deep hole")
        require(5 not in distances, "distance-5 parent found")
        neighborhood = tuple(k for k, d in enumerate(distances) if d == 4)
        require(len(neighborhood) == 20, "invalid neighborhood size")
        neighborhoods.append(neighborhood)

    parent_union = set().union(*(set(s) for s in neighborhoods))
    require(len(parent_union) == 76, "invalid union size")
    require(parent_union == set(PARENT_BIT), "certificate parent set mismatch")
    require(all(distance(a, b) == 6 for a, b in combinations(HOLES, 2)), "invalid hole distance")
    require(all(len(set(a) & set(b)) == 4 for a, b in combinations(neighborhoods, 2)), "invalid pair intersection")
    require(all(len(set.intersection(*(set(neighborhoods[i]) for i in ids))) == 1 for ids in combinations(range(6), 3)), "invalid triple intersection")
    first_five = neighborhoods[:5]
    require(all(set.intersection(*(set(first_five[i]) for i in ids)) == {157} for r in (3, 4, 5) for ids in combinations(range(5), r)), "invalid first-five higher intersection")
    require(all(not set.intersection(set(neighborhoods[5]), *(set(neighborhoods[i]) for i in ids)) for ids in combinations(range(5), 3)), "invalid fourfold intersection")
    require(not set.intersection(*(set(s) for s in neighborhoods)), "invalid sixfold intersection")
    old_union = set().union(*(set(s) for s in neighborhoods[:5]))
    require(len(old_union) == 66, "invalid five-hole union")
    require(len(set(neighborhoods[5]) & old_union) == 10, "invalid sixth-hole overlap")

    replacements = {}
    for k in sorted(parent_union):
        y = nr[k] ^ (1 << PARENT_BIT[k])
        require(distance(y, nr[k]) == 1, "invalid replacement")
        require(all(distance(y, h) >= 5 for h in HOLES), "replacement too close to hole")
        for i, neighborhood in enumerate(neighborhoods):
            if k in neighborhood:
                require(distance(y, HOLES[i]) == 5, "replacement-hole equality failed")
        replacements[k] = y

    require(min(distance(a, b) for a, b in combinations(replacements.values(), 2)) >= 6, "replacement distance below 6")
    retained = {k: nr[k] for k in range(256) if k not in parent_union}
    require(len(retained) == 180, "invalid retained count")
    require(min(distance(a, b) for a, b in combinations(retained.values(), 2)) >= 6, "retained distance below 6")
    require(min(distance(a, h) for a in retained.values() for h in HOLES) >= 6, "retained-hole distance below 6")
    require(min(distance(a, y) for a in retained.values() for y in replacements.values()) >= 5, "retained-replacement distance below 5")

    code = sorted(list(retained.values()) + list(HOLES) + list(replacements.values()))
    require(len(code) == 262 and len(set(code)) == 262, "invalid code size")
    enumerator = Counter(distance(a, b) for a, b in combinations(code, 2))
    require(min(enumerator) == 5, "invalid minimum distance")
    require(dict(sorted(enumerator.items())) == EXPECTED_ENUMERATOR, "distance enumerator mismatch")
    require(sum(enumerator.values()) == 34191, "invalid pair count")
    return nr, neighborhoods, code, enumerator


def write_outputs(neighborhoods, code):
    hex_words = [f"{word:04X}" for word in code]
    payload = "".join(word + "\n" for word in hex_words).encode("ascii")
    digest = sha256(payload).hexdigest()
    require(digest == EXPECTED_HASH, "SHA-256 mismatch")
    HEX_PATH.write_bytes(payload)

    cert_payload = (
        "HOLES " + " ".join(f"{h:04X}" for h in HOLES) + "\n" +
        "".join(f"{k}:{PARENT_BIT[k]}\n" for k in sorted(PARENT_BIT))
    ).encode("ascii")
    CERT_PATH.write_bytes(cert_payload)

    rows = []
    for start in range(0, len(hex_words), 20):
        rows.append(" & ".join(hex_words[start:start + 20]) + r" \\")
    table_i = "\n".join([
        r"\begin{table*}[!t]",
        r"\caption{An explicit binary $(16,262,5)$ code in hexadecimal notation. Each entry is one binary word of length 16; leading zeroes are significant. The entries are listed in increasing numerical order.}",
        r"\label{tab:code}",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.2pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\begin{tabular}{*{20}{c}}",
        r"\hline",
        *rows,
        r"\hline",
        r"\end{tabular}",
        r"\end{table*}",
        "",
    ])
    TABLE_I_PATH.write_text(table_i, encoding="ascii", newline="\n")

    table_ii_rows = [
        f"{i} & {HOLES[i]:04X} & " + ", ".join(map(str, neighborhoods[i])) + r"\\"
        for i in range(6)
    ]
    table_ii = "\n".join([
        r"\begin{table*}[!t]",
        r"\caption{The six sets of base word indices at distance 4 in the indexed Nordstrom--Robinson code.}",
        r"\label{tab:neighborhoods}",
        r"\centering",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{tabular}{c c >{\raggedright\arraybackslash}p{0.81\textwidth}}",
        r"\toprule",
        r"$i$ & $h_i$ & $D_i$\\",
        r"\midrule",
        *table_ii_rows,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
        "",
    ])
    TABLE_II_PATH.write_text(table_ii, encoding="ascii", newline="\n")

    descriptors = [f"{k}:{PARENT_BIT[k]}" for k in sorted(PARENT_BIT)]
    cert_rows = []
    for start in range(0, len(descriptors), 11):
        cert_rows.append(" & ".join(descriptors[start:start + 11]) + r" \\")
    table_iii = "\n".join([
        r"\begin{table*}[!t]",
        r"\caption{Replacement certificate. A descriptor $k{:}b$ means that the parent $n_k$ is deleted and replaced by $n_k+e_b$. There is one descriptor for each of the 76 distinct parents in $D$.}",
        r"\label{tab:certificate}",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4.1pt}",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{tabular}{*{11}{c}}",
        r"\hline",
        *cert_rows,
        r"\hline",
        r"\end{tabular}",
        r"\end{table*}",
        "",
    ])
    TABLE_III_PATH.write_text(table_iii, encoding="ascii", newline="\n")
    return digest


def main():
    _, neighborhoods, code, enumerator = construct()
    digest = write_outputs(neighborhoods, code)
    print("PASS")
    print("size=262 minimum_distance=5 pairs=34191")
    print("distance_enumerator " + " ".join(f"{d}:{n}" for d, n in sorted(enumerator.items())))
    print("SHA-256 " + digest)


if __name__ == "__main__":
    main()
