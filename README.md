# openGauss 日志与事务优化模块开源文档

适用范围：openGauss 3.x/5.x  
目标读者：DBA、后端/平台工程师、SRE、对数据库性能与稳定性有要求的团队

## 背景与目标
日志与事务优化模块的目标是以最低的侵入成本，系统化地采集 openGauss 运行时日志与事务指标，识别慢 SQL、锁等待与死锁风险、WAL 与检查点压力、提交延迟与抖动来源，并给出可执行的优化建议与验证方法，帮助在不改业务逻辑的前提下提升吞吐与稳定性。

## 架构与边界
- 数据源：openGauss 服务器日志（`csvlog`/`stderr`/`syslog`）、`pg_stat_activity`、`pg_locks`、`pg_stat_bgwriter`、`pg_stat_io`（若版本支持）、WAL/Checkpoint 相关统计视图。
- 能力边界：只做观测、分析与建议生成；不直接改写业务 SQL 与库表结构；可输出自动化变更脚本但需人工审核执行。
- 部署形态：可作为独立服务（日志收集与分析）、也可嵌入现有平台任务流；与 openGauss 本身解耦，不需要修改数据库源码。

## 快速开始
1) 启用并规范化日志
```sql
-- 开启日志收集（需重启）
ALTER SYSTEM SET logging_collector = on;
-- 统一日志格式，便于解析
ALTER SYSTEM SET log_destination = 'csvlog';
ALTER SYSTEM SET log_line_prefix = '%m [%p] user=%u,db=%d,app=%a,client=%h ';
-- 慢 SQL 阈值（毫秒）
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1s
-- 控制语句级别日志，生产建议限制到 DDL
ALTER SYSTEM SET log_statement = 'ddl';
-- 滚动策略
ALTER SYSTEM SET log_rotation_age = '1d';
ALTER SYSTEM SET log_rotation_size = '1GB';
SELECT pg_reload_conf();
```

2) 准备事务观测视图（只读查询）
```sql
-- 当前活动会话（含阻塞信息）
SELECT
  pid,
  usename,
  datname,
  application_name,
  client_addr,
  state,
  wait_event_type,
  wait_event,
  query_start,
  now() - query_start AS duration,
  query
FROM pg_stat_activity
ORDER BY query_start NULLS LAST;

-- 锁与阻塞链路
SELECT
  bl.pid               AS blocked_pid,
  a.usename            AS blocked_user,
  bl.locktype,
  bl.mode              AS blocked_mode,
  kl.pid               AS blocking_pid,
  ka.usename           AS blocking_user,
  kl.mode              AS blocking_mode,
  a.query              AS blocked_query,
  ka.query             AS blocking_query,
  now() - a.query_start AS blocked_duration
FROM pg_locks bl
JOIN pg_stat_activity a ON bl.pid = a.pid
JOIN pg_locks kl ON bl.locktype = kl.locktype
                  AND bl.database IS NOT DISTINCT FROM kl.database
                  AND bl.relation IS NOT DISTINCT FROM kl.relation
                  AND bl.transactionid IS NOT DISTINCT FROM kl.transactionid
                  AND bl.classid IS NOT DISTINCT FROM kl.classid
                  AND bl.objid IS NOT DISTINCT FROM kl.objid
                  AND bl.pid <> kl.pid
JOIN pg_stat_activity ka ON kl.pid = ka.pid
WHERE NOT bl.granted;
```

3) 建议安装统计扩展（若环境允许）
```sql
-- 统计语句级别性能数据
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
SELECT pg_reload_conf();
```

## 配置建议（生产基线）
- `logging_collector = on`：开启独立日志收集器，避免与标准输出混杂。
- `log_destination = 'csvlog'`：结构化日志便于解析。
- `log_line_prefix = '%m [%p] user=%u,db=%d,app=%a,client=%h '`：包含时间、PID、用户、库名、应用、客户端。
- `log_min_duration_statement = 500~1000`：从 0.5–1s 开始识别慢 SQL；高并发 OLTP 建议 200–500ms。
- `log_statement = 'ddl'`：避免海量 DML 日志造成 I/O 压力。
- `log_rotation_age/size`：结合磁盘与保留周期制定滚动策略。
- `track_io_timing = on`：可细分 CPU vs IO 归因（开启后有轻微开销）。
- `synchronous_commit`：对低延迟高吞吐场景可评估 `off`（可容忍极端故障下少量事务丢失）。
- `enable_thread_pool = on`（openGauss 特性，按需评估）：提升多核利用率与连接管理效率。

## 日志采集与解析
- 采集方式：文件轮询（tail/cat）、对象存储拉取、Syslog/Fluent* 转发；优先使用 `csvlog`。
- 关键字段：
  - 时间戳 `timestamp`、进程 `pid`、会话用户/库、客户端、应用名。
  - 级别：`LOG/ERROR/WARNING/DETAIL/STATEMENT`。
  - 语句时长：`duration: 1234.567 ms`。
  - 错误栈：约束冲突、唯一键冲突、死锁、连接超时等。
- 解析规则：
  - 统一时区，采用数据库服务器时区。
  - 多行错误栈聚合为单事件；配对 `ERROR` 与随后的 `STATEMENT`。
  - 慢 SQL 与锁等待分别归档，便于后续画像与建议生成。

## 事务诊断与优化方法
1) 慢 SQL 分析
- 使用 `EXPLAIN (ANALYZE, BUFFERS, TIMING)` 获取真实执行路径与代价。
- 关注指标：循环嵌套、全表扫描、排序/哈希溢出、回表开销、索引选择性。
- 优化手段：索引补充（含联合与覆盖索引）、谓词下推、避免隐式类型转换、去除跨类型比较导致的索引失效、参数化查询。

