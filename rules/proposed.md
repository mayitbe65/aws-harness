# Rules Proposed（待人工审核）

> 本文件由 `/evolve-memory` 自动生成。**禁止直接编辑 personal.md 或 CLAUDE.md**。
> 审核通过后手动转正。每条标注状态 ⏳ 待审核 / ✅ 已转正 / ❌ 已否决。

---

## P1：异步函数调用必须加 await ⏳

**触发**：同类纠正 3 次达阈值（首次提案）
**建议硬化层级**：L1 文字规则（首次）→ 5+ 次复发升 L2 hook 门控

**规则文本**：所有 async 函数调用处必须加 `await`；裸调返回 coroutine 对象，后续运算静默产生错误结果。

**级别**：MUST — 违反导致 coroutine 对象被当作值运算，bug 不报错、难定位

**证据**：
- [2026-06-24 20:18] 漏了 await，返回的是 coroutine 不是结果 → async 函数调用前必须加 await
- [2026-06-25 17:55] 又漏 await 了，db.execute() 是 async 的 → 检查所有 async 调用是否加了 await
- [2026-06-26 15:30] 第三次：recommendations 计算里 await 又漏了，直接拿 coroutine 对象做了运算 → mypy 严格模式能帮助发现

**建议检查点**：
- `mypy --strict` 开启后可捕获 coroutine 未 await 警告（`mypy: error: coroutine is not awaited`）
- CI 加 `mypy src/` 步骤，不通过则 block merge

---

## P2：外部 API 调用必须包裹 try/except ⏳

**触发**：同类纠正 3 次达阈值（首次提案）
**建议硬化层级**：L1 文字规则（首次）→ 5+ 次复发升 L2 hook 门控

**规则文本**：调用任何外部依赖（Vision API、Bedrock、PDF 渲染服务等）必须包裹 try/except，至少捕获超时和限流，返回用户友好错误信息而非 traceback。

**级别**：MUST — 违反导致外部服务抖动时用户直接看到 500/traceback

**证据**：
- [2026-06-24 11:05] Vision API 调用没有 try/except，网络超时直接 500 → 外部 API 调用必须包裹错误处理
- [2026-06-25 09:40] Bedrock 调用又没有异常捕获，Bedrock 偶发限流时整个请求崩了 → 不要裸调外部 API
- [2026-06-26 16:55] 第三次：导出用的 PDF 渲染服务调用没有 fallback，服务抖动时用户直接看到 traceback

**建议检查点**：
```python
# 最小模式：每个外部调用都要有这个壳
try:
    result = await external_service.call(...)
except (TimeoutError, RateLimitError) as e:
    logger.warning("external service error: %s", e)
    raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")
```
- code review 时搜索 `await.*api\|await.*service` 确认每个调用有 try/except

---

## P3：init() 必须在 connect() 之前调用 ⏳

**触发**：同类纠正 3 次达阈值（首次提案）
**建议硬化层级**：L1 文字规则（首次）

**规则文本**：初始化序列必须严格遵守 `init() → connect() → start()`，颠倒顺序导致 `AttributeError: NoneType`。

**级别**：MUST — 顺序错误会造成运行时崩溃

**证据**：
- [2026-06-25 02:49] 不对，应该先调用 init 再 connect
- [2026-06-25 14:33] 又搞反了，init 必须在 connect 之前，不然 session 是 None → 先 init() 再 connect()
- [2026-06-26 09:12] 同样的问题：connect 在 init 前调用导致 AttributeError → 顺序：init → connect → start

**建议检查点**：
- 将三步封装为单个 `setup()` 函数，外部只暴露 `setup()`，不允许单独调用 `connect()`
- 若无法封装，在 `connect()` 内部 assert `self._initialized is True`

---

## P4：R1 复发预警 — user_id 查询过滤 ⏳

**触发**：已有规则 R1 在 corrections.md 中复发 3 次，未到 L2 门槛（5+），但趋势需关注
**建议硬化层级**：L1 已存在 → 观察；若复发达 5 次，升 L2（pre-commit hook 扫描裸 `.all()` / `.filter()` 无 user_id）

**规则文本**：R1 已在 personal.md 中定义，但反复被违反。建议：
1. 在 `BaseQuery` 或依赖注入层面强制注入 `user_id`，从根本上让"忘记过滤"变得不可能
2. 集成测试 `test_user_isolation.py` 已存在（2026-06-27 提交），继续扩展覆盖 export 接口

**证据**（R1 复发记录）：
- [2026-06-24 16:05] 查询没带 user_id 过滤，会返回所有用户数据
- [2026-06-25 11:20] 忘记在 list 接口加 user_id 条件了 → R1 规则
- [2026-06-27 10:44] export 接口没过滤 user_id，导致能拿到别人的导出记录

**L2 触发条件**：再复发 2 次（共 5 次）→ 提案 pre-commit hook：
```bash
# 扫描 .all() 裸调，强制要求加 .filter(user_id=...)
grep -rn "\.all()" backend/src/routers/ && echo "WARNING: bare .all() found, add user_id filter"
```

---

## 遗忘扫描结果（2026-06-25）

扫描 `memory/MEMORY.md`：
- 最老条目日期：2026-06-23（距今 2 天）
- 阈值：>60 天
- **结论：无条目满足 dormant 条件，本次不标记任何条目。**
