# 错题宝项目规则库

基于真实场景的事故回溯，此文档记录了项目的核心规则和防护措施。每条规则都对应一个可能的坑，使用 MUST/SHOULD/CAN 等级标记。

---

## MUST（硬约束）— 必须遵守

### R1：userId 数据隔离（必须）

**规则**：错题数据必须按 userId 严格隔离。学生只能查看、修改、删除自己的错题。任何查询都必须带上 `WHERE user_id = current_user_id` 条件。

**等级**：**MUST** — 硬约束，违反即数据泄露事故

**防的坑**：
- 🔴 **事故**：学生 A 登录后能看到学生 B 所有的错题记录
- 📝 **原因**：查询题目接口忘记过滤 user_id，返回了所有用户的数据
- 💥 **后果**：隐私泄露、监管罚款、用户流失
- ✅ **检查点**：
  - 所有 GET/LIST 接口必须加 `user_id` 过滤
  - 所有 UPDATE/DELETE 接口必须验证权限（当前用户 == 数据所有者）
  - 数据库查询使用 ORM，自动过滤不可见数据
  - 单元测试验证用户 A 无法访问用户 B 的数据

---

### R2：Bedrock 返回格式校验（必须）

**规则**：Bedrock（或任何 LLM）返回的推荐数据必须先做格式校验，缺少 `confidence` 字段时按 0 处理。不允许直接使用未验证的 LLM 输出。

**等级**：**MUST** — 硬约束，违反即推荐算法崩溃

**防的坑**：
- 🔴 **事故**：Bedrock API 返回格式变化，缺少 `confidence` 字段，前端推荐列表崩溃显示错误信息
- 📝 **原因**：Bedrock 更新了响应模式，后端代码未做版本兼容性校验
- 💥 **后果**：用户无法查看推荐计划，体验中断
- ✅ **检查点**：
  ```python
  # 后端 src/services/recommend_service.py
  recommendation = bedrock_response.get('recommendation', {})
  confidence = float(recommendation.get('confidence', 0.0))  # 缺失时默认 0
  if confidence < 0 or confidence > 1:
      confidence = 0
  if not isinstance(recommendation.get('questions'), list):
      raise ValueError("Invalid Bedrock response format")
  ```
  - 校验字段完整性、类型正确性、数值范围
  - 低 confidence 的推荐需要标记"低可信度"
  - 单元测试覆盖所有畸形响应场景

---

### R3：API 调用必须通过后端代理（必须）

**规则**：所有外部 API 调用（Vision API、Bedrock 等）必须通过后端代理，前端严禁 hardcode 或暴露任何 API 密钥。前端只能调用后端 REST 接口。

**等级**：**MUST** — 硬约束，违反即密钥泄露

**防的坑**：
- 🔴 **事故**：代码审查时发现前端 hardcode 了 Vision API 密钥，已被推送到公开仓库，密钥被他人滥用，配额用尽
- 📝 **原因**：开发时图方便，直接在前端调用 Vision API
- 💥 **后果**：API 配额被滥用、成本暴增、安全漏洞
- ✅ **检查点**：
  - 前端 `src/services/api.ts` 中绝不出现任何 API 密钥（包括注释）
  - 后端 `/api/vision/recognize` 接口代理所有 Vision API 调用
  - 后端 `/api/recommendations` 接口代理所有 Bedrock 调用
  - .env 文件中的密钥使用 pydantic_settings 加载到后端 config
  - pre-commit hook 检查前端代码中是否出现 API 密钥（grep `-E 'sk-|AKIA'`）

---

### R4：Vision API 返回内容质量校验（必须）

**规则**：Vision API 识别结果必须验证：
1. confidence 值在 [0, 1] 范围内
2. 识别文本不为空且长度合理（> 5 字符，< 10000 字符）
3. 不是纯垃圾数据（如重复符号、全是 emoji、"[无法识别]"）

识别质量不达标时，必须标记为"需人工审核"，不得直接入库。

**等级**：**MUST** — 硬约束，违反即垃圾数据污染

**防的坑**：
- 🔴 **事故**：学生上传了一张空白纸张、噪音图片或模糊截图，Vision API 返回 confidence=0.1 且文本为"[无法识别]"，系统还是创建了错题记录，推荐算法后来处理时崩溃
- 📝 **原因**：没有验证识别结果的质量和合理性
- 💥 **后果**：数据库污染、推荐系统崩溃、用户体验差
- ✅ **检查点**：
  ```python
  # 后端 src/services/ai_service.py
  def validate_vision_response(response):
      confidence = float(response.get('confidence', 0))
      text = response.get('recognized_text', '').strip()
      
      # 质量检查
      if confidence < 0.7:
          return {'valid': False, 'reason': 'low_confidence'}
      if len(text) < 5 or len(text) > 10000:
          return {'valid': False, 'reason': 'invalid_length'}
      if text in ['[无法识别]', '......', '···', '']:
          return {'valid': False, 'reason': 'garbage_data'}
      
      return {'valid': True}
  ```
  - 低质量识别标记为 `needs_review=True`，显示"需人工纠正"
  - 人工纠正后更新 `recognized_text` 并设置 `needs_review=False`
  - 推荐算法只用 `needs_review=False` 的题目
  - 单元测试覆盖垃圾数据场景

