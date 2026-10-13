# Reconnaissance Note: Jiji Uganda (jiji.ug)
**Course:** DSC2107 Data Mining & Wrangling | **Group:** ____ | **Date:** ____ | **Members:** ____

*(1 page, export to PDF. Delete the guidance in italics before submitting.)*

## 1. Site assignment
Assigned site per brief: Group 5 = Jiji Uganda (jiji.ug). Shared categories agreed with Group 6 (Jiji Kenya): ______.

## 2. robots.txt findings
*Paste the relevant lines verbatim and say what they mean for each target path.*
```
(User-agent / Allow / Disallow lines here)
```
| Path | Allowed? | Notes |
|---|---|---|
| /mobile-phones | | |
| /tablets | | |
| /smart-watches | | |
| pagination parameter | | |
Crawl-delay stated: ______ (our delay: 2-5 s regardless)

## 3. Site structure
- URL pattern of listings: `/{area}/{category}/{title-slug}-{ID}.html?indexPosition=N`
- Category hierarchy used and approx. number of ads: /mobile-phones ~15,154; /tablets ~2,577; /smart-watches ____ (record the date of these counts)
- Cards per page: ~20 (verify) ; pagination mechanism: ______
- Card order in the HTML is column-by-column, so rank = `indexPosition`, not DOM order (verify and screenshot)
- Fields on the card: title / price ("USh 450,000") / condition / location ("Region, Area") / seller badges (NOT collected) / description (NOT collected: may contain phone numbers) / discount badge + old price on a few ads: ______
- Posting date found on: card / detail page / not found: ______

## 4. Network analysis (screenshots attached)
- Fetch/XHR calls when loading a category page: ______
- Is listing data in the HTML, in embedded JSON, or from a JSON endpoint? ______
- Does plain `requests` return the data? ______

## 5. Chosen approach and justification
Approach (requests+BeautifulSoup / embedded JSON / Playwright): ______
Why: ______ (speed, politeness, simplicity, no login/token needed, no circumvention)

## 6. Field map
| Required field | Source | Selector / location | Issues |
|---|---|---|---|
| title | | | |
| price | | | |
| condition | | | |
| location | | | |
| posting date | | | |

## 7. Request budget per run
Listing pages ~__ + cohort re-checks ~__ = ~__ requests (cap ~1,000; code stops at 950).

## 8. Ethical safeguards
User-Agent, delays, no logins, excluded personal data (seller names, phones, badges, descriptions),
stop-on-block policy.
