# ImageGen Card Prompts

当前运行环境未暴露内置 `image_gen` 工具，因此项目默认使用 `cards/generator.py` 的 Pillow 高级兜底渲染。若后续可调用 `$imagegen`，可按以下提示词为每张卡生成更高质感位图，再覆盖输出到 `output/cards/<match_id>/`。

## 总览卡

Use case: infographic-diagram
Asset type: WeChat article esports match summary card
Primary request: Generate a premium StarCraft Brood War Korean team league match summary card.
Style/medium: polished esports broadcast graphic, dark navy glassmorphism panels, sharp neon accents, high-end Korean esports scoreboard aesthetic.
Composition/framing: 1080x545 landscape. Top large title. Left team roster panel, right team roster panel, center prize pool and final score. Dense but clean information design.
Text (verbatim): use the exact match data provided by the program; do not invent names, scores, prize values, or maps.
Constraints: no watermark, no logo, no QR code, no decorative mascot, no fake sponsor marks. Text must be sharp and readable. Keep race tags as P/T/Z in colored square badges.
Avoid: blurry text, misspelled Chinese/Korean/English names, extra players, invented statistics, low-contrast gray text.

## 轮次卡

Use case: infographic-diagram
Asset type: WeChat article esports round recap card
Primary request: Generate a premium StarCraft round result card listing every game result in one set.
Style/medium: dark esports scoreboard UI, layered panels, subtle blue/red neon edge lights, compact rows, crisp typography.
Composition/framing: 1080px wide, height may grow by game count. Header contains SET number, round title, first-to-N wins, score, winning team. Body contains one row per game: left player, WIN/LOSE, center GAME number and map, right WIN/LOSE and player.
Text (verbatim): use exact round data supplied by the program. Do not add watermark.
Constraints: no watermark, no MVP section, no single-game card layout, no process narration. Results only.
Avoid: overlapping text, truncated names, altered maps, decorative clutter, low readability.
