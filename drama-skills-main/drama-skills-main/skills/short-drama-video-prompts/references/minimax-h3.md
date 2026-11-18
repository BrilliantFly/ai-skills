# MiniMax H3 提示词方言

只在目标档案明确写 `target_video_model: minimax-h3` 时使用。推荐档案：

```json
{
  "target_video_model": "minimax-h3",
  "video_prompt_dialect": "minimax-h3",
  "video_prompt_language": "en",
  "native_duration_seconds": {"min": 4, "max": 15},
  "supported_generation_modes": ["text", "first_frame", "first_last_frame", "reference"],
  "audio_generation": "same_pass"
}
```

H3 的结构字段用英文；这不等于把中文对白翻成英文。每句中文对白保持原文并写成
`<d>[Chinese] 逐字台词</d>`，由稳定说话人 ID 引出。不要在对白前增加外语、语气词或未写入剧本的开场句。
**例外**：走本机 ComfyUI 导演台直连时不用 `<d>`，改写中文引号直引，见
[本机导演台音轨硬约束](#本机导演台comfyui-直连的音轨硬约束)。

点名 MiniMax H3 只选定模型与方言，不表示创作者选了文生视频。当镜头需要人物、场景、道具或起始构图一致性时，
先按主 Skill 完成真实图片发现与缺口列表。有任何必要图片仍缺失时，不因 H3 同时支持 Base 模式就默默改用文生视频。

## Base / 首帧 / 首尾帧

文生视频、首帧和首尾帧使用三段结构：

```text
integrated_multimodal_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: ...
```

- `integrated_multimodal_description` 按 `[Shot 1]`、`[Shot 2]` 写画面、动作、说话人、逐字对白和同步声音；
  单镜也保留 `[Shot 1]`。第一镜不加切镜时间戳，后续切镜用 `[Shot 2] At 00:03.500, ...`，时间递增且落在本次生成时长内。
  小样本观察到切点接近要求，但仍有偏差；交付要求精确时应检查实际切点并在剪辑中调整。
- `overall_soundscape` 汇总环境声、物理音效和非语言人声，不重复对白；对白事件留在上面的主时间线。
  无非画内配乐时写 `non_diegetic_music: N/A`，不要留空让模型补乐——这一条有实测支撑，见
  [无对白镜](#无对白镜)。
- 首帧模式从输入帧的可见姿态开始；首尾帧模式只能到达上游已接受终点，不发明过渡后的新状态。

## 无对白镜

在 `overall_soundscape` 写清全镜的环境声、音效或静默。
**`craft_default`**：优先描述需要的声轨；必要时可以补「无对白」，不因用了否定句判错。
人物嘴部状态按实际表演写，不能把无对白一律改成全程闭嘴。

无非画内配乐时保留 `non_diegetic_music: N/A`。小样本中省略这一层出现过额外配乐，
显式写空可作为 H3 的默认写法，不保证所有生成都遵守。
时间线总结只列本镜实际存在的声音层，不照抄包含对白的模板。

## 选哪一种模式

模式由本镜「输入参考图」里各槽位的 `用途` 决定，不由“想不想用多模态”决定：

| 本镜绑定的图 | H3 模式 | 正文结构 |
|---|---|---|
| 没有图，且创作者已明确选择文生视频 | Base（文生） | 三段 |
| 只有一张 `用途：起始帧` | `first_frame` | 三段 |
| 一张 `用途：起始帧` + 一张 `用途：结束帧` | `first_last_frame` | 三段 |
| 其他任何组合（起始帧与人物/地点/道具图同时存在，或只有人物/地点/道具图） | `reference`（full-reference） | 六段 |

`REF-...` 和 `PLAN-...` 在这张表里同权：模式由 `用途` 组合决定，与图片此刻在不在项目里无关。
创作者在 H3 的网页界面里自己挂图时，正文照这张表写，`顺序` 就是他挂图的次序。

H3 官方另有只给尾帧、由模型推断开场的 L2VA 模式。本套件不使用它：开场由分镜已接受的起点决定，
把它交给模型推断会让 `SHOT-...` 的起点失去权威。因此 `结束帧` 只在同时绑定 `起始帧` 时出现。

第四行是最常见、也最容易写错的一种。H3 的首/尾帧输入与参考输入**互斥**，所以「起始帧 + 角色板 +
场景板」不能拆成 `first_frame` 加 `reference_image`：整组统一走 full-reference，起始帧也以
`reference_image` 送入，正文按下面的标签编号引用。用哪一种模式在《视频提示词.md》里由 `用途` 组合读出，
不写进「生成方式」字段——该字段仍只有「文生视频」和「图生视频」两个值。

## Full-reference

任何 `reference_image`、`reference_video` 或 `reference_audio` 进入任务时，改用六段结构，段名和正文说明均用英文：

```text
subject_definitions: ...
summary: ...
retention_analysis: ...
detailed_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: ...
```

**这六段是一条提示词，一次整体提交。** 它们是同一个 `MOTION-...` 的可复制正文，从第一段到最后一段
一起放进那一次生成的提示词框，不是六次生成、也不是只提交第一段。三段结构的 Base / 首帧 / 首尾帧同理。
默认一镜一次生成，下一镜换成它自己那条完整正文；几个镜头装进同一次生成的条件见
[多镜容器](#多镜容器每切一张关键帧)。

### 素材标签怎么编号

正文用 `<Picture N>`、`<Video N>`、`<Audio N>` 指向本次 job 的实际素材，`<Subject N>` 指向可复用的可见内容。
**编号按同类素材在本镜「输入参考图」里的 `顺序` 递增**：第 1 张图片是 `<Picture 1>`，第 2 张是 `<Picture 2>`，
视频和音频各自从 1 开始。生产端 compiler 按同一顺序附加引用契约，所以文档里手写的编号必须和 `顺序` 一致；
两套编号不一致时模型会收到互相矛盾的素材说明，而接口不会报错。

因此写 full-reference 正文前，先把本镜的槽位按 `顺序` 列一遍，例如：

```text
REF-SHOT-START（顺序：1；用途：起始帧）  -> <Picture 1>
REF-XIAOYU-SHEET（顺序：2；用途：身份）  -> <Picture 2>
REF-STUDY-PLATE（顺序：3；用途：地理）    -> <Picture 3>
```

这份清单不依赖文件路径，只依赖 `顺序` 和 `用途`，所以图片由创作者自己挂载时它照样成立：
把上面的 `REF-` 换成 `PLAN-`，定位符换成 `SHOT-...` 或 `IMG-...`，正文一个字都不用改。
创作者按 `顺序` 在生成界面里挂图，`<Picture N>` 就对得上。

`PLAN-...` 的图套件没有看过，所以 `subject_definitions` 和 `retention_analysis` 写的是
**这张图按它的 `用途` 必须保留什么**，事实取自《视觉设定.md》和本镜冻结关键帧，而不是对像素的观察结论。
两种槽位的句式相同：`用途` 决定保留什么，本来就不是看图看出来的。不要因为图没进项目就改写成
「未验证」或省略保留强度——那会让执行端收不到本镜真正的保留要求。

`subject_definitions` 把每个主体绑到它的标签上，句式为
`<Subject 1> is the ... in <Picture 2>, with ...`；`retention_analysis` 逐条写保留强度和出现的镜次，
视觉素材用 `fully_preserved`、`partially_preserved`、`attribute_transfer`、`weak_reference`，
音频素材用 `fully_copy`、`partially_copy`、`reference`、`weak_reference`，例如
`<Subject 1> (appears in [Shot 1]): fully_preserved - 短发轮廓、连帽外套配色与鞋型保留`。
每个标签在六段里保持同一写法，不留下没有定义的标签。

### 每张图带什么、不带什么

`用途` 决定这一张在正文里被要求保留什么，具体到哪几项由该槽位自己写下的 `控制` 范围决定。

需要保留构图时，在 `控制` 中点名构图、站位或机位高度。
`不得控制` 记录不应照搬的内容，生成后仍需检查实际参考影响，不能把文字声明当成模型保证。
本镜没有起始帧时，地点图会把景别拉宽，要在 `detailed_description` 里写具体取景，见
[目标模型能力档案](target-model-profile.md#参考条件方式)。

`起始帧` 只锚定开场构图与姿态，`身份` 锚定这个人跨镜不变的长相与体态（角色板同时固定本集造型时，
`控制` 里会写明），
`地理` 只锚定空间关系，`造型状态` 只锚定服装与损污。把这条差异写进 `retention_analysis`，
不要让角色板顺带决定构图，也不要让场景板顺带决定人物长相。

角色始终使用同一个说话人 ID；中文对白只出现在 `<d>[Chinese] ...</d>` 内。禁字幕写进可见文字约束，
与获准的画内文字分开。
Full-reference 的逐字对白与同步声音放在 `detailed_description` 的对应事件里，`overall_soundscape` 仍只汇总底声与音效。
不要为了“多模态”把所有资产图都带上；每镜只绑定它真正可见且需要保持的起始帧、人物、地点或关键道具图。

### 一个完整例子

分镜里的槽位（三张图：本镜起始帧、角色板、场景板）：

```markdown
- 输入参考图：REF-SHOT002-START（顺序：1）· 剧集/EP001/制作成果/images/SHOT-EP001-002.png《SHOT-EP001-002 起始帧》（用途：起始帧；控制：起始构图、双人站位；不得控制：尚未发生的动作、终态）；REF-XIAOYU-SHEET（顺序：2）· 输入/参考图/小雨定妆.png《小雨定妆照》（用途：身份；控制：脸型、发型剪影、身高比例；不得控制：构图、动作、表情）；REF-STUDY-PLATE（顺序：3）· 输入/参考图/家庭书房.png《家庭书房场景图》（用途：地理；控制：书桌方位、书架墙、灯位；不得控制：人物身份、动作、道具状态）
```

对应的 full-reference 正文（`生成方式：图生视频`，模式为 `reference`）：

```text
subject_definitions: <Subject 1> is the elementary-school boy in <Picture 2>, with a round short black haircut and a light grey-blue hooded jacket over a white inner shirt. <Subject 2> is the home study in <Picture 3>, with the desk against the window wall, a full bookshelf on the left and a warm desk lamp. <Picture 1> is the opening composition of this shot.
summary: The boy leans over an open textbook at his desk and stops when he notices the printed map.
retention_analysis: <Picture 1> (appears in [Shot 1]): fully_preserved - overhead framing, desk edge position and the boy's seated placement open the shot exactly as supplied. <Subject 1> (appears in [Shot 1]): fully_preserved - face shape, hair silhouette and the jacket-over-shirt layering stay identical; his pose and expression are set by this shot, not by <Picture 2>. <Subject 2> (appears in [Shot 1]): partially_preserved - desk orientation, bookshelf wall and lamp position are kept; the props on the desk follow this shot.
detailed_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: N/A
```

三张图各自只负责一件事：`<Picture 1>` 给构图，`<Picture 2>` 给身份，`<Picture 3>` 给地理。
把这条差异写进 `retention_analysis`，生成后检查身份、构图与地理是否分别保留。

### 多镜容器：每切一张关键帧

**`taste_option`**：几个相邻镜头可以装进同一次 full-reference 生成，每切挂它自己的已接受关键帧。
**`craft_default`**：装容器的条件是三条都满足：

- 每个成员镜头都有已接受的起始帧图片（`REF-...` 或 `PLAN-...`，`用途：起始帧`）；缺一张就逐镜生成；
- 成员已接受时长之和在 4–15 秒内，且成员资格与容器算术按 [交付形态](delivery-profile.md) 的多镜容器记账；
- 容器用一份参考清单：各切关键帧按切的顺序排在前面，共用的身份、地点图接在后面，
  `<Picture N>` 按这份清单的 `顺序` 编号，不照抄逐镜时的编号。

正文第一行、`subject_definitions` 之前，写一句对齐句把每张关键帧钉到它那一切的起点：

```text
<Picture 1> aligns with the 0.00-second mark as the opening frame of [Shot 1]; <Picture 2> aligns with the 3.00-second mark as the frame of [Shot 2]; <Picture 3> aligns with the 6.00-second mark as the frame of [Shot 3].
```

`detailed_description` 里后续各切照常写 `[Shot 2] At 00:03.000, ...`，秒数与对齐句一致；
`retention_analysis` 为每张关键帧写它负责的那一切。一组 9 秒三切的小样本（要求 3.0/6.0 秒切）：
每切挂关键帧，切点落在 2.88–3.04 / 6.00–6.04 秒，各切与关键帧的构图相似度接近三次逐镜首帧生成，
生成次数为三分之一；只挂第一切的关键帧时，切点偏到 2.92–3.88 / 5.88–6.21 秒，第 2、3 切的构图
明显偏离关键帧，还出现过一次多出来的切。所以没有逐切关键帧时不装容器。

## 素材数量上限

一次生成最多 1 张首帧、1 张尾帧、9 张 `reference_image`、3 段 `reference_video`、3 段 `reference_audio`；
视频与音频每段 2–15 秒，且各自合计不超过 15 秒。分辨率取 `768P` 或 `2K`（`MiniMax-H3-Max` 另为 `480P`/`768P`）。
超过上限时在分镜阶段按重要性取舍，并写明放弃了哪些参考，不在正文里假装它们仍然生效。

本镜还没有起始帧图片时有两条路：由 `$short-drama-produce` 从 `分镜.md` 的 `SHOT-...` 冻结关键帧生成，
拿到真实文件后由分镜 owner 绑成 `用途：起始帧` 的 `REF-...`；或者由创作者把该镜的冻结关键帧正文复制到
自己的工具里出图，本轮先记成 `PLAN-...（用途：起始帧）`、定位符写本镜 `SHOT-...`。
两种写法本阶段都原样抄入，正文写法相同。

`输入参考图` 只登记参考**图片**。连续段的实际视频不写进这个字段；下面说明支持双输入的执行端
怎样绑定视频与尾帧。当前内置 creator-first 生产选择器尚不能绑定续接视频，投产时按
[交付路线的接口边界](delivery-profile.md#从已生成结果续接)停靠，不把视频路径塞进图片 `REF-...`。

## 连续段

H3 的首/尾帧模式与 full-reference 模式互斥，不能在同一请求混用 `first_frame`/`last_frame` 和
`reference_image`/`reference_video`/`reference_audio`。连续段需要上一段实际视频和实际尾帧时，统一走
full-reference：

- 上一段实际视频：`reference_video`，正文称 `<Video 1>`，控制动作、节奏和声音连续；
- 该视频的实际尾帧：`reference_image`，正文称 `<Picture 1>`，只作为新段开场的可见姿态与构图锚点。

实际尾帧在该模式下使用 `reference_image`，以满足首尾帧输入与 full-reference 输入互斥的接口契约。

## 本机导演台续接（ComfyUI 直连）

走本机 ComfyUI 的 MiniMax H3 导演台时，续接不靠上面的接口契约，靠执行端自带的段间开关。开关在
timeline JSON 的 `output` 里，不在 `global`：

- `output.continuityEnabled`：总开关，默认 `false`。整集 `false` 等于每段独立生成，段间不接力，
  这就是打斗在剪辑点重新起势的机制性原因。
- `output.continuityOverlapFrames`：交接帧数，`0` 表示不重叠。导演台工作流的自带说明给本机建议值是
  **22 帧**（约 0.9 秒），与 `motion_context` 上下文长度一致。
- `global.continuousReference` **不是**这个开关，它是"参考图是否跨段沿用"，别拿它当续接。

生效证据：每段产物同名 `.meta.json` 里 `continuity` 与 `continuity_from_prev` 为 `true`，
`continuity_pipeline` 为 `minimax_h3_motion_context_v9`。整集抽查全为 `false`，说明开关没打开。

起链与断链：同一连续时空的第一段起链，后续段沿用；遇到剪接、时间/地点跳变、换镜头轴线时断链重起。
4step 加速档跑长链时，每 3–4 段用新起始帧重起一次链，避免累积漂移。这条只在本机直连路由下生效，
`$short-drama-produce` 的内置选择器边界不变。

## 本机导演台（ComfyUI 直连）的音轨硬约束

走本机导演台时，同一套 H3 提示词有四处**方言差异**。照网页/API 的写法直接喂给导演台，会出现
「画面对了、台词没了」——这些不是模型能力问题，是执行端解析方式不同。

### 1 对白不用 `<d>` 标签，用中文引号直写

导演台的主提示词由 Qwen3-VL 自由解析，**不认 `<d>[Chinese] …</d>` 这种 API 方言**。
整句塞进 `<d>` 里，模型收到的是「一段带标记的英文结构化描述」，台词常常不落地。
改写成中文自然语言直引：

```text
<Picture 1> 中的令狐冲面向镜头说话，台词逐字为：「前辈这刀，是扶桑的形制。」
口型与台词逐字精准对齐，表情克制。声音完全模仿 <Audio 1> 的音色、语速与气质，吐字清晰、对白突出。
真人实拍质感，中景，黄昏侧逆光。背景干净安静：无音乐、无环境杂音，除对白外无其他声音。
Audio: reference
```

要点：① 角色名只出现一次；② `「」` 只出现一次（一句一镜）；③ 不给台词加说话人前缀
（`令狐冲：「…」` 会让模型把名字也念出来）；④ 不写「谁说话谁的嘴动，另一人保持静默」这类二次指令
——它要求模型同时管理两张脸，反而分散口型落点；⑤ 不把「0.4s / 2.8s / 4.2s」这种分镜时间点转述进来，
多时间点会稀释「念这句台词」的指令。

### 2 参考音频：一镜一音色，且不写 `index`

- 导演台的 `refAudios[]` 槽位是 **0-based**。写成「顺序：1 / 2」会落到空槽，模型拿不到音色 → 输出乱音。
  文档里的「顺序」在提交时换成数组下标（第一段音频 = 槽位 0），或干脆**省略 `index` 字段**按数组顺序挂。
- 一镜只挂**说话人那一条**。挂两条时模型只取一条，或两条都不取、退回念提示词描述。

### 3 帧数：采样走 `17k+5`，但 `length` 要按连续性反算

执行端把每段采样帧数**向上**对齐到 `17k + 5`（5, 22, 39, 56, 73, 90, 107, 124, 141, 158, 175, 192, 209, 226…）。
连续链开启时，每段还多采 `ctx` 帧前文语境、导出前切掉：

```
export_frames = align17k5(length + ctx) − ctx      # ctx = continuityOverlapFrames，默认 22
```

所以 `length ≡ 5 (mod 17)`（124 / 192 / 209 这类）时每段会**多出 12 帧（0.5 秒）**，
`length ≡ 0 (mod 17)`（102 / 119 / 204 这类）时才零漂移。首段无前文语境，恒等于 `length`。

EP001 实测（36 段全填 `17k+5`，设计 4770 帧 / 198.75 秒）：公式预测 5190 帧 / 216.25 秒，
逐段数视频帧实得 **5177 帧 / 215.71 秒**。差的 13 帧分布很规整——**13 段各少 1 帧**，
且全是预测值 `≡ 1 (mod 3)` 的段（124→123、136→135、187→186），属编码器末帧处理。

验收按帧数判、不按容器时长判：**±1 帧算编码舍入，≥2 帧才算丢帧**。容器 `Duration` 恒比帧数折合多
`段数 × 约 16 ms`（AAC 编码延迟），36 段就是 0.58 秒，拿它当标准会误判。

可用档位（24 fps）：`102 / 119 / 136 / 153 / 170 / 187 / 204 / 221` 帧 = `4.25 / 4.96 / 5.67 / 6.38 /
7.08 / 7.79 / 8.50 / 9.21` 秒。分镜阶段就该按这张表取镜长——本技能只负责把已定镜长写进 `length`，
不在这里改秒数；改口径要回分镜阶段（镜型与拆镜规则由 `short-drama-storyboard` 技能管）。
`totalFrames` 必须等于各段 `length` 之和，`durationSec = length / 帧率`。

### 4 `global_prompt` 必须留空

批量（r2v）模式下执行端会把 `global_prompt` **拼接到每一段 prompt 前面**。填了它，每段都会先念一遍
全局描述，段内台词被冲淡。全局风格写进各段内联句，不写进 `global_prompt`。

### 5 提交前五条机械门

1. `Σ length == totalFrames`；每段 `length ≡ (5 − ctx) mod 17`（默认 `ctx = 22` → `length` 取 17 的倍数），
   否则每段多 12 帧，全片按 `段数 × 0.5 秒` 漂移
2. `refAudios` 内无 `index` 字段，且一镜只有一条
3. 每段 `「」` 出现 ≤1 次，且逐字来自《剧本.md》
4. `global_prompt == ""`
5. 每个 `refs[].imageFile`、`refAudios[].audioFile` 在 `input/` 下真实存在

### 6 出片后必须做音频验收

对白是否真的生成，**不能靠「有声音」判断**。逐段抽音轨转写，与剧本台词比字符相似度：
≥0.5 判可用，0.2~0.5 判含糊，<0.2 或空判无语音。

先做一次**对照**：拿一条真实人声参考音频（如 `视觉设定.md` 里登记的声音参考）转写一遍，
确认转写器本身可信，再判生成音频。否则会把「转写器不行」误判成「音频不行」。

实测结论：单轨对口型在 `SOLO` 镜可用，但**发音清晰度不足以承担文学性台词**；短促喊招（2~4 字）
也不稳定。因此剧本层面的兜底是：把台词内容交给 TTS 补配（`reference` 音色参考正好复用），
H3 只负责画面、口型动作与环境声，原声压成底噪。`DUO` 镜尤其如此，不要试图用提示词救。

### 7 渲染模式：分段导出，不要合并导出

`timeline_data.output.exportMode` 默认写 `"segments"`。合并导出（`all`）会把**所有段的像素同时留在内存**
等最后拼接：960×544×3×float32 单帧约 6.3 MB，**总时长超过约 40 秒就会撞内存墙**（60 G 机器上 36 段
4770 帧 = 26.4 GB 像素 + 约 20 GB 权重）。崩溃点在 VideoVAE 解码，Python 层接不住，日志只看到
`access violation`，容易被误判成显存问题。

`segments` 模式每段解码后立即释放，内存恒定，代价是段间不复用采样缓存。

### 8 参考音频必须先标准化，不要直接喂原始 wav

插件用 `lib/audio_io.load_reference_audio` 读参考音频：**按源文件原生采样率解码**（`-ar` 取自探测值）、
`-ac 2` 强制成双声道，然后原样交给官方节点——**不做重采样、不做响度归一、不裁时长、不去头尾静音**。
素材什么样，模型就学什么样。

EP001 实测 8 条参考音色：

| 项 | 实际分布 | 风险 |
|---|---|---|
| 采样率 | 24k / 32k / 48k 三种混用 | 音色克隆的频响基准不一致，同一角色换素材音色会漂 |
| 时长 | 2.35 ~ 8.86 秒（差 3.8 倍） | 太短学不准音色，太长容易把语气/内容一起学进去 |
| 平均响度 | -31.7 dB ~ -11.7 dB（差 20 dB，即 10 倍幅度） | 模型对「说话力度」的判断被参考带偏 |

生成端的输出响度其实很稳（10 段实测 mean 均在 -15.7 ~ -16.6 dB），所以响度差**不会**直接传到成片；
但它会改变模型模仿的「发力程度」，是发音发虚、咬字糊的一个变量。

**统一标准**（同一部剧全部参考音频按此处理）：

| 项 | 目标值 |
|---|---|
| 采样率 | 32 kHz（与 H3 音频 VAE 一致；不确定时统一成 32k，别混） |
| 声道 | 单声道源即可，别用带立体声混响的 |
| 响度 | `-18 LUFS`（或 mean_volume ≈ -18 dB） |
| 峰值 | ≤ -3 dBFS，避免削波 |
| 时长 | 5 ~ 8 秒，纯说话，无背景音乐、无第二人 |
| 首尾 | 切掉开头静音与结尾拖音，第一帧就是字头 |

处理完再写进 `视觉设定.md` 的「声音参考」行，并在分镜表里登记"哪一镜用哪条"。一步到位：

```bash
ffmpeg -i in.wav -af "silenceremove=start_periods=1:start_threshold=-45dB,\
atrim=0:8,loudnorm=I=-18:TP=-3,aresample=32000" -ac 1 out.wav
```

批量处理多条素材时，先统一采样率与响度再做音色对比，否则频响基准不同，听起来像换了个人。

### 9 对白不能指望模型生成，必须自己造音轨（`source` 模式）

**这是 EP001 最大的坑**：用 `audioMode="generate"`（插件默认，prompt 写 `Audio: reference`）
让模型"模仿音色自己说台词"，实测结果是**没有人声**——ASR 转写为空或整段乱语。

机理：H3 的语音走 AV latent 一次推理生成，与画面共用同一套采样预算。
加速档 4~8 step 时，画面刚够成形，音频细节已被蒸馏掉——参考音频只是条件，不提供波形。
把采样提到 20 step 能让语音变清楚，但那是拿 5 倍渲染时间换一句台词，且仍不可控。

**正解：对白轨自己造，`source` 模式原样输出。**

| 项 | 做法 |
|---|---|
| 音频来源 | TTS（如 `edge-tts`）按角色音色逐句合成，或真人录音 |
| 段落音轨 | 该段所有台词按顺序拼接，句间留 0.3~0.5 s，静音补到 `length / fps` 秒 |
| 采样率/响度 | 32 kHz、`-18 LUFS`、峰值 ≤ -3 dBTP（与第 8 节同一标准） |
| 挂载 | 每段 `refAudios` **只挂这一条**（第 0 槽） |
| `audioMode` | `"source"`（不是默认的 `generate`） |
| prompt 尾标签 | `Audio: fully_copy`（不是 `reference`） |

`source` 模式下参考音频仍作为 AV latent 的条件**驱动口型**，输出则直接把这条 wav 混进成片——
两头都对上：口型跟着台词走，人声是清楚的 TTS 原声。

**硬限制**：一镜仍只有**一条**音轨、一个音色。一段里两个角色交替说话时，
`source` 输出的是那条拼好的双人音轨，但模型的嘴型只认"有一条音频在响"，
会把口型落到最显眼的那张正脸上——**双人对话必须拆成一句一镜（SOLO）**，
每个说话人各挂自己那条 TTS 音频。这条在分镜阶段就拆，不在提示词层补救。

**一句一镜的收益**（EP001 复盘）：21 个台词镜拆成 ~40 个 SOLO 镜后，口型准确率、台词可懂度、
可重跑单句的成本三项同时改善；代价是段数变多，但每段变短，总渲染时间基本持平。

### 10 参考图要挂满 9 槽，不要只挂起始帧

执行端上限：`reference_image` **9 张**（`<Picture 1>`…`<Picture 9>`）、`reference_audio` **3 条**、
`reference_video` 3 段。导演台的时间线里 `segments[].refs[].index` 是 **1-based**（与 `refAudios` 的 0-based 相反）。

EP001 实测：36 段**每段只挂了 1 张起始帧**，9 个槽位移空 8 个，47 张素材里的 16 张身份板/场景板/道具板
一张都没进工作流。后果是模型对"这个人是谁、这场在哪拍"没有任何锚点，4step 下几帧就漂成另一个人。

**打斗镜最少 4 张**：起始帧（双人面对面同框）+ A 身份板 + B 身份板 + 本场场景板。
**对话镜最少 3 张**：起始帧 + 说话人身份板 + 场景板。
**物件镜**：物件状态板 + 场景板（可只 2 张）。
超出 9 张时按 `起始帧 > 身份 > 地理 > 造型状态 > 风格` 的顺序取舍，并在分镜里写明放弃了哪几张。

提示词里对应的标签顺序必须与挂载顺序一致（`<Picture 1>` = 起始帧，`<Picture 2>` = A 身份板……），
否则模型会把身份板当构图参考、把起始帧当风格参考。

---

## 时长

**`structural_invariant`（执行端契约）**：MiniMax-H3 的 `duration` 必填，为 4–15 的任一整数秒，
并非只有 5/10/15 三档。网页界面或 job 的时长设置要与分镜时长和正文终点一致；写在提示词里的秒数
不能替代生成设置。短动作在合法镜长内完成并保持已接受终点；超过 15 秒的镜头回分镜按闭合状态拆开。
本阶段不偷改镜头秒数。

`MiniMax-H3-Max` 是另一型号：5–15 秒、480P/768P，仅支持文生和首/尾帧，不支持 full-reference。
不能把本页 H3 的参考音频路径或 4 秒下限套到 Max。

**武打、追赶、抢夺这类高速镜的模式选择** `craft_default`：优先走首帧模式（只挂 `起始帧`），
不挂 `结束帧`——两端都钉住时，执行端会把动作摊成匀速过渡，命中点被拉晚、动作发软。
确需精确落点时仍可用首尾帧，但正文要写时间分配句，把动作压在前段完成、剩余时间停在结果：
`the strike lands by the 2.0-second mark; the remaining time holds the follow-through`。
正文里也不写"slowly / smoothly / in slow motion"这类减速词，速度靠短促动词与方向，
见 [表演与动作时序](performance-action-timing.md#4b-动作速度力度与多人同时武打追赶群戏)。

### 对白容量与自然语速

**`craft_default`**：按 [对白预算](performance-action-timing.md#对白预算) 先核对完整发声需要多久，
再给主时间线安排开口、停顿与落点。分镜镜长够长但开口太晚，一样会赶词。
H3 中文小样本可参考约 4.1 个可发声字/秒；用实际可发声区间估算，生成后核对台词完整性。
样本出现过赶词与静默截断，不能据此确定通用截断阈值。
口语语言、声线与语速描述放在 `<d>` 外；`<d>` 内只放语言标签和逐字台词，不放秒数或表演指令。
稳定说话人用 `(S1)`、`(S2)`；full-reference 中说话人物同时写 `<Subject N> (Sx)`。

无参考音频时，以自然语言交代说话方式、开口 cue、句间停顿和说完后的动作；文本估时区间只留在镜头说明中，
不把每个词硬塞进小数秒槽。实际有音频对齐依据或已接受的精确时点时，才据此细化声音时序。
H3 官方接口未提供独立 `speech_rate` 参数，也没有公布「中文每秒固定几字」的可靠公式；
提示词中的语速与时机是生成指导，不能当作秒级执行保证。仅追加“自然语速”无法补上缺失的发声时间。

同一次生成内，已接受的对白跨切镜时可以用 `<scenetrans>` 并声明声音连续；它不会增加总时长，也不能
保证两个独立 job 的音频无缝衔接。`<cutoff>` 表示视频结束时有意截断发声，只用于剧本已要求的截断，
不用于处理装不下的完整台词。

### 说话人绑定

**`craft_default`**：说话人第一次出现时，在 `<d>` 外交代他在画内还是画外、以及音色（年龄、性别、高低），
台词跟在他的可见动作句后面（仍只出现一次），不集中列在正文末尾：
`<Subject 1> (S1), the boy on-screen with a clear high voice, opens his mouth and calls out: <d>[Chinese] ...</d>`。
台词期间画里还有别人的正脸时，把那个人明写成不说话：
`The messenger does not speak; his lips remain completely closed.`——与官方画外音写法
`while his lips remain completely closed` 是同一句式。

一镜实测（远处小孩喊一句，近处骑手不说话，骑手在台词期间仍正对镜头）：现行写法 3 次中 2 次口型落在骑手、
小孩闭嘴；加上述两条后 3 次全部落在小孩。19 条样本的发声基频都在儿童区间——模型没有选错声音，
只是把口型放到画面里最显眼的正脸上。骑手已出画或背对时，两种写法 12 次全部正确。所以分镜能安排时，
先让不说话的人出画或背身；不能时才靠这两条兜底，生成后仍核对口型落在谁脸上。

### 有配音或参考音频时

**`craft_default`**：已有同句同表演音频时，先测实际发声与停顿，再确定镜长。没有现成音频仍可按文本估计
写提示词，不为完成本阶段自动调用 TTS 或生成服务。

- 只参照音色、情绪或说话方式：使用 `reference`；它会重新表演本镜台词，不能拿参考音频的文件长度
  当作新台词时长，也不携带参考音频里无关的原话。
- 已接受完整声音轨原样复用：`fully_copy` 表示整条最终音轨；只用对白层或片段并另加环境声时使用
  `partially_copy`，写清源片段与目标时间的对应。复用用到的发声区间要完整容纳，不为适配镜长压缩语速。
- 参考音频走 full-reference，配合至少一张参考图或一段参考视频；每段音频 2–15 秒，最多三段、合计
  不超过 15 秒。图片改用 `reference_image`，不能与 `first_frame`/`last_frame` 混用。

`fully_copy` 等是官方提示词的复用意图，不是逐样本一致的验收证明。生成后核听逐字内容、语速、停顿、
尾音完整性与口型；项目需要精确锁定已有音轨时，以后期保留该音轨并核对画面同步作为最终依据。

### Context-IR 的作用

H3-Context-IR 把多模态输入增强成结构化提示词，本身不生成视频，且仍要求调用方先给出 4–15 秒的
`duration`。它不能代替对白预算。若执行端使用该服务，检查增强后的逐字台词、声音时间线与原时长一致，
不因使用官方增强就跳过容量检查。

官方依据（2026-09-07 核对）：

- [Base 提示词指南](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/base-en.txt)：对白位置、说话人、语速描述、切镜时间戳与跨镜发声。
- [Full-reference 指南](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt)：六段结构、音频引用与复用语义。
- [视频生成 API](https://platform.minimax.io/docs/api-reference/video-generation-v2-create)：必填时长、型号差异和输入模式互斥。
- [官方 CLI 的 H3 指南](https://github.com/MiniMax-AI/cli/blob/main/skill/h3-video/references/h3-video.md)：音频配合视觉参考，声音对齐与生成后检查。
- [Context-IR API](https://platform.minimax.io/docs/api-reference/video-generation-v2-h3-context-ir)：提示词增强和独立的时长输入。
