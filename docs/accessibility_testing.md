# Accessibility Testing in AMY

## Automated Testing

The automated tests aim to test one page corresponding to each template in `amy/templates` (including base templates and the `includes` subfolder).

### Workflow

The [GitHub Actions workflow](https://github.com/carpentries/amy/blob/develop/.github/workflows/accessibility.yml) includes options for testing with both [pa11y](https://pa11y.org/) and [Google Lighthouse](https://github.com/GoogleChrome/lighthouse). In both cases, the report can be found in the artifacts attached to the workflow run. The report contains one HTML file for each page covered by the tests, plus a summary file (something like `index.html`).

### Local testing

See the [AMY README](https://github.com/carpentries/amy#run-accessibility-tests-locally) for instructions on running the tests on your own machine.

### Limitations

The following pages cannot be effectively tested automatically at the moment. Problems include:

* page inaccessible to logged-in admin (`/terms/action_required``)
* objects unavailable (e.g. no available signups for instructors to view)
* file upload required (bulk uploads)
* domain/slug required in URL, but organizations and events are randomly generated

```json
"http://127.0.0.1:8000/terms/action_required/",
"http://127.0.0.1:8000/dashboard/instructor/teaching_opportunities/<int:recruitment_pk>/signup",
"http://127.0.0.1:8000/requests/bulk_upload_training_request_scores/",
"http://127.0.0.1:8000/requests/bulk_upload_training_request_scores/confirm/",
"http://127.0.0.1:8000/fiscal/organization/<str:org_domain>/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/review_metadata_changes/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/delete/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/edit/",
"http://127.0.0.1:8000/workshops/persons/bulk_upload/confirm/",
"http://127.0.0.1:8000/workshops/event/<slug:slug>/validate/",
```

## Manual Testing Workflow

This assumes you are testing in Google Chrome on a Windows computer. It's also possible to test in other browsers and OSs (indeed, this is encouraged), but some tools and features may differ (e.g. Device Mode). The AMY team are not experts, so this workflow is likely to evolve over time.

1. Bookmark the [Web Content Accessibility Guidelines 2.1](https://www.w3.org/TR/WCAG21), which we'll be using as a reference throughout.
1. Create a spreadsheet which lists all the criteria, so you can mark each one passed or failed. Alternatively, use the [WCAG-EM Report Tool](https://www.w3.org/WAI/eval/report-tool/), but note that it won't save your data if you close the page.
1. Install the [WAVE](https://wave.webaim.org/extension/) and [axe devTools](https://www.deque.com/axe/devtools/) extensions (you don't need the Pro version of axe devTools)
1. Run WAVE and axe devTools on the target page. Where there are failures, the extensions will state the associated WCAG criterion - mark this criterion failed.
1. Run Lighthouse and/or Pa11y on a local version of the page (see [Run accessibility tests locally](../README.md#run-accessibility-tests-locally)), and note any failures. These should broadly match the output of axe devTools, but each package is slightly different in what info it provides.
1. Step through the [A11y Project Checklist](https://www.a11yproject.com/checklist/) and note any failures. Each checklist item is matched to a WCAG criterion.
1. Use the [Nu Html Checker](https://validator.w3.org/nu/) to validate the HTML. You can do this by setting the input to 'Check by text input' and copy-pasting the test page's source code into it. **Note: don't do this with the DJDT panel enabled, it makes the source code much larger and the checker will crash.** (WCAG criterion: [4.1.1 Parsing](https://www.w3.org/TR/WCAG21/#parsing))
1. Use the [Device Mode](https://developer.chrome.com/docs/devtools/device-mode/) features in Chrome DevTools to simulate a mobile viewport. Use the 'Mobile S - 320px' width preset (on the bar just below the dimensions). Check if the page scrolls in two dimensions (bad) and if any content or functionality is lost. (WCAG criteria: [1.3.4 Orientation](https://www.w3.org/TR/WCAG21/#orientation) and [1.4.10 Reflow](https://www.w3.org/TR/WCAG21/#reflow))
1. Use a screen reader (e.g. [NVDA](https://www.nvaccess.org/download/), which is free) and keyboard-only navigation to operate the page. Is anything confusing or inaccessible? Map it to the appropriate WCAG criterion. (This step requires some practice with NVDA to effectively model how full-time screen reader users navigate pages. See [Further Reading](#further-reading) below.)
1. Manually study the page to fill in any gaps that need some human assessment (e.g. [WCAG 1.3.5 Identify Input Purpose](https://www.w3.org/TR/WCAG21/#identify-input-purpose), [2.4.5 Multiple Ways](https://www.w3.org/TR/WCAG21/#multiple-ways), [2.5.x Input Modalities](https://www.w3.org/TR/WCAG21/#input-modalities), [3.2.3 Consistent Navigation](https://www.w3.org/TR/WCAG21/#consistent-navigation), [3.2.4 Consistent Identification](https://www.w3.org/TR/WCAG21/#consistent-identification), [3.3.x Input Assistance](https://www.w3.org/TR/WCAG21/#input-assistance))
1. If the page has multiple states (e.g. a dropdown expanded, date picker activated, content appearing on hover/focus, etc.), repeat the process with the page in each state.
1. If unsure if a pattern is a failure of a particular criterion X, read the 'Understanding X' and 'How to Meet X' pages, linked from X in the WCAG 2.1 document. If still unsure, make a note and move on.

## Further Reading

* [Website Accessibility Conformance Evaluation Methodology (WCAG-EM) 1.0](https://www.w3.org/TR/WCAG-EM/#procedure) - Procedure for selecting and auditing pages.
* [How I Use My Screen Reader - Rhea Guntalalib](https://vimeo.com/456535774/f41d56c54d) (52 minute video)
* [How A Screen Reader User Accesses The Web - Léonie Watson](https://www.smashingmagazine.com/2019/02/accessibility-webinar/) (1 hour, 12 minute video)
* [Keyboard Shortcuts for NVDA - WebAIM](https://webaim.org/resources/shortcuts/nvda)
* [Using NVDA to Evaluate Web Accessibility - WebAIM](https://webaim.org/articles/nvda/)
* [Perform an accessibility review on your website - Indiana University](https://kb.iu.edu/d/atmv)
* [A 'learn as you do' accessibility checklist](https://uxdesign.cc/a-learn-as-you-do-accessibility-checklist-c657d9ed2c62)
* [Introduction to Web Accessibility - edX](https://www.edx.org/course/web-accessibility-introduction) (self-paced course)
* [A11y Bookmarklets](https://a11y-tools.com/bookmarklets/) - A collection of accessibility-focused tools
