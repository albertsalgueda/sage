# Experiment 1 v2 — Comparison Results

**Date:** 2026-03-30 05:43

| Metric | opus_basic | opus_few_shot | opus_full | sonnet_basic | sonnet_few_shot | sonnet_full |
|--------|--------|--------|--------|--------|--------|--------|
| Overall Grade | **81.7%** | **84.8%** | **89.7%** | **86.5%** | **87.3%** | **85.3%** |
| SQL Tables | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Primary Keys | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 4GL Keywords | 47.1% | 82.3% | 94.1% | 82.3% | 70.6% | 94.1% |
| Ranking Query | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% |
| SQL Validity | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Sage Conventions | 80.0% | 90.0% | 90.0% | 100.0% | 90.0% | 90.0% |
| Artifact Completeness | 76.5% | 64.7% | 76.5% | 76.5% | 76.5% | 70.6% |
| Business Logic | 90.9% | 90.9% | 100.0% | 81.8% | 100.0% | 90.9% |
| Similarity (SQL) | 6.9% | 3.2% | 4.0% | 11.6% | 4.1% | 4.9% |
| Similarity (4GL) | 7.0% | 5.6% | 12.0% | 5.6% | 5.7% | 8.6% |

## API Usage

| Config | Input Tokens | Output Tokens | Model |
|--------|-------------|--------------|-------|
| opus_basic | 2461 | 7312 | claude-opus-4-20250514 |
| opus_few_shot | 3781 | 8192 | claude-opus-4-20250514 |
| opus_full | 5339 | 7207 | claude-opus-4-20250514 |
| sonnet_basic | 2461 | 8001 | claude-sonnet-4-20250514 |
| sonnet_few_shot | 3781 | 8192 | claude-sonnet-4-20250514 |
| sonnet_full | 5339 | 8065 | claude-sonnet-4-20250514 |