# Firm logo sources

Every file was downloaded on **2026-10-14** directly from the firm's own website. No logo-aggregator sites were used.
Only resizing (Topstep) and monochrome fill (Vest, whose inline SVG inherits CSS colour) were applied; the site also renders
all logos in a uniform monochrome tint via CSS. Firm names and logos are trademarks of their owners, used for identification only.

| Firm | File | Source (exact URL) | Notes |
|---|---|---|---|
| Topstep | `topstep.png` | https://cdn.prod.website-files.com/69e902b0a74d3d99a517f56d/6a299fdfbdc3a918fdf4b3ff_topstep_logo-white.webp | Header logo `<img>` on https://www.topstep.com/ (Webflow asset host used by the site). Resized 3457 px → 480 px wide, converted WebP → PNG. |
| Tradeify | `tradeify.svg` | https://cdn.prod.website-files.com/679b064a680c614548672a06/6a82f59b2b2b53f7c664d19e_logo-light%20(1).svg | Brand logo `<img>` on https://tradeify.co/ (Webflow asset host used by the site). Unmodified. |
| Take Profit Trader | `takeprofittrader.svg` | https://takeprofittrader.com/assets/desktop-logo.svg | Header logo on https://takeprofittrader.com/. Unmodified. |
| Breakout | `breakout.svg` | https://www.breakoutprop.com/ (inline `<svg>` inside `a.header__logo`) | Extracted verbatim from the homepage header markup. Unmodified. |
| Vest | `vest.svg` | https://vestmarkets.com/ (inline `<svg>` inside the site `<header>`) | Extracted from header markup. Paths use a CSS class `fill-foreground` (theme colour); replaced by `fill="#ECEAE4"` so the file renders standalone. No shape changes. |
| MyFundedFutures | `myfundedfutures.png` | https://myfundedfutures.com/images/mffu/apple-touch-icon.png | Official site icon (shield mark) linked from the homepage `<head>`; the homepage has no separate header logo file. Unmodified. |
| Apex Trader Funding | — (text wordmark) | https://apextraderfunding.com/ returned HTTP 403 to automated fetch (help-center and support subdomains too) | No official asset obtainable without bypassing the block → neutral text wordmark. |
| Lucid Trading | — (text wordmark) | https://lucidtrading.com/ returned HTTP 403; https://support.lucidtrading.com/assets/favicon is a generic book icon, not a brand mark | No clean official asset → neutral text wordmark. |
| MyFundedPerps | — (text wordmark) | https://myfundedperpetuals.com/assets/mff-logo-DuWw_HpNXn.svg | The site's header logo reads "My Funded Futures", not a distinct MyFundedPerps mark; using it would misidentify the firm → neutral text wordmark. |
