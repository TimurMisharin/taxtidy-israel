[English](README.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [العربية](README.ar.md)

# TaxTidy Israel

TaxTidy Israel הוא תוסף קוד פתוח ל-ChatGPT שעוזר לבדוק מסמכי מס בישראל. הוא מסייע לבחור מסלול לכל שנה, להשוות בין שכר למס שנוכה, לבדוק תרומות לפי סעיף 46 ולזהות את האסמכתאות הדרושות לאימות הגשת דוח. המחשבון המצורף תומך במקרים מוגדרים לשנת **2025**.

**גרסה 0.1.2** · [גרסת GitHub וקובץ אימות SHA-256](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.2) · [רישיון AGPL-3.0-only](LICENSE)

## התקנה לפי פלטפורמה

| פלטפורמה | איך מתקינים |
| --- | --- |
| **ChatGPT ב-macOS** | מתקינים את [אפליקציית ChatGPT למחשב](https://chatgpt.com/download/) ופועלים לפי השלבים להתקנה מהקטלוג של המאגר בהמשך העמוד. |
| **ChatGPT ב-Windows** | מתקינים את [אפליקציית ChatGPT למחשב](https://chatgpt.com/download/) ומבצעים את אותם שלבים ב-PowerShell. המחשבון וזיהוי הטקסט לא אומתו בסביבת Windows מקורית. |
| **Linux** | פותחים את [ChatGPT בדפדפן](https://chatgpt.com/) ופועלים לפי ההנחיות לגרסת הווב. אפליקציית המחשב הרשמית זמינה ל-macOS ול-Windows. רישום הקטלוג ב-Codex CLI אינו מעניק לדפדפן גישה לתוסף. |
| **ChatGPT בדפדפן** | פותחים **Plugins** בסרגל הצד. אם מנהל סביבת העבודה ייבא את הקטלוג מ-GitHub, בוחרים בקטלוג של סביבת העבודה, מחפשים **TaxTidy Israel** ובוחרים **Install plugin** כשהאפשרות מוצגת. |
| **ChatGPT ב-iPhone או Android** | מתקינים או מעדכנים את [אפליקציית ChatGPT הרשמית](https://chatgpt.com/download/). נכנסים לסביבת עבודה מתאימה, פותחים **Plugins**, מחפשים **TaxTidy Israel** ובוחרים **Install plugin** כשהאפשרות מוצגת. התוסף חייב להופיע בקטלוג סביבת העבודה או בקטלוג הציבורי. |

**מצב הקטלוג הציבורי.** גרסת GitHub מספקת את חבילת ההתקנה. הופעה בקטלוג הציבורי של ChatGPT מחייבת [הגשה, בדיקה ופרסום באישור OpenAI](https://developers.openai.com/plugins/deploy/submission). עד אז לא ניתן להתקין את גרסת GitHub מהקטלוג הציבורי בחשבון אישי בדפדפן או בנייד. הזמינות תלויה גם בתוכנית, באזור ובהגדרות סביבת העבודה. [מידע על תוספי ChatGPT](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)

### התקנה מהקטלוג של המאגר במחשב

1. מתקינים את [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) ומתחברים. מריצים את הפקודה ב-Terminal ב-macOS או ב-PowerShell ב-Windows.

   ```sh
   codex plugin marketplace add TimurMisharin/taxtidy-israel
   ```

2. מפעילים מחדש את אפליקציית ChatGPT למחשב. פותחים **Plugins**, בוחרים בקטלוג **TaxTidy Israel**, פותחים את התוסף ובוחרים **Install plugin**.
3. אם הקטלוג אינו מופיע, בודקים שהפקודה הצליחה ושגרסת האפליקציה וסביבת העבודה מאפשרות שימוש בקטלוג מקומי. [הוראות OpenAI לקטלוגים](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)

### סביבת עבודה מנוהלת

מנהל סביבת העבודה פותח **Admin → Plugins → Add → Import marketplace**, מזין את `https://github.com/TimurMisharin/taxtidy-israel` בשדה **Source**, משאיר את **Path** ריק ואת הפניית Git ריקה כדי לעקוב אחר `main`. מאשרים גישה ל-GitHub אם מתבקשים, בודקים את תוצאות הייבוא ומאפשרים לחברי סביבת העבודה להתקין את התוסף. [מדריך הייבוא של OpenAI](https://learn.chatgpt.com/docs/enterprise/plugin-management)

## מתחילים בדיקה

1. פותחים שיחה חדשה ובוחרים **@TaxTidy Israel**. עברית היא ברירת המחדל. אפשר לבקש תשובה גם באנגלית, ברוסית או בערבית.
2. מציינים את שנת המס ואת המטרה. לדוגמה, ״עזור לי לבדוק את שנת המס 2025. התחל ברשימת המסמכים הדרושים ומה אפשר לאמת מכל מסמך.״
3. בודקים את המסמכים המקוריים שהתוסף מבקש, למשל **טופס 106**, אישורי בנק וקבלות תרומה. שואלים אילו נתונים הותאמו, מה חסר ומה הצעד הרשמי הבא.

ההדרכה בשיחה זמינה גם בלי הרצת קוד מקומית. מחשבון **2025** וכלי PDF וזיהוי טקסט דורשים סביבת Python/POSIX פרטית ותלויות נפרדות. יש להשוות את הסכומים שחולצו למסמכים המקוריים. התוסף אינו מתחבר אוטומטית לאזור האישי ברשות המסים ואינו מגיש דוחות. אין להעלות ל-GitHub מסמכי מס או פרטי התחברות. [התקנה והגדרת סביבת הרצה](taxtidy-israel/SETUP.md)

## מידע נוסף

- [דוגמה עם נתונים מדומים](taxtidy-israel/DEMO.md) · [יכולות מאומתות ומגבלות](taxtidy-israel/VERIFICATION.md)
- [פיתוח ואריזה](DEVELOPMENT.md) · [דיווח על בעיה](https://github.com/TimurMisharin/taxtidy-israel/issues) · [רישיונות צד שלישי](THIRD_PARTY_NOTICES.md)
