# Synthetic local demonstration

Executed on 2026-11-20 using the real local CLI in a new private synthetic case. No real taxpayer, mailbox, portal, upload or filing was involved. Runtime documents and secrets are excluded from this package.

## Inputs and actual result

The fictional taxpayer selected 2025 and an annual refund/balance check, with Hebrew as the initial language. Reviewed evidence established full-year residency, male adult under 60, unmarried status, 2.25 credit points, complete income/payment declarations and no unsupported material facts. These are fixture facts, not defaults for a real person.

Two employers supplied annual taxable wages ILS 80,000 and ILS 40,000, with total actual withholding ILS 12,000. Cumulative payroll, A99/5 and later matching טופס 106 records remained supporting observations; wages counted once per employer. Three records for one qualifying ILS 1,000 donation reconciled to one receipt and one annual credit. Payroll relief of ILS 350 was retained without adding another payment or credit.

Independent arithmetic: 84,120 × 10% + 35,880 × 14% = 13,435.20; personal credits 2.25 × 2,904 = 6,534; donation credit 1,000 × 35% = 350. Estimated liability is ILS 6,551.20, giving an **estimated 2025 refund of ILS 5,448.80** against ILS 12,000 withheld. This exact-decimal estimate is not filing-ready or a statutory rounding determination.

## Executed sequence

1. `init --years 2025 --language he --synthetic` created the private case.
2. Three `import-evidence` calls loaded baseline wages/coverage, corroborating payroll/Form 106 evidence, and repeated donation records.
3. `pdf --authorized` handled a synthetic protected employer certificate through a concealed terminal password prompt. The original hash stayed unchanged; the copy reopened and compared successfully. No password appeared in output, command arguments or case files.
4. The assistant viewed both full-page original/copy renders: year 2025, wages 80,000, withholding 8,000, adjustment −450 and the blank field matched. `review-document` then recorded the actual visual/figure checks. Local attachment readiness did not establish recipient acceptance or import monetary evidence automatically.
5. `calculate --tax-year 2025` produced the estimate above. A demonstration harness initially expected a different decimal string spelling; its failed assertion and corrected exact-string check are retained in the development evidence.
6. Three `record-event` calls stored explicitly synthetic draft, rejected original attachment and accepted corrected attachment observations. `bank-2025-original.pdf` remained rejected; `bank-2025-corrected.pdf` remained accepted. Neither observation was a real portal action.
7. `summary --language he`, then `resume --language ru` and `resume --language ar`, reopened the same checkpoint with no mailbox. Both current year projections and the saved summary retained the checked estimate, exact attachment history, and **draft** filing state. No acknowledgment, transmission or settlement was invented.

All calls also supplied the explicit private case root and appropriate reviewed input JSON. See [setup](SETUP.md) for executable invocation patterns and the linked schema/template instructions. Raw development evidence is retained privately and is not included in this package. See [verification scope](VERIFICATION.md) for the public limits of these observations.

## Short conversation based on the observed workflow

**User:** אני רוצה לבדוק החזר מס לשנת 2025. יש לי שני מעסיקים ותרומה.

**Assistant:** אפשר להעלות את המסמכים הקיימים או לאסוף אותם ידנית. נצטרך טופס 106 מכל מעסיק כדי לאמת את השכר השנתי ואת המס שנוכה, וקבלה לתרומה כדי לבדוק זכאות לזיכוי. נברר גם את שאר ההכנסות והזכאויות לפני חישוב מלא.

**After the verified fictional calculation:** לפי הנתונים הסינתטיים שנבדקו, אומדן ההחזר לשנת 2025 הוא 5,448.80 ש״ח. נשמרה טיוטה; לא הוגש דוח. אפשר להשלים כעת בדיקת מסמכים והתאמה למסלול ההגשה. ״להגשת הבקשה״ היא כניסה לשירות הציבורי, לא הוראה לשלוח לפני השלמת הבדיקות.

**Returning user:** Продолжим по-русски, без почты.

**Assistant:** Я прочитал сохранённое дело. За 2025 год расчётный возврат — 5 448,80 ₪; декларация остаётся черновиком. Повторно запрашивать уже проверенные טופס 106 не нужно. Далее проверим право на выбранный способ подачи и требования к приложениям. «להגשת הבקשה» означает вход в сервис подачи заявления, а не подтверждение отправки.

**Returning user:** لنكمل بالعربية دون بريد إلكتروني.

**Assistant:** قرأتُ ملف الحالة المحفوظ. الاسترداد التقديري لعام 2025 هو 5,448.80 شيكل، والإقرار ما زال مسودة ولم يُقدَّم. لا حاجة لطلب نماذج טופס 106 التي جرى التحقق منها مرة أخرى. الخطوة التالية هي التحقق من أهلية مسار التقديم ومتطلبات المرفقات. «להגשת הבקשה» تعني الدخول إلى خدمة تقديم الطلب، وليست تأكيدًا لإرساله.

These replies render the actual CLI state; the separate independent forward-test covers skill use with different fictional amounts and conflicting evidence. No account installation or live service behavior is claimed.

## Synthetic spouse routing examples

- For fictional spouses already married before 2025, an official form showing a separate-return checkbox leaves a proposed separate submission unresolved. If the year-specific route review verifies a joint Form 1301 and eligibility for separate tax calculation, record `submission: joint` and `separate_calculation: true`. If the review instead verifies two coordinated submissions for the same family file, record `submission: separate` and explain the possible joint processing.
- For fictional spouses who married in 2025, a signed Form 4430 leaves the proposed separate route unresolved until the Authority's 2025 election and the form/channel are verified. Their 2026 route requires its own review. If the registered spouse has already filed and the office directs joint reporting, preserve the acknowledged return and use the correction route. Receiving the correction attachment, accepting the correction and issuing a revised assessment each require their own evidence.