2) 锁与阻塞
- 识别阻塞链路（上文 SQL）；统计累计阻塞时长与 Top N 阻塞者。
- 降低锁范围与持有时间：将长事务拆分、避免在事务内执行业务外操作（IO/网络调用）、及时显式提交。
- 降低冲突：合理粒度的索引与业务分片，减少热点行；必要时采用悲观/乐观并发策略调整。

3) 死锁防治
- 统一资源获取顺序（表/行/索引）；避免交叉更新。
- 批量操作改为稳定顺序（如主键升序）。
- 通过日志中 `deadlock detected` 与阻塞图定位相互依赖。

4) 提交路径与 WAL 压力
- `synchronous_commit`：对极致低延迟应用评估 `off`，但必须具备异地多副本或消息恢复能力。
- `commit_delay/commit_siblings`：微调组提交，平衡延迟与吞吐。
- `wal_level/checkpoint_timeout/max_wal_size`：根据写入速率与磁盘制定检查点策略，避免频繁全量刷盘。

5) 内存与排序
- `work_mem`：基于典型查询的排序/哈希峰值评估，避免频繁落盘；按会话维度生效，不可全局过大。
- `maintenance_work_mem`：加速索引构建与 VACUUM。

6) 版本特性与线程池
- `enable_thread_pool`：在高连接数场景减少上下文切换与连接占用；需结合业务模型与 CPU 拓扑评估。
- 关注 openGauss 增强特性（如存储引擎与 REDO 路径优化），选择与场景匹配的配置。

## 建议生成与变更脚本
- 建议类型：索引建议、参数建议、SQL 重写建议、会话治理建议（连接池化、长事务切分）。
- 输出形式：结构化建议（JSON/YAML）与可选 SQL 脚本（`ALTER SYSTEM SET ...`、`CREATE INDEX ...`）。
- 审核流程：所有自动化脚本必须由 DBA 合规审核后执行；生产环境采用窗口与灰度发布。

## 验证与评估
1) 基准与回归
- 使用 `pgbench`/`oltpbench` 在代表性数据规模与并发下对比前后：TPS、P99 延迟、错误率。
- 观测变更前后指标：慢 SQL 数量与时间、阻塞占比、WAL 写入速率与检查点时长、IO 等待与 CPU 利用率。

2) 变更策略
- 先在预生产环境验证功能正确性与性能收益，记录试验参数与数据基线。
- 采用分阶段灰度发布与回滚预案，明确触发阈值与观测指标。

## 监控与告警
- 指标：慢 SQL 数量与分布、阻塞时长/数量、死锁事件、会话活跃度、检查点间隔与时长、WAL 写入速率、IO 等待、CPU 使用率。
- 告警阈值示例：
  - 单条语句 `duration > 2s` 连续 5 次。
  - 阻塞链路长度 > 3，累计阻塞 > 30s。
  - 10 分钟内死锁事件 ≥ 1。
  - 检查点耗时 > 30s 且 WAL 写入突增。
- 可对接 Prometheus/ELK 等监控栈；将分析结果以事件形式推送。

## 安全与合规
- 日志脱敏：过滤或掩码敏感字段（身份证、手机号、令牌等）。
- 权限边界：只读查询统计视图，避免对生产造成写入风险。
- 保留策略：按业务合规要求制定日志留存与归档周期；遵循加密与访问审计。

## 故障处理清单
- 慢 SQL 爆发：先定位 Top N，通过 `EXPLAIN` 与索引覆盖优化；立即调低 `log_min_duration_statement` 做短期画像。
- 锁等待积压：定位阻塞者并与业务侧协同调整操作顺序；必要时终止长时间阻塞会话。
- 死锁频发：梳理访问顺序并在应用侧统一排序；评估拆分事务。
- WAL/Checkpoint 抖动：优化检查点参数与 IO 带宽；评估 `synchronous_commit` 与组提交参数。

## 常见问题（FAQ）
- 是否需要重启数据库？`logging_collector` 等少数参数需重启，其余大多支持在线 `pg_reload_conf()`。
- 开启统计是否有开销？`pg_stat_statements` 与 `track_io_timing` 有一定开销，生产需评估。
- 线程池适合所有场景吗？高连接数与多核场景侧收益明显，小并发或长事务型负载需实测。

## 贡献指南
- 议题分类：解析（log parser）、规则（rules/heuristics）、建议生成（advise）、变更脚本（patches）、可视化（ui）。
- 开发建议：为每条规则提供可复现实验与回归案例；所有建议需附带适用场景与风险说明。
- 提交与评审：采用标准化 PR 模板与自动化检查（lint/格式/示例覆盖）。

## 版本与兼容
- 文档以 openGauss 3.x/5.x 与 PostgreSQL 兼容配置为参考，具体 GUC 名称与行为以 `SHOW ALL` 及官方手册为准。
- 部分视图与统计在不同版本存在差异（如 `pg_stat_io`），请按环境实际调整。

## 许可
推荐使用 Apache-2.0 或 GPL-3.0（含规则与脚本），遵循第三方依赖的许可证约束。

---
附：示例优化清单（可据此生成自动化建议）
1) 慢 SQL 阈值从 1s 调整到 500ms，采集更多边缘样本用于画像。
2) 为读多写少的热点查询补充覆盖索引，减少回表。
3) 对大排序/哈希操作评估 `work_mem` 峰值并按会话调整。
4) 对短事务高吞吐场景评估 `synchronous_commit = off` 与组提交参数。
5) 统一批处理的资源获取顺序，降低死锁概率。

