#!/usr/bin/env python3
"""Apply final scope cleanup to the already-refocused AGENTS v0.4.0."""
from __future__ import annotations

import re
from pathlib import Path


PATH = Path("AGENTS.md")


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    if "> 版本：**0.4.0**" not in text:
        raise RuntimeError("AGENTS.md is not the expected v0.4.0 charter")

    replacements = {
        "1. 非标准早期宇宙参数 `theta`；":
            "1. 标准或扩展 BBN 的低维物理参数 `theta`；R0 首先使用标准 BBN；",
        "7. 轻元素观测、CMB、SGWB/PTA/LVK 数据误差和系统学；":
            "7. 轻元素观测与必要的 CMB 重子密度信息；SGWB/PTA/LVK 仅属于 Gate 后可选应用；",
        "`C_rate(theta)` 在扩展宇宙学空间显著变化，常数 `sigma_th` 无法保持后验正确性。":
            "`C_rate(theta)` 在注册的宇宙学参数空间显著变化，常数 `sigma_th` 无法保持后验正确性。",
        "至少一个头部反应的 shape 模态对 D/H、目标扩展参数或 detector-relevant region 的影响不能被单一 normalization `q_i` 吸收。":
            "至少一个头部反应的 shape 模态对主丰度分布或核心宇宙学 posterior 的影响不能被单一 normalization `q_i` 吸收。",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"函数基底可来自：\s*函数基底可来自：",
        "函数基底可来自：",
        text,
        count=1,
    )
    text = re.sub(
        r"#### 计算主终点\s*#### 计算主终点",
        "#### 计算主终点",
        text,
        count=1,
    )

    start = "#### H5 — 早期宇宙物理结论被改变"
    end = "#### H6 — emulator 具有必要性"
    if start in text and end in text:
        i = text.index(start)
        j = text.index(end, i)
        replacement = """#### H5 — 宇宙学推断结论被改变

完整 rate/weak/solver 不确定度传播后，至少一个注册的 BBN inference 结论发生决策相关变化，例如：

- central-rate 与完整边缘化的核心参数 posterior 明显偏移；
- credible interval 或 exclusion boundary 超出冻结的 null band；
- posterior mode/topology 或数据张力解释发生变化；
- 不同丰度之间的理论相关性改变联合 likelihood 的约束。

非标准宇宙学应用只有在 UQ baseline 和正式 Gate 通过后才进入该假设的扩展检验。

"""
        text = text[:i] + replacement + text[j:]

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
