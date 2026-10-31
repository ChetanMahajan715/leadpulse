# LeadPulse Brand Guide

**Name:** LeadPulse
**Tagline:** Know which leads are alive.
**Repo:** `leadpulse`

## Logo

| File | Use |
|---|---|
| `assets/logo.svg` | README header, light backgrounds |
| `assets/logo-dark.svg` | Dark backgrounds (GitHub dark mode) |
| `assets/icon.svg` / `assets/icon.png` | Browser tab icon (Streamlit `page_icon`) |

The mark is a pulse (heartbeat) line in an indigo rounded square. It stands for "checking the pulse" of every lead.
Don't stretch, recolour or add effects to the logo.

## Colours

| Role | Name | Hex |
|---|---|---|
| Primary | Indigo | `#4F46E5` |
| Text / dark | Navy | `#0F172A` |
| Muted text | Slate | `#64748B` |
| Light surface | Mist | `#F1F5F9` |
| 🔥 Hot lead | Red | `#EF4444` |
| 🌤 Warm lead | Amber | `#F59E0B` |
| ❄️ Cold lead | Blue | `#3B82F6` |
| Positive factor | Green | `#16A34A` |
| Negative factor | Red | `#DC2626` |

## Typography

**Inter** (free, Google Fonts): Bold 700 for headings and the score, Medium 500 for labels, Regular 400 for body text.

## Theme

- **Default:** light, set in `.streamlit/config.toml`
- **Dark:** values are included in the same file as comments
- **Custom UI styles** (score, badges, cards, factors): `assets/style.css`

## README header

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img src="assets/logo.svg" alt="LeadPulse" height="64">
  </picture>
</p>
<p align="center"><b>Know which leads are alive.</b><br>AI-powered, explainable lead scoring</p>
```

This shows the right logo automatically in GitHub light and dark mode.
