# REBRAND.md — NovaFlow 定制说明

本仓库是 [WNLUO/dsh-mobile-plugin](https://github.com/WNLUO/dsh-mobile-plugin)（MIT）的 **NovaFlow 定制分支**。
上游代码保留，改动集中在品牌化与兼容性验证；MIT 许可证与原始版权声明保留（见 `LICENSE`）。

## 1. 插件侧（桌面端服务）

- `lib/panel/index.html` 由 `React/` 重新构建（构建产物直接提交，符合上游约定）。
- `React/src/lib/i18n/messages/*.ts`：`AI-HUB` / `DSH` 文案统一改为 `NovaFlow`（含韩语等非 ASCII 相邻写法）。
- `lib/client.js`：诊断弹窗中的 `DSH` 文案改为 `NovaFlow`（`consoleTitle` 为 `NovaFlow 移动端`）。
- `React/src/components/FirewallDialog.tsx`：防火墙规则名 `DSH Mobile {port}` → `NovaFlow Mobile {port}`。
- `locale/en.json` / `locale/zh.json` 插件描述同步改名。
- 保留未改的内部标识：模块 id `dsh-mobile-plugin`、CSS 前缀 `dshm_`、`__DSH_CHAT_EMBED_*` 全局键等（仅内部使用，界面不可见）。

构建：

```powershell
cd React
pnpm install
pnpm build       # tsc -b && vite build && node scripts/inline.mjs
```

`pnpm build` 会重新生成单文件面板 `lib/panel/index.html`。

## 2. 安卓 App 侧（NovaFlow.apk）

上游 App（`com.dsh.mobile`）为 React Native + Hermes 字节码，本仓库提供可复现的改包流程，产物见 Releases。

已改动：

| 项目 | 内容 |
| --- | --- |
| 应用名 | `AI-HUB` → `NovaFlow`（`res/values/strings.xml` `app_name` 及各语言） |
| 图标 / 圆形图标 / 自适应图标 / 启动图 / App 内 logo | 全部换成 NovaFlow 图标 |
| 引导页 hero logo | Hermes 里的矢量路径（原 DeepSeek 鲸鱼）等长替换为 NovaFlow N 标 |
| 关于页正文（11 语言）、版权行、默认品牌名 | AI-HUB → NovaFlow |
| 划词菜单（9 语言） | `Ask DSH` → `Ask NovaFlow` |
| 微信交流群二维码无障碍文案（11 语言中的多数） | AI-HUB → NovaFlow（仅剩 6 条 UTF-16 无障碍串，屏幕阅读器才会读） |
| 自动更新 | OTA 地址替换为无效域名，`embeddedOtaId = 999999`，防止线上热更覆盖 |
| 版本 | `versionCode 465` / `versionName 0.5.50` |

关键约束（Hermes 字符串表）：

- 字符串表条目之间**共享字节**（子串去重、边界共享），因此所有改写都必须**等长且不移动任何字节**；只改整行/整条，不能插入或删除字符。
- 文件末尾 20 字节是 body 的 SHA-1；每次改 bundle 后必须重算，并同步更新 `assets/dsh-build.json` 的 `embeddedJsSha256`。
- 仓库内 `tools/patch-release-strings.py` 说明了本项目实际的补丁方式（含共享存储校验与 `SIMULATE=1` 预演）。

改包与签名（需要 JDK、`apktool.jar`、`uber-apk-signer.jar`）：

```powershell
# 1) 解码（-s 保留原始 dex）
java -jar apktool.jar d -f -s NovaFlow-original.apk -o apk-rebrand
# 2) 改资源 / 改 assets/index.android.bundle（见 tools/patch-release-strings.py）
# 3) 回编译 + 对齐签名（使用自己的 keystore，以后可直接覆盖安装）
java -jar apktool.jar b apk-rebrand -o NovaFlow-unsigned.apk
java -jar uber-apk-signer.jar --apks NovaFlow-unsigned.apk --ks novaflow.keystore --ksAlias novaflow
```

## 3. 在 NovaFlow 桌面端安装插件

```powershell
# 在 NovaFlow 账号 profile 目录里（DSH 运行时自带的 pnpm）
pnpm add "file:C:/path/to/dsh-mobile-plugin"
```

并把 `dsh-mobile-plugin` 追加到 profile `package.json` 的 `dsh.profile.bundles`，重启 NovaFlow。
验证：`GET /api/mobile/v1/health` 返回 `{"ok":true,"service":"dsh-mobile-plugin",...}`，设置 → 移动端 出现配置页面。

> 注意：NovaFlow 实例必须使用 `C:\Users\<user>\.novaflow` 作为 `DSH_HOME`（启动前清掉环境里从 DSH Desktop 继承的 `DSH_HOME`），否则插件会装进错误的账号 profile。

## 4. 免责

品牌化与功能验证由本仓库维护者完成；上游项目与其作者不背书本分支。使用隧道/机器人等能力时请遵守各平台服务条款。
