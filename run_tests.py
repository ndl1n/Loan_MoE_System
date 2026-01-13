#!/usr/bin/env python
"""
測試執行器
提供便捷的測試執行方式
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(test_type: str = "all", verbose: bool = True, coverage: bool = False):
    """
    執行測試
    
    Args:
        test_type: "all", "unit", "integration", "e2e"
        verbose: 是否顯示詳細輸出
        coverage: 是否計算覆蓋率
    """
    # 基本命令
    cmd = ["python", "-m", "pytest"]
    
    # 測試類型對應的路徑
    test_paths = {
        "all": "tests/",
        "unit": "tests/unit/",
        "integration": "tests/integration/",
        "e2e": "tests/e2e/"
    }
    
    # 加入測試路徑
    if test_type in test_paths:
        cmd.append(test_paths[test_type])
    else:
        print(f"❌ 未知的測試類型: {test_type}")
        print(f"   可用選項: {', '.join(test_paths.keys())}")
        sys.exit(1)
    
    # 詳細輸出
    if verbose:
        cmd.append("-v")
    
    # 覆蓋率
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing"])
    
    # 執行
    print(f"🧪 執行測試: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd)
    
    return result.returncode


def run_specific_test(test_path: str):
    """執行特定測試檔案"""
    cmd = ["python", "-m", "pytest", test_path, "-v"]
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Loan MoE System 測試執行器")
    
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "e2e"],
        help="測試類型 (default: all)"
    )
    
    parser.add_argument(
        "-f", "--file",
        help="執行特定測試檔案"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="計算測試覆蓋率"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="減少輸出"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🏦 Loan MoE System - 測試套件")
    print("=" * 60)
    
    if args.file:
        print(f"📁 執行特定測試: {args.file}")
        return_code = run_specific_test(args.file)
    else:
        print(f"📋 測試類型: {args.type}")
        return_code = run_tests(
            test_type=args.type,
            verbose=not args.quiet,
            coverage=args.coverage
        )
    
    print("=" * 60)
    if return_code == 0:
        print("✅ 所有測試通過!")
    else:
        print(f"❌ 測試失敗 (return code: {return_code})")
    
    sys.exit(return_code)


if __name__ == "__main__":
    main()
