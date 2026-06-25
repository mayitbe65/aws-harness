# 识别功能需求规格 — recognize

## 1. 概述

用户上传作业照片，系统通过 Vision API 识别图中的题目文字，返回结构化识别结果。

## 2. 输入约束

| 字段 | 约束 |
|------|------|
| 文件类型 | 仅接受 JPEG、PNG、WebP；其他格式必须拒绝 |
| 文件大小 | 不超过 10MB；超过必须拒绝 |

## 3. 识别结果结构

识别成功时返回：

```
recognized_text   string   识别出的完整题目文字
confidence        float    可信度，范围 [0.0, 1.0]；缺失时视为 0.0
has_formulas      bool     是否含数学公式，默认 false
has_diagrams      bool     是否含示意图/图表，默认 false
```

## 4. 质量分级（Rule R4）

根据 `confidence` 和文本内容，结果分三级：

### HIGH（高质量）
- 条件：`confidence >= 0.7` **且** 文本通过有效性检查
- 含义：可直接存入数据库，无需人工审核

### MEDIUM（中等质量）
- 条件：`0.0 <= confidence < 0.7` **且** 文本通过有效性检查
- 含义：识别成功但置信度较低，需标记 `needs_review = true`，提示用户确认

### LOW（低质量 / 失败）
- 触发任意一条即判为 LOW：
  1. `confidence` 不在 `[0.0, 1.0]` 范围内
  2. 文本长度（strip 后）< 5 字符
  3. 文本长度（strip 后）> 10000 字符
  4. 文本命中垃圾模式（见 §5）
- 含义：识别失败，不存储，提示用户重新上传

## 5. 垃圾数据判定

以下任意一项成立，文本视为垃圾数据（→ LOW）：

**正则模式**（整个文本，strip 后匹配）：
- `^\[.*无法.*识别.*\]$`
- `^\.+$`（纯英文句点）
- `^·+$`（纯间隔号）
- `^\s*$`（纯空白）

**关键词**（出现在文本任意位置）：
- `无法识别`
- `[image]`
- `[chart]`
- `模糊`

## 6. 重试逻辑（Rule R8）

- Vision API 调用失败时，最多重试 **3 次**（含首次，共 3 次尝试）
- `ThrottlingException`：等待后重试，等待时间按指数退避（2^attempt 秒）
- JSON 解析失败：等待后重试
- 非限流类 `ClientError`（如 `AccessDeniedException`）：**立即放弃，不再重试**
- 3 次全部失败：返回空结果（`null`），调用方标记为需人工审核

## 7. API 响应格式

```
status             "success" | "failed"
quality            "high" | "medium" | "low"
result             识别结果对象（LOW 时为 null）
message            用户可读的说明文字
needs_manual_review  bool
photo_url          已上传照片的存储 URL（可为 null）
```

## 8. 安全与隔离

- **不得**在前端暴露 Vision API 密钥（Rule R3）
- 所有 AI 调用必须经后端代理

## 9. 超出范围

本规格不覆盖：
- 照片存储（S3 上传逻辑）
- 用户认证
- 题目持久化（写入数据库）