---

### R5：推荐计划计算需事务保护（必须）

**规则**：推荐计划的计算和更新必须在数据库事务中完成，防止计算过程中数据被修改导致结果不一致。

**等级**：**MUST** — 硬约束，违反即推荐数据不一致

**防的坑**：
- 🔴 **事故**：系统正在计算学生的推荐计划（遍历所有错题），此时学生删除了部分题目，最终计算结果包含了已删除题目的推荐
- 📝 **原因**：推荐计算没有在事务中进行，中途数据被修改
- 💥 **后果**：推荐计划包含无效题目、用户点击时 404、体验差
- ✅ **检查点**：
  ```python
  # 后端 src/services/recommend_service.py
  async def compute_recommendations(user_id: str):
      async with db.begin():  # 开启事务
          questions = await Question.filter(user_id=user_id).all()
          review_plans = []
          for q in questions:
              # 计算推荐优先级
              priority = calculate_priority(q)
              review_plans.append(ReviewPlan(..., priority=priority))
          # 全部计算完成后一次性提交
          await ReviewPlan.bulk_create(review_plans)
      # 事务提交
  ```
  - 使用数据库事务（`async with db.begin()`）保护计算过程
  - 不允许在计算中途提交部分结果
  - 单元测试模拟并发修改场景，验证最终结果一致性

---

### R6：缓存 key 必须包含 userId（必须）

**规则**：Redis 缓存 key 必须包含 userId，严禁使用全局 key（如 `"questions"` 直接作为 key）。缓存 key 格式：`user:{user_id}:questions`。

**等级**：**MUST** — 硬约束，违反即用户看到他人数据

**防的坑**：
- 🔴 **事故**：缓存中的 `"questions"` key 被多个用户共享，用户 A 查询题目，获得了用户 B 的缓存数据
- 📝 **原因**：缓存 key 设计不当，没有隔离用户信息
- 💥 **后果**：严重隐私泄露、数据混乱
- ✅ **检查点**：
  - 所有缓存 key 格式：`{entity}:{user_id}:{resource}:{optional_filter}` 
  - 示例：`question:user123:list:subject_math`、`recommend:user456:plan:week1`
  - 从缓存读取数据后必须验证 user_id 匹配
  - code review 时禁止使用硬编码 key，必须使用常量或工厂函数
  - 单元测试验证不同用户无法访问彼此缓存

---

## SHOULD（强建议）— 默认遵守，有理由可偏离

### R7：推荐算法需单元测试覆盖（强建议）

**规则**：推荐算法（计算优先级、排序、筛选）必须有单元测试，目标覆盖率 > 80%。测试场景包括：正常情况、边界值、异常数据。

**等级**：**SHOULD** — 强建议

**防的坑**：
- 🔴 **事故**：推荐算法改动后，用户投诉推荐顺序毫无逻辑，甚至依赖了随机数生成器，今天刷新推荐就变了
- 📝 **原因**：算法改动没有单元测试，逻辑错误未被发现
- 💥 **后果**：推荐不可信、用户体验差
- ✅ **检查点**：
  - `tests/unit/test_recommend_service.py` 覆盖所有推荐逻辑
  - 测试固定输入、验证输出顺序一致
  - 测试边界值：0 个题目、1000 个题目、各种难度组合
  - 运行 `pytest --cov=src/services/recommend_service.py` 验证覆盖率 > 80%

---

### R8：异步任务失败需通知用户和重试（强建议）

**规则**：Vision API、Bedrock 等异步调用失败时，必须：
1. 记录详细错误日志
2. 在前端显示错误信息（toast 或状态标记"识别失败"）
3. 实现自动重试机制（最多 3 次）
4. 重试失败后保存到人工审核队列

**等级**：**SHOULD** — 强建议

