[English](README.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [العربية](README.ar.md)

# TaxTidy Israel

TaxTidy Israel إضافة مفتوحة المصدر لـ ChatGPT لمراجعة المستندات الضريبية في إسرائيل. تساعدك على اختيار الإجراء المناسب لكل سنة، ومطابقة الأجور والضريبة المقتطعة، والتحقق من تبرعات المادة 46، وتحديد الأدلة اللازمة لتأكيد تقديم الإقرار. تدعم الحاسبة المرفقة حالات محددة من سنة **2025**.

**الإصدار 0.1.2** · [إصدار GitHub وبصمة التحقق](https://github.com/TimurMisharin/taxtidy-israel/releases/tag/v0.1.2) · [رخصة AGPL-3.0-only](LICENSE)

## التثبيت حسب المنصة

| المنصة | طريقة التثبيت |
| --- | --- |
| **ChatGPT على macOS** | ثبّت [تطبيق ChatGPT لسطح المكتب](https://chatgpt.com/download/)، ثم اتّبع خطوات التثبيت من دليل المستودع أدناه. |
| **ChatGPT على Windows** | ثبّت [تطبيق ChatGPT لسطح المكتب](https://chatgpt.com/download/) واتّبع الخطوات نفسها باستخدام PowerShell. لم تُختبر الحاسبة وأدوات التعرّف على النص في بيئة Windows الأصلية. |
| **Linux** | افتح [ChatGPT في المتصفح](https://chatgpt.com/) واتّبع تعليمات الويب. تطبيق ChatGPT الرسمي لسطح المكتب متاح على macOS وWindows. يستطيع Codex CLI تسجيل الدليل، لكن التسجيل لا يتيح الإضافة داخل المتصفح. |
| **ChatGPT على الويب** | افتح **Plugins** في الشريط الجانبي. إذا استورد مسؤول مساحة العمل دليل GitHub، فاختر دليل مساحة العمل، وابحث عن **TaxTidy Israel**، ثم اختر **Install plugin** إذا ظهر الخيار. |
| **ChatGPT على iPhone أو Android** | ثبّت أو حدّث [تطبيق ChatGPT الرسمي](https://chatgpt.com/download/). سجّل الدخول إلى مساحة عمل مؤهلة، وافتح **Plugins**، وابحث عن **TaxTidy Israel**، ثم اختر **Install plugin** إذا ظهر الخيار. يجب أن تكون الإضافة ظاهرة في دليل مساحة العمل أو في الدليل العام. |

**حالة دليل ChatGPT العام.** يوفّر إصدار GitHub حزمة قابلة للتنزيل. يتطلّب الظهور في الدليل العام [تقديم الإضافة للمراجعة ثم نشرها عبر OpenAI](https://developers.openai.com/plugins/deploy/submission). قبل النشر، لا يمكن للحسابات الشخصية تثبيت إصدار GitHub من الدليل العام على الويب أو الهاتف. يتأثر الوصول أيضاً بالخطة والمنطقة وإعدادات مساحة العمل. [مساعدة OpenAI بشأن الإضافات](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)

### التثبيت من دليل المستودع على سطح المكتب

1. ثبّت [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) وسجّل الدخول. نفّذ الأمر في Terminal على macOS أو PowerShell على Windows.

   ```sh
   codex plugin marketplace add TimurMisharin/taxtidy-israel
   ```

2. أعد تشغيل تطبيق ChatGPT لسطح المكتب. افتح **Plugins**، واختر دليل **TaxTidy Israel**، ثم افتح الإضافة واختر **Install plugin**.
3. إذا لم يظهر الدليل، فتحقّق من نجاح الأمر ومن سماح التطبيق ومساحة العمل باستخدام الأدلة المحلية. [تعليمات OpenAI لإضافة الدليل](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)

### مساحات عمل ChatGPT المُدارة

يفتح مسؤول مساحة العمل **Admin → Plugins → Add → Import marketplace**، ويدخل `https://github.com/TimurMisharin/taxtidy-israel` في **Source**، ويترك **Path** وخانة مرجع Git فارغتين لمتابعة الفرع `main`. يوافق على الوصول إلى GitHub عند الطلب، ويراجع نتائج الاستيراد، ثم يتيح الإضافة للأعضاء كي يثبّتوها. [دليل الاستيراد من OpenAI](https://learn.chatgpt.com/docs/enterprise/plugin-management)

## بدء المراجعة

1. افتح محادثة جديدة واختر **@TaxTidy Israel**. العبرية هي اللغة الافتراضية. يمكنك طلب الإجابة بالعربية أو الإنجليزية أو الروسية.
2. اذكر السنة الضريبية والهدف. مثال «ساعدني في مراجعة ضرائبي في إسرائيل لعام 2025. ابدأ بالمستندات التي أحتاجها وما يثبته كل مستند».
3. راجع المستندات الأصلية المطلوبة، مثل **טופס 106** (النموذج 106) وشهادات البنك وإيصالات التبرعات. اسأل عمّا تمت مطابقته، وما ينقصك، والخطوة الرسمية التالية.

يمكن الحصول على إرشادات في المحادثة دون تشغيل أدوات محلية. تتطلّب حاسبة **2025** وأدوات PDF والتعرّف على النص بيئة Python/POSIX خاصة ومتوافقة وتبعيات منفصلة. قارِن الأرقام المستخرجة بالمستندات الأصلية. لا تتصل الإضافة تلقائياً بحسابك الضريبي ولا تقدّم الإقرارات. لا ترفع المستندات الضريبية أو بيانات الدخول إلى GitHub. [دليل إعداد بيئة التشغيل](taxtidy-israel/SETUP.md)

## موارد المشروع

- [مثال ببيانات اصطناعية](taxtidy-israel/DEMO.md) · [الإمكانات التي تم التحقق منها والقيود](taxtidy-israel/VERIFICATION.md)
- [التطوير وتجهيز الحزمة](DEVELOPMENT.md) · [الإبلاغ عن مشكلة](https://github.com/TimurMisharin/taxtidy-israel/issues) · [إشعارات تراخيص المكونات الخارجية](THIRD_PARTY_NOTICES.md)
