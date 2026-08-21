"""
两数之和（LeetCode 1）

给定一个整数数组 nums 和一个目标值 target，
找出数组中两个数，使它们的和等于 target，返回这两个数的下标。
"""

import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def two_sum(nums: list[int], target: int) -> list[int]:
    """用哈希表一次遍历，时间复杂度 O(n)。"""
    seen: dict[int, int] = {}  # 值 -> 下标
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []


def two_sum_brute(nums: list[int], target: int) -> list[int]:
    """暴力双循环，时间复杂度 O(n²)，便于对照理解。"""
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []


if __name__ == "__main__":
    cases = [
        ([2, 7, 11, 15], 9),
        ([3, 2, 4], 6),
        ([3, 3], 6),
        ([1, 5, 8, 12], 13),
    ]

    print("两数之和示例：")
    print("-" * 40)

    for nums, target in cases:
        result = two_sum(nums, target)
        if result:
            i, j = result
            print(
                f"nums = {nums}, target = {target}  "
                f"-> 下标 {result}  "
                f"({nums[i]} + {nums[j]} = {target})"
            )
        else:
            print(f"nums = {nums}, target = {target}  -> 无解")