**防的坑**：
- 🔴 **事故**：学生上传照片，页面一直显示"识别中..."，但后台 Vision API 调用其实在第 1 秒就失败了，用户没有任何反馈，等了 10 分钟才放弃
- 📝 **原因**：没有实现失败通知和重试机制
- 💥 **后果**：用户体验极差、客服投诉增加
- ✅ **检查点**：
  - 后端设置 API 调用超时（5 秒）
  - 失败时触发 Celery 重试（max_retries=3，backoff：1s、2s、4s）
  - 前端轮询任务状态，失败时显示"识别失败，已重试 X 次"
  - 重试 3 次仍失败时，题目状态改为"人工审核中"，通知管理员
  - 单元测试验证重试逻辑和错误通知

---

### R9：导出文档使用快照机制（强建议）

**规则**：导出 PDF 时，必须先对选定的题目生成快照（冻结当前的题目内容、答案、解析），然后基于快照生成 PDF。不能实时读取数据库，防止导出中途数据被修改。

**等级**：**SHOULD** — 强建议

**防的坑**：
- 🔴 **事故**：用户导出 PDF 时，题目内容正在被修改，最终 PDF 中的题目和答案对不上，用户投诉
- 📝 **原因**：导出时直接读取数据库，没有使用快照机制
- 💥 **后果**：导出数据不一致、用户不信任
- ✅ **检查点**：
  - 调用导出接口时生成 Snapshot 表记录
  - Snapshot 包含：user_id、selected_questions、created_at、snapshot_data（JSON）
  - 基于 snapshot_data 生成 PDF，不再查询原始数据库
  - 快照保留 30 天供重新下载，之后删除
  - 单元测试验证导出中途修改数据不影响 PDF 内容

---

## CAN（可选偏好）— 灵活选择

### R10：API 限流和速率限制（可选）

**规则**：可选实现 API 限流，防止单个用户或滥用者消耗过多资源。建议限制：
- 每用户每小时 Vision API 调用：100 次
- 每用户每分钟推荐请求：10 次
- 每 IP 每分钟注册：5 次

**等级**：**CAN** — 灵活选择

**防的坑**：
- 🟡 **事故**：某个用户不断刷新上传 10MB 大文件，导致服务器带宽被占满，其他用户无法使用
- 📝 **原因**：没有实现限流保护
- 💥 **后果**：服务雪崩、成本暴增
- ✅ **实现选项**：
  - 使用 FastAPI 中间件 + Redis 计数器
  - 超限时返回 429 Too Many Requests
  - 前端显示"请稍后再试"

---

## 使用指南

### 遵循规则优先级

1. **遇到 MUST 规则**：无条件遵守，违反即停止
2. **遇到 SHOULD 规则**：默认遵守，偏离时说明理由
3. **遇到 CAN 规则**：用判断力，灵活调整

### Code Review 检查清单

```markdown
- [ ] R1：所有查询都加了 user_id 过滤？
- [ ] R2：Bedrock 返回做了格式校验？
- [ ] R3：前端代码中是否暴露 API 密钥？
- [ ] R4：Vision API 返回做了质量检查？
- [ ] R5：推荐计算在事务中完成？
- [ ] R6：缓存 key 包含 user_id？
- [ ] R7：推荐算法有单元测试？
- [ ] R8：异步任务有失败处理和通知？
- [ ] R9：导出功能使用快照机制？
```

### 新规则的加入流程

1. **发现一个坑**（生产事故、代码审查发现的风险）
2. **复盘**："如果当时有什么规则就不会发生？"
3. **编写规则**：规则 + 等级 + 防的坑说明
4. **在 PR 中讨论**并纳入 severity-guide.md 的规则表
5. **添加检查点到 CI/CD**（代码扫描、测试用例等）

---

**最后更新**：当前规则版本 1.0，基于常见坑场景。欢迎更新和补充。

---

## 人类 Gate 规则

以下操作必须暂停并等待我明确确认（输出"⚠️ 需要确认"后等我回复），绝不自动执行：
- git push（任何推送到远端）
- 删除文件（rm / unlink）
- 修改 CI 配置
- 修改 package.json 的 dependencies
- 调用外部 API（真实环境，非 mock）

以下操作可以自动执行，不需要问我：
- git add / commit（本地提交）
- 创建/编辑文件
- 运行测试
- 安装 devDependencies

---

## 会话交接规则（MUST）

### R11：收工时必须写交接契约

**规则**：当用户说"交接"、"收工"、"结束"，或当前会话内容复杂（涉及多个文件修改、未完成任务、踩过坑），必须主动将进度写入 `memory/progress.md`，使用 `memory/exit-contract.template.md` 的格式。

**等级**：**MUST**

**关键约束**：
- "已尝试但失败的方案"栏**必须填写**，它防止下次会话重复犯同样的错
- "进行中"栏必须精确到文件路径和函数名，不能含糊描述
- 写完后告知用户："✅ 交接契约已写入 memory/progress.md"

**格式参考**：`memory/exit-contract.template.md`
