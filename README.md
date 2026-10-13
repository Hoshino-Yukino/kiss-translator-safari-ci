# kiss-translator-safari

用 GitHub Actions 自动把 [KISS Translator](https://github.com/fishjar/kiss-translator) 构建成 iOS 和 macOS 的 Safari 扩展，并上传到自己的 TestFlight（仅内部测试，自用）。

- 每天检查一次上游 release，有新版本就自动构建上传
- 距上次上传满 60 天会自动重新上传，避免 TestFlight 构建 90 天过期
- 本仓库只包含 workflow，构建时直接拉取上游源码，无需 fork、无需同步

## 一次性准备

### 1. Apple Developer（developer.apple.com）

在 Certificates, Identifiers & Profiles → Identifiers 注册两个 App ID：

| 用途 | Bundle ID 示例 |
| --- | --- |
| App 本体 | `com.yourname.kiss-translator` |
| Safari 扩展 | `com.yourname.kiss-translator.Extension` |

扩展的 ID 是在 App 的 ID 后面加 `.Extension`（Safari 转换工具的默认规则）。
iOS 和 macOS 两个 target 通常共用这两个 ID，不需要再为 macOS 单独注册。可以在本地生成的 Xcode 工程里确认一下。

### 2. App Store Connect（appstoreconnect.apple.com）

1. **我的 App → + → 新建 App**：平台同时勾选 **iOS 和 macOS**，套装 ID 选上面注册的 App ID，SKU 随意填。
   如果已经只按 iOS 建好了，可以在该 App 的页面里再添加 macOS 平台。
   名称在 App Store 全局唯一，`KISS Translator` 很可能已被占用，填一个自己的名字即可（只用于 TestFlight，不会公开）。
2. **TestFlight → 内部测试 → +**：新建一个群组，打开「自动分发」，把自己加进去。
3. **用户和访问 → 集成 → App Store Connect API → 团队密钥 → +**：
   - 访问权限选 **Admin**（CI 上自动创建签名证书和描述文件需要）
   - 下载 `.p8` 文件（只能下载一次），记下 **Key ID** 和页面上方的 **Issuer ID**

### 3. 本仓库的设置

**Settings → Secrets and variables → Actions**

| 类型 | 名称 | 值 |
| --- | --- | --- |
| Secret | `APPLE_TEAM_ID` | 10 位 Team ID |
| Secret | `ASC_KEY_ID` | API Key 的 Key ID |
| Secret | `ASC_ISSUER_ID` | Issuer ID |
| Secret | `ASC_KEY_P8` | `.p8` 文件的完整内容（含 `-----BEGIN PRIVATE KEY-----` 首尾行） |
| Secret | `DEV_CERT_P12_BASE64` | Apple Development 证书（含私钥）导出的 `.p12`，再转成 base64 |
| Secret | `DEV_CERT_PASSWORD` | 导出 `.p12` 时设置的密码 |
| Variable | `BUNDLE_ID` | App 本体的 Bundle ID，如 `com.yourname.kiss-translator` |

**Settings → Actions → General → Workflow permissions** 选 **Read and write permissions**。

#### 导出开发证书（在自己的 Mac 上操作）

Archive 阶段，Xcode 的自动签名会先用开发证书签名，而 API Key 的云端签名只管导出上传时用的发布证书，所以 CI 上需要你的开发证书。

1. Xcode → Settings → Accounts → 选中账号 → Manage Certificates，确认有 **Apple Development** 证书（没有就点 + 创建）。
2. 打开「钥匙串访问」→「我的证书」，找到 `Apple Development: 你的名字`，展开确认下面带有私钥。
3. 右键 → 导出，格式选 `.p12`，设置一个密码（填进 `DEV_CERT_PASSWORD`）。
4. 转成 base64 并复制到剪贴板，粘贴进 `DEV_CERT_P12_BASE64`：
   ```bash
   base64 -i Certificates.p12 | pbcopy
   ```

开发版描述文件需要至少注册一台设备：iOS 需要注册你的 iPhone，macOS 需要注册你的 Mac。用 Xcode 往设备上装过一次就会自动注册，也可以在 developer.apple.com 的 Devices 里手动添加。

### 4. 首次运行

**Actions → Safari iOS → TestFlight → Run workflow**，勾选 `force` 运行一次。
iOS 和 macOS 会并行构建，各自上传。两个平台都成功后才会记录状态；任一平台失败，第二天会自动重试。
上传成功后，App Store Connect 处理几分钟，就能在 TestFlight 里安装。

之后什么都不用管，定时任务会自动处理新版本和 60 天刷新。

不需要 macOS 版本时，把 workflow 里 `platform: [iOS, macOS]` 改成 `platform: [iOS]` 即可。

## 安装后

- **iPhone / iPad**：用 TestFlight App 安装，然后在 设置 → App → Safari → 扩展 打开 Kiss Translator，网站权限选「所有网站」。
- **Mac**：从 Mac App Store 安装 TestFlight，用它安装 Kiss Translator，打开一次 App，然后在 Safari → 设置 → 扩展 里启用。

然后在扩展设置里填同步信息，配置会从云端拉下来。

## 首次运行可能遇到的问题

本 workflow 已通过语法检查，但没有在真实的 Apple 账号上跑过，第一次可能需要调整：

- **上传校验失败（图标等）**：转换工具生成的 iOS 工程可能缺少 App Store 要求的 1024×1024 App 图标。按报错信息处理，必要时在 `Build Xcode project` 之后加一步替换图标。
  最省事的排查方法是先在自己的 Mac 上用 Xcode 手动 Archive → Distribute 一次，把校验问题都解决，再交给 CI。
- **签名失败**：确认 API Key 是 Admin 权限，两个 App ID 都已注册且和 `BUNDLE_ID` 一致。
- **找不到 iOS / macOS scheme**：日志里会打印实际的 scheme 列表，按需修改 workflow 里的筛选条件。
- **macOS 上传被拒（沙盒等）**：Mac App Store 渠道要求 App 和扩展都开启 App Sandbox。转换工具生成的工程默认已开启，如果报错，在 Xcode 里检查 macOS target 的 Signing & Capabilities。
- **上游构建脚本变更**：如果上游改了 `build-safari.mjs` 里的默认 Bundle ID，workflow 会直接报错停止，不会用错的 ID 去签名。

## 状态文件

`.state/last-built` 记录上次构建的上游版本，`.state/last-upload` 记录上次上传时间。
删除它们（或手动运行时勾选 `force`）即可强制重新构建。

## 费用

公开仓库使用标准 GitHub 托管 runner 免费。如果改成私有仓库，macOS 分钟数按 10 倍计费，每个平台每次构建大约消耗 150～250 分钟额度，两个平台翻倍。

## 许可

本仓库只包含构建脚本。KISS Translator 本体为 GPL-3.0，构建产物仅供自己使用，不要通过公开 TestFlight 链接或 App Store 分发。
