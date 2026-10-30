# 第三方来源与许可声明（仓库根，跨包）

本仓库含两个技能包：`drama-skills-main/`（短剧产线，MIT）与 `chinese-novelist-skill-master/`
（小说创作，MIT）。本文件登记**跨包**的外部来源与许可边界；drama 包的逐条取用记录在其包内
`drama-skills-main/drama-skills-main/THIRD_PARTY_NOTICES.md`，本文件不重复其内容，只登记 novelist 侧
与两侧共同的原则。

## 一、chinese-novelist 侧

### 已内联的来源

- `One-flower-OneFlower`（Apache License 2.0，全文唯一许可、无 NOTICE 文件、
  `Copyright 2026 sleepykino`）：仅取其**量化去 AI 味的概念**（比喻与破折号每千字密度上限、
  连续三句字数是否相同、连续三段行数是否相同、裸对话标签占比、微表情套话词表的方向）与
  **文风条的思路**（武侠三包的「招式有名目、兵刃有形制、以巧胜力、不用能量对轰」类要求）。
  落点：`chinese-novelist-skill-master/scripts/check_text_metrics.py` 与
  `references/quality-checklist.md` 的量化一节、`SKILL.md` 第 11 步的子条目。
  改写声明：阈值、指标定义、词表与判定分级全部按本套件口径重写，未复制其条目原文与句子；
  其「对话须锚定可见表情」与本套件既有规则的冲突**未被裁决**，只报告不判违规。
  合规义务：Apache-2.0 §4 要求分发时附许可副本、注明修改、保留原版权与署名。
  本仓库当前只在本机使用；若对外发布或推送到公开远端，须补附 Apache-2.0 许可副本与出处。

### 明确**未**内联的来源（copyleft 边界）

- `opencode-novel-plugin-main`：**AGPL-3.0-or-later**，且 README 自陈融合 GPL-3.0／AGPL-3.0 项目，
  其 `skills/novel-wuxia/SKILL.md`（407 行：功法体系、门派架构、战斗场景写法、桥段库、兵器谱、
  江湖规矩）是本机唯一成体系的武侠技法文档。**不内联**：AGPL 的 copyleft 与本仓库 MIT 加公开远端
  的组合存在传染风险；且其步骤绑定插件专有工具名与 `.novel/` 目录约定，脱离宿主不可执行。
- `QMAI-main`：**GPL-3.0**（`private:true`）。其中 `SkillHub/ZhengwenSkill/combat-action`（六步战斗流程）、
  `SheDingSkill/power-system`（力量体系四栏代价表）、`de-ai-writing/references/novel-de-ai-rules.md`
  （六类禁词与终检清单）颗粒度有价值，**同样不内联**。另注：`good-writing/style-dna.md` 逐字引用了
  第三方散文约 350 字，属危险素材，一律不使用。
- 上述两包的内容如需吸收，只走两条安全路径：作为外部读物人工翻查（不安装、不复制进本仓库），
  或由创作者用自己的话转述概念、再据转述撰写——来源链落在创作者的表述，不在对本包正文的改写。
  `references/wuxia-prose.md` 即按此原则**自拟**，未参考上述正文。

### 与武侠打斗相关的既有分工（避免越层与双权威）

`SKILL.md` 第 5.7 条与短剧交接段确立的口径：**小说层不预先限制镜头**。招式拆镜、攻防相位、
冻结关键帧、景别与运镜归 `$short-drama-storyboard`；力量体系、门派谱系、身法签名、古典语感、
代价账目归小说层（`wuxia-prose.md`、`outline-template.md` 的力量体系小节、
`character-template.md` 的可选字段）。两份知识文件在文件头各自声明了这条边界。

## 二、跨包共同原则

1. 先读许可并分层看：代码／文档与数据资产可能是不同许可，ND 与 copyleft 条款优先于技术可读性
2. 只内联概念与判据，逐条改写成套件自己的字段语言；条目原文、示例正文、展示素材不搬
3. 每处内联在落点就近注明来源与「已改写」，并在本文件与包内 notices 登记取用层级与未采用项
4. 与既有权威冲突的参数类内容（阈值表、色表、模型清单、时长口径、镜头规范）不内联，
   未决的口径不代创作者裁决
5. 不引入新的运行时依赖（外部宿主、加密检索脚本、需联网或建模工具的流程）
