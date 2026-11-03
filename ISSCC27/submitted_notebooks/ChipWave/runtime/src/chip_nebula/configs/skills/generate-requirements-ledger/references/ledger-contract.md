# Requirements Ledger Contract

## Document shape

```json
{
  "schema_version": "1.0",
  "source_artifact_id": "art-source",
  "source_digest": "sha256:...",
  "document_kind": "requirements",
  "classification_evidence": [
    {"locator": "source.md#L1-L40", "reason": "目标级描述，缺少完整实现决策"}
  ],
  "requirements": [
    {
      "id": "REQ-A1B2C3D4E5F6",
      "kind": "functional",
      "text": "分支判定成立时冲刷流水线中的错误路径指令",
      "evidence": [
        {"locator": "source.md#L72", "quote": "分支跳转后不得提交错误路径指令"}
      ],
      "status": null
    }
  ],
  "source_inventory": [
    {
      "locator": "source.md#L72",
      "digest": "sha256:...",
      "disposition": "mapped",
      "requirement_ids": ["REQ-A1B2C3D4E5F6"],
      "reason": ""
    }
  ]
}
```

`kind` 至少支持 `functional`、`interface`、`protocol`、`state`、`pipeline`、`timing`、
`clock_reset`、`register`、`exception`、`integration`、`verification`、`performance`、
`power`、`physical`、`assumption`、`definition`。类别用于完整性审计，不改变原文语义。

ID 取规范化字符串
`source_digest + "\n" + primary_locator + "\n" + normalized_atomic_claim` 的 SHA-256
前 12 位大写十六进制，格式 `REQ-XXXXXXXXXXXX`。修订措辞但语义与主 evidence 不变时保留 ID；
拆分出的新原子需求使用各自 claim 计算新 ID。

`ledger-shape` Gate 只做第一版需要的确定性检查：requirements 输入必须存在 ledger，
detailed_design 输入不得存在 ledger；必需字段类型正确；source artifact/digest 匹配；ID 唯一；
evidence 非空；所有 status 均为 `null`。语义是否穷举完整由独立 Reviewer 判断，不在 Gate 中
实现复杂的增量差异审计。

返工时改用 `ledger-status-protection` Gate：按稳定 requirement ID 对比输入和输出 ledger；
输入输出中同 ID 条目的 `status` 必须逐值相同；新增 ID 的 `status` 必须为 `null`。Gate 不判断
Author 如何修改其他字段，也不判断删除或改 ID 是否合理，语义正确性由下一轮 Reviewer 对照
原始 source 全量复核。
