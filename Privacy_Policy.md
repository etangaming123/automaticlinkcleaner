# Automatic Link Cleaner Privacy Policy

**Effective Date**: 2026-08-15
**Bot Name**: Automatic Link Cleaner#1001
**Developer**: etangaming123
**Contact**:
email: me [at] etangaming [dot] xyz
discord: @etangaming123

## 1. Introduction
This Privacy Policy ("Policy") describes how Automatic Link Cleaner ("the Bot", "we", "us", or "our") collects, uses, stores, and protects your information when you use our services. By using the Bot, you consent to the collection, use, and handling of your information as described in this Policy.
**If you do not agree with this Policy, you must not use the Bot.**
This policy only describes what the Bot collects, not what Discord collects.

## 2. Information We Collect

### 2.1. Technical Information
- **The links themselves**: When you run `/clean-link` or `/clean-link-v2`, the link you provide is processed in memory to strip tracker parameters and is not logged or stored anywhere.
- **TikTok short-link resolution**: For `vt.tiktok.com` and `www.tiktok.com/t/` links, the Bot makes an outbound HTTP request to that link to resolve the real destination URL before cleaning it. Only the link you provided is touched by this request; the resolved URL is used to build the cleaned link and is not stored.
- **Error Logs**: When a command fails, a traceback of the error may be printed to the bot's console for debugging. This does not include any personally identifiable information.

### 2.2. Server (Guild) Settings
If a server admin configures the auto embed-fixer (`/linkembeds config`, `platform`, `param`), we store that server's Discord Guild ID along with the chosen settings (enabled/disabled, platform list, tracker parameter list). This is server-level configuration, not personal data about any individual user.

### 2.3. Command Access Records
To enforce bans and command cooldowns, the Bot checks your Discord User ID against internal records (see Section 4 and 6). No other personal information is collected as part of this process.

**We do not collect any personally identifiable information such as your real name, physical address, or any other information that can be used to identify you personally.**

## 3. How We Use Your Information
We use the information we collect for the following purposes:

- **Service Provision**: To clean links you submit and to auto-fix embeds for links posted in servers where the feature is enabled, according to that server's configuration.
- **Access Control**: To enforce command cooldowns and bans.
- **Error Diagnosis**: To diagnose and fix issues with the Bot using error logs.

**We do not use your information for any advertising, marketing, or any other commercial purposes.**

## 4. How We Store Your Information
**WARNING!!! Your information is stored as .json files on the machine running the bot.** The machine running the bot is not shared with any third parties, and only the developer has access to this machine.
If you are banned from using the bot, a hash of your user ID will be stored in a .json file on the machine running the bot, and this hash will be used to prevent you from using the bot again. This is a hash and cannot be reversed to obtain your user ID. It is only used for the purpose of banning users from using the bot.

## 5. How We Share Your Information
**We do not share your information with any third parties.**
We may disclose information only in the following limited circumstances:

- **Legal Compliance**: If we are required to do so by law or in response to valid requests by public authorities (e.g., a court or a government agency).

## 6. Data Retention
Server settings are retained until a server admin changes them, or until the Bot is removed from the server. Ban record hashes are retained for as long as the ban is in effect (bans may be time-limited, tied to a specific command use, or indefinite, depending on how the ban was applied). Command cooldowns exist only in memory and are cleared on every Bot restart. The links you clean are never logged or retained.

## 7. Your Rights and Choices
At any point, you may:

- **Access Your Information**: Request access to the information we have about you.
- **Update Your Information**: Update or correct any information we have about you.
- **Delete Your Information**: Request that we delete any information we have about you.

We will respond to verifiable requests from users who wish to exercise their data protection rights. Please contact us with the given contact information at the top of this page.

## 8. Children's Privacy
The Bot is not intended for use by children under the age of digital consent in their jurisdiction. We do not knowingly collect personal information from children. If we become aware that we have collected personal information from a child, we will take steps to delete that information as soon as possible.

## 9. Third-Party Services
The Bot interacts with the following third parties as part of its core functionality:

- **TikTok**: to resolve shortened `vt.tiktok.com` links before cleaning them.
- **fixupx.com** and **kkinstagram.com**: used to generate fixed embed links for Twitter/X and Instagram content. Links to these domains are shown to users, but no data about you is sent to them by the Bot.

We are not responsible for the privacy practices of these third-party services. We encourage you to review their privacy policies separately.
We are also not responsible for content hosted on third party sites (e.g external links that the bot has posted).

## 10. Changes to This Privacy Policy
We may update this Privacy Policy from time to time. We will notify you of any changes via etan bot support server.. You are advised to review this Privacy Policy periodically for any changes. Changes to this Privacy Policy are effective when they are posted on this page. Your continued use of the Bot after any such change constitutes your acceptance of the updated Privacy Policy.

## 11. Contact Us
If you have any questions about this Privacy Policy, please contact us at the provided contact information at the top of this page.
