# ============================================================
# 防御引擎 — 一键测试入口
#
# 用法:
#   python run_tests.py           # 运行全部测试
#   python run_tests.py --quick   # 仅运行核心测试 (跳过边缘用例)
#   python run_tests.py -v        # 详细模式
# ============================================================

import sys
import os
import io

# ---- 强制 UTF-8 (解决 Windows GBK 编码问题) ----
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ---- 确保项目根目录在 sys.path ----
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

import time
import traceback


def discover_tests():
    """自动发现 tests/ 目录下所有 test_*.py 文件"""
    import importlib
    tests_dir = os.path.join(PROJECT_ROOT, "tests")
    test_modules = []

    for fname in sorted(os.listdir(tests_dir)):
        if fname.startswith("test_") and fname.endswith(".py"):
            mod_name = f"tests.{fname[:-3]}"
            test_modules.append(mod_name)

    return test_modules


def collect_test_functions(module_name):
    """从模块中收集所有 test_ 开头的测试类和函数"""
    import importlib
    mod = importlib.import_module(module_name)
    cases = []

    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and attr_name.startswith("Test"):
            # 测试类
            instance = attr()
            for method_name in dir(instance):
                if method_name.startswith("test_"):
                    cases.append((f"{attr_name}.{method_name}", getattr(instance, method_name)))
        elif callable(attr) and attr_name.startswith("test_"):
            # 独立测试函数
            cases.append((attr_name, attr))

    return cases


def main():
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    quick = "--quick" in sys.argv

    print("=" * 60)
    print("  LLM Agent 防御引擎 — 自动化测试")
    print("=" * 60)
    print()

    modules = discover_tests()
    if not modules:
        print("  [警告] tests/ 目录下未找到测试模块")
        return 0

    print(f"  发现 {len(modules)} 个测试模块")
    print()

    total = 0
    passed = 0
    failed = 0
    skipped = 0
    failures = []

    t_start = time.time()

    for mod_name in modules:
        # 如果快速模式且模块名含 edge，跳过
        if quick and "edge" in mod_name.lower():
            continue

        print(f"  [{mod_name}]")
        cases = collect_test_functions(mod_name)

        if not cases:
            print(f"    (无测试用例)")
            continue

        for case_name, case_fn in cases:
            total += 1
            t0 = time.perf_counter()
            try:
                case_fn()
                elapsed = (time.perf_counter() - t0) * 1000
                if verbose:
                    print(f"    PASS  {case_name:<50s} ({elapsed:.1f}ms)")
                passed += 1
            except AssertionError as e:
                elapsed = (time.perf_counter() - t0) * 1000
                msg = str(e) if str(e) else "断言失败"
                print(f"    FAIL  {case_name:<50s} — {msg}")
                if verbose:
                    traceback.print_exc()
                failed += 1
                failures.append((mod_name, case_name, str(e)))
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                print(f"    ERROR {case_name:<50s} — {e}")
                if verbose:
                    traceback.print_exc()
                failed += 1
                failures.append((mod_name, case_name, str(e)))

        if not verbose:
            module_cases = len(cases)
            module_passed = module_cases - sum(1 for m, c, _ in failures if m == mod_name)
            print(f"    {module_passed}/{module_cases} 通过")
        print()

    elapsed_total = time.time() - t_start

    # ---- 汇总 ----
    print("=" * 60)
    print(f"  结果: {passed} 通过 / {failed} 失败 / {total} 总计")
    print(f"  耗时: {elapsed_total:.1f}s")
    print("=" * 60)

    if failures:
        print(f"\n  失败明细:")
        for mod, case, err in failures:
            print(f"    - {mod}::{case}")
            if err:
                print(f"      {err}")
        return 1
    else:
        print("\n  全部测试通过 ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
