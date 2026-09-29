# Project: Kubozoa Website Test Automation (POC)

## Goal

Build an example proof-of-concept test automation platform that opens [https://www.kubozoa.com/](https://www.kubozoa.com/) and exercises real user interactions. The platform confirms that the public site responds as expected: pages load, navigation works, and common actions such as clicking, following links, and scrolling complete without breaking the experience.

The same checks must run in more than one browser so results reflect how the site behaves for different visitors. The tooling simulates those browsers (for example Chromium, Firefox, and WebKit) and reports outcomes per browser.

This is a demonstration of automated browser testing against a live marketing site. It is not a product feature of Kubozoa and does not change the site itself.

## Target

| Item | Detail |
| --- | --- |
| Site | [https://www.kubozoa.com/](https://www.kubozoa.com/) |
| Owner | Kubozoa Inc. |
| Nature | Public marketing site for cloud-native products and services |
| Scope | Read-only visitor flows on pages linked from the home page and primary navigation |

Primary areas visible on the site:

- Home, with its hero and section content
- What we do: KuboSuite™ and Services
- Who we are
- Join us
- Get in touch
- KuboSuite™ product entries (KuboDevelop™, KuboSecure™, KuboOperate™, KuboLib™, and the products overview)
- Footer destinations, including the privacy policy

## What the platform should do

1. Launch each target browser and open the home page.
2. Assert that the page loads and key content is present (for example the Kubozoa name, primary navigation, and main sections).
3. Perform interactions a visitor would:
   - Click buttons and calls to action (Learn more, Read more, Get in touch, View open positions, See all KuboSuite™ Products, More about us).
   - Follow in-site navigation and footer links.
   - Scroll through long sections so content below the fold is reached.
4. After each interaction, check that the resulting page or section is usable: it loads, shows the expected heading or content, and does not surface a broken layout or an obvious error page.
5. Repeat the same interaction set in each simulated browser so a failure in one browser is visible next to a pass in another.
6. Report each check as pass or fail, with enough context (browser, URL, action, what was expected) to see what broke.

## Out of scope for the POC

- Logging in, submitting forms with real personal data, or creating accounts
- Load, performance, security, or accessibility audits as primary goals
- Changing site content, APIs, or infrastructure
- Covering every historical URL; start from the home page and the links a visitor can reach from it

## Success

The POC is successful when a single run can visit the site in each simulated browser, complete the interaction set above, and produce a clear pass/fail result per browser and step without manual clicking.
