import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TSVC_SRC = REPO_ROOT / "emulator" / "benchmarks" / "TSVC_2" / "src"
SHIM_HEADER = TSVC_SRC / "math.h"
SYS_TIME_HEADER = TSVC_SRC / "sys" / "time.h"
STDLIB_HEADER = TSVC_SRC / "stdlib.h"
STRING_HEADER = TSVC_SRC / "string.h"
INTTYPES_HEADER = TSVC_SRC / "inttypes.h"
MATH_CALL_PATTERN = re.compile(
    r"\b("
    r"fabsf?|fabsl|sqrtf?|sqrtl|sinf?|sinl|cosf?|cosl|expf?|expl|"
    r"logf?|logl|powf?|powl|atanf?|atanl|floorf?|floorl|ceilf?|ceill|"
    r"fminf?|fminl|fmaxf?|fmaxl|isnan|isinf"
    r")\s*\("
)
PREVIOUS_MATH_H_FAILURE_BENCHES = {
    "s111",
    "s1111",
    "s1112",
    "s1115",
    "s1119",
    "s113",
    "s115",
    "s1161",
    "s119",
    "s122",
    "s1221",
    "s1232",
    "s125",
    "s1251",
    "s132",
    "s1351",
    "s162",
    "s171",
    "s172",
    "s173",
    "s174",
    "s175",
    "s176",
    "s2102",
    "s2244",
    "s2275",
    "s233",
    "s257",
    "s2711",
    "s2712",
    "s272",
    "s273",
    "s274",
    "s315",
    "s4115",
    "s4116",
    "s431",
    "s441",
}


class TSVCMathCompatTest(unittest.TestCase):
    def test_math_shim_exports_only_used_helpers(self):
        header = SHIM_HEADER.read_text(encoding="utf-8")
        self.assertIn("static inline float fabsf(float value)", header)
        self.assertIn("static inline double fabs(double value)", header)
        common_header = (TSVC_SRC / "common.h").read_text(encoding="utf-8")
        self.assertIn("#define ABS fabsf", common_header)
        sys_time_header = SYS_TIME_HEADER.read_text(encoding="utf-8")
        self.assertIn("struct timeval", sys_time_header)
        self.assertIn("typedef long suseconds_t;", sys_time_header)
        stdlib_header = STDLIB_HEADER.read_text(encoding="utf-8")
        self.assertIn("void exit(int code);", stdlib_header)
        string_header = STRING_HEADER.read_text(encoding="utf-8")
        self.assertIn("int strcmp(const char *lhs, const char *rhs);", string_header)
        inttypes_header = INTTYPES_HEADER.read_text(encoding="utf-8")
        self.assertIn("typedef __UINT64_TYPE__ uint64_t;", inttypes_header)

    def test_previous_math_h_failures_only_need_supported_math_helpers(self):
        used_helpers = set()
        loops_dir = TSVC_SRC / "loops"
        for bench in PREVIOUS_MATH_H_FAILURE_BENCHES:
            path = loops_dir / f"{bench}.c"
            matches = MATH_CALL_PATTERN.findall(path.read_text(encoding="utf-8"))
            used_helpers.update(matches)

        self.assertTrue(used_helpers.issubset({"fabs", "fabsf"}), used_helpers)


if __name__ == "__main__":
    unittest.main()
