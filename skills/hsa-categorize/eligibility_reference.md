# HSA eligibility reference (for sorting only)

**For sorting only. Not tax advice.** Last reviewed: 2026-10-15. Rules change; check the sources and your plan administrator before you claim anything.

Sources: IRS Publication 502, Medical and Dental Expenses (https://www.irs.gov/publications/p502), and IRS Publication 969, Health Savings Accounts (https://www.irs.gov/publications/p969). This file summarizes them in plain words and is not a copy of either.

## How the review page uses this

The page suggests a likelihood for each item. It never sets a status; you do.

| Suggestion | Why |
|---|---|
| Highly likely | Amazon's product page shows its "FSA or HSA eligible" badge |
| Likely | A medical category on Amazon, or a medical word or drug ingredient in the product type |
| Unlikely | Mixed categories: personal care, vitamins and supplements, baby, clothing, home, food |
| Highly unlikely | Everything else (books, office, toys, kitchen, electronics, and so on) |

Two limits. A missing badge means unknown, not not eligible. An "FSA Eligible Items" link on a page is a store link, not a product label. The rules the page and the Python tools apply are in `category_rules.json` in this folder (it has a version number); change them there, not in the page.

## The core test

An expense generally qualifies when its main purpose is to diagnose, treat, ease, or prevent a specific medical condition. General health, comfort, hygiene, or appearance does not qualify.

## Usually eligible

- Visits, tests, imaging, therapy, mental health care, and prescriptions.
- Over-the-counter medicines such as pain, allergy, cold, and stomach remedies (no prescription needed since 2020), and menstrual products.
- First-aid supplies, bandages, thermometers, blood pressure and glucose monitors, and test kits for diagnosing a condition.
- Dental treatment, eye exams, prescription glasses and contact lenses.
- Breast pumps, hearing aids, mobility aids, and breathing equipment prescribed for a condition.

## Usually not eligible

- Everyday toiletries and cosmetics: shampoo, soap, toothpaste, floss, deodorant, makeup, anti-aging products.
- Ordinary vitamins and supplements taken for general health.
- Gym memberships, fitness gear, and general-purpose fitness trackers.
- Groceries, diapers, cleaning supplies, and household items.
- Insurance premiums in most cases.

## Dual use: needs a letter of medical necessity (LMN)

Things with both a wellness use and a medical use are treated as ineligible unless a clinician states that you need the item for a specific diagnosed condition. Examples: massage tools, air purifiers for documented allergy or asthma, special mattresses, some supplements, fitness programs for rehabilitation, special foods (only the extra cost over normal food). In the page, set these to "Doctor's note / LMN"; reimbursing without the letter is your decision.

## Often unclear: check the plan

Sunscreen, reading glasses, acne products, skin products for a diagnosed condition, and anything an administrator's card system approves or rejects. If sources disagree, treat the item as unresolved and verify.

## Reimbursement rules that catch people

- No double reimbursement: an expense paid by insurance or another account cannot also be paid from the HSA.
- Eligible people: you, your spouse, and your tax dependents.
- The expense must be incurred after the HSA was set up.
- Keep itemized receipts and any letters. Non-qualified withdrawals are generally taxable and may carry an extra tax before age 65, with exceptions.
