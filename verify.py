from collections import Counter
from hashlib import sha256
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEX_PATH = HERE / "hex_16_262_5_code.txt"
REPORT_PATH = HERE / "verification_results.txt"
EXPECTED_HASH = "c3a3c9947da9ee43278cf0eeddb798db0d4cdb2bce6280a944270e7f998d5fef"
EXPECTED_ENUMERATOR = {
    5:2540, 6:8533, 7:4113, 8:3413, 9:5163,
    10:7754, 11:2244, 12:303, 15:76, 16:52,
}

def distance(x, y):
    return (x ^ y).bit_count()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def main():
    require(HEX_PATH.exists(), "missing hex_16_262_5_code.txt")
    payload = HEX_PATH.read_bytes()
    text = payload.decode("ascii")
    words = text.splitlines()
    require(len(words) == 262, "invalid number of codewords")
    require(all(len(word) == 4 and all(c in "0123456789ABCDEF" for c in word) for word in words), "invalid hexadecimal word")
    values = [int(word, 16) for word in words]
    require(len(set(values)) == 262, "duplicate codeword")
    require(values == sorted(values), "codewords are not sorted")
    require(all(0 <= value < (1 << 16) for value in values), "word exceeds 16 bits")
    canonical = "".join(f"{value:04X}\n" for value in values).encode("ascii")
    require(payload == canonical, "noncanonical hexadecimal file")
    digest = sha256(payload).hexdigest()
    require(digest == EXPECTED_HASH, "SHA-256 mismatch")
    enumerator = Counter(distance(a, b) for a, b in combinations(values, 2))
    require(sum(enumerator.values()) == 34191, "invalid pair count")
    require(min(enumerator) == 5, "minimum distance is not 5")
    require(dict(sorted(enumerator.items())) == EXPECTED_ENUMERATOR, "distance enumerator mismatch")
    lines = [
        "INDEPENDENT BLACK-BOX VERIFICATION",
        "PASS: the final list is a binary (16,262,5) code",
        "number of distinct codewords: 262",
        "number of unordered pairs: 34191",
        "minimum Hamming distance: 5",
        "",
        "unordered-pair distance enumerator:",
    ]
    for d, count in sorted(enumerator.items()):
        lines.append(f"  d={d:2d}: {count}")
    lines.extend(["", f"SHA-256: {digest}", "", "PASS"])
    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_bytes(report.encode("ascii"))
    print(report, end="")

if __name__ == "__main__":
    main()
