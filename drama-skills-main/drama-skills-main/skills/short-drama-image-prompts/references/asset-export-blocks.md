# 外部工具资产直出块（C/S/P 编号导出）

> 把《视觉设定.md》《图片提示词.md》的条目**导出**为可直接粘进即梦 / Nano Banana Pro /
> Midjourney 的编号提示词块。这是**导出视图**：原项目文档仍是唯一真相，导出块不回写、不参与
> `creator_markdown_check.py` 核对。

## 什么时候生成

- 创作者要在项目外出图（自带工具/第三方平台）时
- 项目锁定了风格包，且创作者想把"风格 + 锚点"一次性带走时

## 编号规则

| 前缀 | 来源 | 编号 |
|------|------|------|
| C（Character） | 视觉设定·人物条目 | C01, C02…（同一人物多视角/多造型加后缀：C01a 正面、C01b 战损） |
| S（Scene） | 视觉设定·地点条目 | S01, S02… |
| P（Prop） | 视觉设定·道具条目 | P01, P02… |

编号只在导出块内有意义；与项目内 `IMG-...` 的对应关系写在块尾注释里。

## 单块格式

```markdown
### C01 — 叶青云·正面全身

[风格前缀], 中文古风武侠, 灰蓝束腰劲装 male warrior standing front view,
full body, 素色交领劲装, 背长剑剑穗, 高马尾束发带, neutral studio-gray backdrop,
soft even studio light, 8k, photorealistic / clean 2D cel style per project
Negative: text, watermark, extra fingers, distorted face

<!-- 来源: 视觉设定.md·人物「叶青云」; IMG-SH-001; 风格包: wuxia-film -->
```

## 生成规则

1. **锚点逐字带走**：人物块的五官/发型/服装段取《视觉设定.md》识别锚点与连续性锁，
   地点块取 [地点板] 配方要点，道具块取道具板的形制/材质——导出不是改写
2. **风格前缀**：项目锁了风格包时，前缀 = 包名中文 + 材质/色盘关键词一行
   （从 `short-drama-develop/references/style-packs.md` 的对应包提取）；未锁包则用《视觉设定.md》风格声明句
3. **画幅/用途标注**：块尾注明建议画幅（人物参考板 16:9 横、头像特写 1:1、地点板 16:9）
4. **负向词**：统一带 `text, watermark, extra fingers, distorted face`，可按板式追加
5. **一致性提示**：导出块文件头写一行提醒——同一人物的多视角/表情格请用同一张参考图 + 同一风格前缀，外部平台没有连续性锁，靠复用块保一致

## 产物

- 路径：`剧集/<EP>/导出/asset-blocks.md`（或单文件放项目根 `导出/`，创作者点名即改）
- 与角色参考板三段式的关系：C01 块可整体替换参考板配方的服装/发型段在外部平台出图；
  项目内生产仍走 `character-reference-board.md` 原配方

## 红线

- 导出块与项目文档不一致时，**以项目文档为准**，重新导出
- 不把导出块当 `IMG-...` 使用；项目内引用仍走既有 ID 体系
