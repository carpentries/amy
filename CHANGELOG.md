# Changelog

All release notes prior to version v4.0.5 are kept in `docs/releases/` directory.

To add changelog for a given release version use `docs/generate_changelog.py` script,
e.g.:

```shell
$ python docs/generate_changelog.py v4.1
```

Then paste output from that script here.

-----------------------------------------------------------------

## v4.6.1 - 2025-01-28

### Features
* API: Add `state_verbose` API r/o field to models that have state` field - [#2747](https://github.com/carpentries/amy/pull/2747) by @pbanaszkiewicz


## v4.6 - 2025-01-20

### Bugfixes
* Emails: Improve managing instructor task in recruitments, new email action Instructor Task Created for Workshop - [#2739](https://github.com/carpentries/amy/pull/2739) by @pbanaszkiewicz

### Features
* chore(deps): Bump django from 4.2.17 to 4.2.18 - [#2740](https://github.com/carpentries/amy/pull/2740) by @dependabot[bot]
* chore(deps-dev): Bump virtualenv from 20.26.2 to 20.26.6 - [#2738](https://github.com/carpentries/amy/pull/2738) by @dependabot[bot]
* chore(deps): Bump jinja2 from 3.1.4 to 3.1.5 - [#2736](https://github.com/carpentries/amy/pull/2736) by @dependabot[bot]
* Update CICD workflow - [#2735](https://github.com/carpentries/amy/pull/2735) by @pbanaszkiewicz
* Allow admins to see upcoming teaching opportunities - [#2734](https://github.com/carpentries/amy/pull/2734) by @pbanaszkiewicz
* Display tasks per role summary in instructor dashboard - [#2733](https://github.com/carpentries/amy/pull/2733) by @pbanaszkiewicz
* Leverage full-text search in Postgres to improve searching for people and training requests - [#2732](https://github.com/carpentries/amy/pull/2732) by @pbanaszkiewicz
* Multiple changes - [#2731](https://github.com/carpentries/amy/pull/2731) by @pbanaszkiewicz
* Updates admin user documentation about automated emails - [#2730](https://github.com/carpentries/amy/pull/2730) by @maneesha
* [Emails] Complex strategy for instructor declined for workshop - [#2729](https://github.com/carpentries/amy/pull/2729) by @pbanaszkiewicz
* Bump django from 4.2.16 to 4.2.17 - [#2727](https://github.com/carpentries/amy/pull/2727) by @dependabot[bot]
* Update upload-artifact version to v4 - [#2716](https://github.com/carpentries/amy/pull/2716) by @froggleston


## v4.5 - 2024-11-30

### Features
* [Recruitment] Disallow multiple signups for the same person - [#2725](https://github.com/carpentries/amy/pull/2725) by @pbanaszkiewicz
* [Emails] Add condition for event in future in Instructor Confirmed for Workshop - [#2724](https://github.com/carpentries/amy/pull/2724) by @pbanaszkiewicz


## v4.4 - 2024-11-10

### Bugfixes
* [Emails] Change related object to Task in Instructor Confirmed for Workshop and to Award in Instructor Badge Awarded - [#2720](https://github.com/carpentries/amy/pull/2720) by @pbanaszkiewicz

### Features
* [Emails] Change email scheduled condition in some strategies - [#2722](https://github.com/carpentries/amy/pull/2722) by @pbanaszkiewicz
* [Emails] Limit instructor confirmed for workshop email - [#2718](https://github.com/carpentries/amy/pull/2718) by @pbanaszkiewicz
* [Emails] Enable membership onboarding email for membership rollovers - [#2715](https://github.com/carpentries/amy/pull/2715) by @pbanaszkiewicz
* [Emails] Remove RQ Jobs listings from event and task detail pages - [#2714](https://github.com/carpentries/amy/pull/2714) by @pbanaszkiewicz
* Bump waitress from 3.0.0 to 3.0.1 - [#2712](https://github.com/carpentries/amy/pull/2712) by @dependabot[bot]
* [Emails] Allow editing cancelled emails - [#2711](https://github.com/carpentries/amy/pull/2711) by @pbanaszkiewicz


## v4.3 - 2024-10-26

### Bugfixes
* [Emails] Update trigger for the host-instructor introduction - [#2699](https://github.com/carpentries/amy/pull/2699) by @pbanaszkiewicz
* [Emails] Extend REST API for events, scheduled emails, and fix too many logs - [#2674](https://github.com/carpentries/amy/pull/2674) by @pbanaszkiewicz
* [Emails] Fix template render issue with email update actions - [#2659](https://github.com/carpentries/amy/pull/2659) by @pbanaszkiewicz
* [Emails] Correct URLs in context for scheduled emails - [#2642](https://github.com/carpentries/amy/pull/2642) by @pbanaszkiewicz
* Never hide training requests with invalid code when filtering - [#2571](https://github.com/carpentries/amy/pull/2571) by @elichad
* Remove nonexistent field from knowledge domain lookup - [#2565](https://github.com/carpentries/amy/pull/2565) by @elichad

### Features
* chore: Update manual deployment steps - [#2708](https://github.com/carpentries/amy/pull/2708) by @pbanaszkiewicz
* Bump django from 4.2.15 to 4.2.16 - [#2706](https://github.com/carpentries/amy/pull/2706) by @dependabot[bot]
* [#1992] Rename Host->Host Site, Sponsor->Organiser - [#2705](https://github.com/carpentries/amy/pull/2705) by @pbanaszkiewicz
* Automatically generate and update survey link - [#2704](https://github.com/carpentries/amy/pull/2704) by @pbanaszkiewicz
* [Emails] Update Tag condition for some email actions - [#2702](https://github.com/carpentries/amy/pull/2702) by @pbanaszkiewicz
* [Emails] Link to other related scheduled emails - [#2701](https://github.com/carpentries/amy/pull/2701) by @pbanaszkiewicz
* [Emails] Rendering emails - switch to API serializers to fix error - [#2698](https://github.com/carpentries/amy/pull/2698) by @pbanaszkiewicz
* Bump cryptography from 42.0.7 to 43.0.1 - [#2692](https://github.com/carpentries/amy/pull/2692) by @dependabot[bot]
* [Emails] Cleanup feature flags - [#2690](https://github.com/carpentries/amy/pull/2690) by @pbanaszkiewicz
* Bump webob from 1.8.7 to 1.8.8 - [#2686](https://github.com/carpentries/amy/pull/2686) by @dependabot[bot]
* [Emails] Preview rendered jinja2+markdown email templates - [#2685](https://github.com/carpentries/amy/pull/2685) by @pbanaszkiewicz
* Bump django from 4.2.14 to 4.2.15 - [#2684](https://github.com/carpentries/amy/pull/2684) by @dependabot[bot]
* [Emails] Bunch of updates aimed at running email actions in new situations - [#2683](https://github.com/carpentries/amy/pull/2683) by @pbanaszkiewicz
* [Emails] Failed emails circuit breaker - [#2680](https://github.com/carpentries/amy/pull/2680) by @pbanaszkiewicz
* [Emails] Add missing email state - [#2677](https://github.com/carpentries/amy/pull/2677) by @pbanaszkiewicz
* [Emails] UI improvements for emails - [#2676](https://github.com/carpentries/amy/pull/2676) by @pbanaszkiewicz
* Bump setuptools from 69.5.1 to 70.0.0 - [#2672](https://github.com/carpentries/amy/pull/2672) by @dependabot[bot]
* [Emails] Management command to enable new emails for existing events - [#2671](https://github.com/carpentries/amy/pull/2671) by @pbanaszkiewicz
* Bump django from 4.2.13 to 4.2.14 - [#2670](https://github.com/carpentries/amy/pull/2670) by @dependabot[bot]
* Bump certifi from 2024.2.2 to 2024.7.4 - [#2669](https://github.com/carpentries/amy/pull/2669) by @dependabot[bot]
* [Emails] Updated technical documentation - [#2667](https://github.com/carpentries/amy/pull/2667) by @pbanaszkiewicz
* Bump djangorestframework from 3.15.1 to 3.15.2 - [#2666](https://github.com/carpentries/amy/pull/2666) by @dependabot[bot]
* Bump braces from 3.0.2 to 3.0.3 - [#2665](https://github.com/carpentries/amy/pull/2665) by @dependabot[bot]
* Bump urllib3 from 2.2.1 to 2.2.2 - [#2664](https://github.com/carpentries/amy/pull/2664) by @dependabot[bot]
* Update README.md - [#2663](https://github.com/carpentries/amy/pull/2663) by @froggleston
* [Emails] Add missing context variables - [#2658](https://github.com/carpentries/amy/pull/2658) by @pbanaszkiewicz
* [Emails] Add missing email template seeds for New Self-Organised Workshop and Ask For Website - [#2656](https://github.com/carpentries/amy/pull/2656) by @pbanaszkiewicz
* [Emails] New email Ask For Website - [#2655](https://github.com/carpentries/amy/pull/2655) by @pbanaszkiewicz
* [Emails] New self organised workshop - [#2654](https://github.com/carpentries/amy/pull/2654) by @pbanaszkiewicz
* [Emails] New email: PostWorkshop7Days - [#2653](https://github.com/carpentries/amy/pull/2653) by @pbanaszkiewicz
* Bump requests from 2.31.0 to 2.32.2 - [#2652](https://github.com/carpentries/amy/pull/2652) by @dependabot[bot]
* [Emails] New email: recruit helpers - [#2651](https://github.com/carpentries/amy/pull/2651) by @pbanaszkiewicz
* [Emails] New email host intructors introduction - [#2645](https://github.com/carpentries/amy/pull/2645) by @pbanaszkiewicz
* [Emails] Improvements to scheduled emails list and details - [#2640](https://github.com/carpentries/amy/pull/2640) by @pbanaszkiewicz
* [Emails] Validate rescheduled date/time to not be in past - [#2639](https://github.com/carpentries/amy/pull/2639) by @pbanaszkiewicz
* Bump gunicorn from 20.1.0 to 22.0.0 - [#2637](https://github.com/carpentries/amy/pull/2637) by @dependabot[bot]
* [Emails] List related scheduled emails - [#2636](https://github.com/carpentries/amy/pull/2636) by @pbanaszkiewicz
* Update datetime and time formats to include a timezone - [#2635](https://github.com/carpentries/amy/pull/2635) by @pbanaszkiewicz
* Bump sqlparse from 0.4.4 to 0.5.0 - [#2634](https://github.com/carpentries/amy/pull/2634) by @dependabot[bot]
* [#2624] Add CSRF_TRUSTED_ORIGINS because it was missing - [#2632](https://github.com/carpentries/amy/pull/2632) by @pbanaszkiewicz
* [#2624] Upgrade Django to v4.2 - [#2630](https://github.com/carpentries/amy/pull/2630) by @pbanaszkiewicz
* Fix2582 corporate workshop costs - [#2626](https://github.com/carpentries/amy/pull/2626) by @maneesha
* Bump pillow from 10.2.0 to 10.3.0 - [#2625](https://github.com/carpentries/amy/pull/2625) by @dependabot[bot]
* Bump black from 23.7.0 to 24.3.0 - [#2620](https://github.com/carpentries/amy/pull/2620) by @dependabot[bot]
* Bump django from 3.2.24 to 3.2.25 - [#2619](https://github.com/carpentries/amy/pull/2619) by @dependabot[bot]
* Bump django from 3.2.23 to 3.2.24 - [#2610](https://github.com/carpentries/amy/pull/2610) by @dependabot[bot]
* Bump cryptography from 41.0.6 to 42.0.0 - [#2609](https://github.com/carpentries/amy/pull/2609) by @dependabot[bot]
* [Chore] Unconditionally enable "ENFORCE_MEMBER_CODES" feature flag - [#2606](https://github.com/carpentries/amy/pull/2606) by @pbanaszkiewicz
* Bump pillow from 10.1.0 to 10.2.0 - [#2604](https://github.com/carpentries/amy/pull/2604) by @dependabot[bot]
* Bump jinja2 from 3.1.2 to 3.1.3 - [#2600](https://github.com/carpentries/amy/pull/2600) by @dependabot[bot]
* [Emails] Context JSON for email worker - [#2598](https://github.com/carpentries/amy/pull/2598) by @pbanaszkiewicz
* Member codes docs - [#2595](https://github.com/carpentries/amy/pull/2595) by @elichad
* Miscellaneous docs updates - [#2594](https://github.com/carpentries/amy/pull/2594) by @elichad
* Fix IntegrityError and make CoC agreement required - [#2593](https://github.com/carpentries/amy/pull/2593) by @elichad
* Bump cryptography from 41.0.4 to 41.0.6 - [#2592](https://github.com/carpentries/amy/pull/2592) by @dependabot[bot]
* [Emails] New membership onboarding email - [#2580](https://github.com/carpentries/amy/pull/2580) by @pbanaszkiewicz
* Make agreement_link required field in Membership model - [#2579](https://github.com/carpentries/amy/pull/2579) by @elichad
* Member codes feature - [#2575](https://github.com/carpentries/amy/pull/2575) by @elichad
* add CLDT tag - [#2573](https://github.com/carpentries/amy/pull/2573) by @maneesha
* Automatically assign learner TTT task membership based on code in training application - [#2572](https://github.com/carpentries/amy/pull/2572) by @elichad
* Instructor Training application - add question about Eventbrite URL and associated filter - [#2570](https://github.com/carpentries/amy/pull/2570) by @elichad
* Instructor Training applicaton - change checkboxes to questions about intent - [#2569](https://github.com/carpentries/amy/pull/2569) by @elichad
* Bump django from 3.2.20 to 3.2.23 - [#2563](https://github.com/carpentries/amy/pull/2563) by @dependabot[bot]
* Update autoresponses with member codes - [#2561](https://github.com/carpentries/amy/pull/2561) by @elichad
* Add soft validation of member codes to training request update form - [#2560](https://github.com/carpentries/amy/pull/2560) by @elichad
* Add a filter to the workshop request view for requests where an active member did not use their code - [#2559](https://github.com/carpentries/amy/pull/2559) by @elichad
* Add filter to training requests view for invalid codes - [#2558](https://github.com/carpentries/amy/pull/2558) by @elichad
* Add code seat availability check to IT application - [#2554](https://github.com/carpentries/amy/pull/2554) by @elichad
* Add further checks for invalid code to workshop request forms - [#2553](https://github.com/carpentries/amy/pull/2553) by @elichad
* Remove member affiliation question; remove code question from SO and WI forms - [#2552](https://github.com/carpentries/amy/pull/2552) by @elichad
* [Emails] Completed instructor training not yet badged - [#2551](https://github.com/carpentries/amy/pull/2551) by @pbanaszkiewicz
* Implement soft validation for member codes in training requests - [#2549](https://github.com/carpentries/amy/pull/2549) by @elichad
* Override link colours in banner to improve contrast - [#2548](https://github.com/carpentries/amy/pull/2548) by @elichad
* Enforce membership code on instructor training application - [#2544](https://github.com/carpentries/amy/pull/2544) by @elichad
* [Emails] Refactor receivers into class-based actions - [#2541](https://github.com/carpentries/amy/pull/2541) by @pbanaszkiewicz
* Bump urllib3 from 2.0.5 to 2.0.6 - [#2539](https://github.com/carpentries/amy/pull/2539) by @dependabot[bot]
* Autofill membership when accepting workshop requests - [#2538](https://github.com/carpentries/amy/pull/2538) by @elichad
* Bump cryptography from 41.0.3 to 41.0.4 - [#2537](https://github.com/carpentries/amy/pull/2537) by @dependabot[bot]
* Add membership code & validation to workshop requests - [#2532](https://github.com/carpentries/amy/pull/2532) by @elichad
* [Emails] Instructor training event approaching email - [#2529](https://github.com/carpentries/amy/pull/2529) by @pbanaszkiewicz
* Remove question about learner count from WRF - [#2523](https://github.com/carpentries/amy/pull/2523) by @elichad
* [Emails] Enable field `active` on EmailTemplates - [#2522](https://github.com/carpentries/amy/pull/2522) by @pbanaszkiewicz
* [Emails] Disable some notifications for non-admin users - [#2521](https://github.com/carpentries/amy/pull/2521) by @pbanaszkiewicz
* Update release procedure documentation - [#2519](https://github.com/carpentries/amy/pull/2519) by @elichad
* Make explicit where Instructors can include accommodations they need when signing up for workshop - [#2517](https://github.com/carpentries/amy/pull/2517) by @elichad
* [Emails] Use django-flags for feature flag management - [#2516](https://github.com/carpentries/amy/pull/2516) by @pbanaszkiewicz
* Update admin documentation for checkout - [#2514](https://github.com/carpentries/amy/pull/2514) by @elichad
* New checkout docs - [#2509](https://github.com/carpentries/amy/pull/2509) by @maneesha
* [Emails] Scheduled email log author - [#2506](https://github.com/carpentries/amy/pull/2506) by @pbanaszkiewicz
* [Emails] Prevent changes to emails in specific states - [#2494](https://github.com/carpentries/amy/pull/2494) by @pbanaszkiewicz
* [Emails] Template context variables documentation links - [#2491](https://github.com/carpentries/amy/pull/2491) by @pbanaszkiewicz
* Improve event validation and option filtering for training progress and instructor badge awarding - [#2471](https://github.com/carpentries/amy/pull/2471) by @elichad
* Add documentation for checkout project and DB changes - [#2464](https://github.com/carpentries/amy/pull/2464) by @elichad


## v4.2.3 - 2023-11-07

### Bugfixes
* Escape trainee notes in progress_description tag - [#2567](https://github.com/carpentries/amy/pull/2567) by @elichad

## v4.2.1 - 2023-08-15

### Bugfixes
* Make GitHub organization check case insensitive - [#2518](https://github.com/carpentries/amy/pull/2518) by @elichad

## v4.2.4 - 2024-03-22

### Features
* [#2617] Default training requests to preapproved only - [#2621](https://github.com/carpentries/amy/pull/2621) by @pbanaszkiewicz
* Remove references to open training - [#2618](https://github.com/carpentries/amy/pull/2618) by @maneesha

## v4.2.2 - 2023-09-27

### Features

* Add CLDT to admin domains - [#2536](https://github.com/carpentries/amy/pull/2536) by @elichad

## v4.2.1 - 2023-08-15

### Bugfixes
* Make GitHub organization check case insensitive - [#2518](https://github.com/carpentries/amy/pull/2518) by @elichad

## v4.2 - 2023-08-11

### Bugfixes
* Force HTTPS in `redirect_uri` generated by social auth - [#2513](https://github.com/carpentries/amy/pull/2513) by @pbanaszkiewicz
* Update conditions for progress messages at top of page - [#2512](https://github.com/carpentries/amy/pull/2512) by @elichad
* Allow admins to submit/update training progress with non GitHub URL - [#2510](https://github.com/carpentries/amy/pull/2510) by @elichad
* [#2426] Hide Anymail errors - [#2505](https://github.com/carpentries/amy/pull/2505) by @pbanaszkiewicz
* Add cancel button and fix validation bug on Get Involved form - [#2504](https://github.com/carpentries/amy/pull/2504) by @elichad
* Correct links in changes_log view - [#2466](https://github.com/carpentries/amy/pull/2466) by @elichad

### Features
* Remove use of text-white to override text colour - [#2515](https://github.com/carpentries/amy/pull/2515) by @elichad
* Check that GitHub contributions are associated with a Carpentries GH organisation - [#2502](https://github.com/carpentries/amy/pull/2502) by @elichad
* Bump cryptography from 41.0.2 to 41.0.3 - [#2501](https://github.com/carpentries/amy/pull/2501) by @dependabot[bot]
* Set permissions for Get Involved views - [#2500](https://github.com/carpentries/amy/pull/2500) by @elichad
* Update curriculum links - [#2496](https://github.com/carpentries/amy/pull/2496) by @maneesha
* Introduce separate views for Get Involved submissions - [#2492](https://github.com/carpentries/amy/pull/2492) by @elichad
* Update color palette for better accessibility - [#2490](https://github.com/carpentries/amy/pull/2490) by @elichad
* Bump certifi from 2023.5.7 to 2023.7.22 - [#2489](https://github.com/carpentries/amy/pull/2489) by @dependabot[bot]
* Improvements to trainee progress view - [#2487](https://github.com/carpentries/amy/pull/2487) by @elichad
* Additional immediate email actions - [#2481](https://github.com/carpentries/amy/pull/2481) by @pbanaszkiewicz
* Bump cryptography from 41.0.1 to 41.0.2 - [#2479](https://github.com/carpentries/amy/pull/2479) by @dependabot[bot]
* remove outdated issue template - [#2469](https://github.com/carpentries/amy/pull/2469) by @maneesha
* Email template create, update, delete views - [#2467](https://github.com/carpentries/amy/pull/2467) by @pbanaszkiewicz
* Add tests for training progress template tags - [#2465](https://github.com/carpentries/amy/pull/2465) by @elichad
* Adjust consents docs to support a less technical audience - [#2463](https://github.com/carpentries/amy/pull/2463) by @elichad
* Add accessibility testing workflow - [#2458](https://github.com/carpentries/amy/pull/2458) by @elichad
* Update trainee progress view - [#2453](https://github.com/carpentries/amy/pull/2453) by @elichad
* Improve scheduled email views - [#2448](https://github.com/carpentries/amy/pull/2448) by @pbanaszkiewicz
* Email module feature flag - [#2447](https://github.com/carpentries/amy/pull/2447) by @pbanaszkiewicz
* Update bulk training progress form to work with Get Involved step - [#2446](https://github.com/carpentries/amy/pull/2446) by @elichad
* Update instructor eligibility requirements with Get Involved step - [#2444](https://github.com/carpentries/amy/pull/2444) by @elichad
* Update filter for unevaluated Get Involved step - [#2443](https://github.com/carpentries/amy/pull/2443) by @elichad
* Initial email module - [#2434](https://github.com/carpentries/amy/pull/2434) by @pbanaszkiewicz
* Create "Get Involved" requirement and associated Involvement model - [#2431](https://github.com/carpentries/amy/pull/2431) by @elichad
* Rename Discussion to Welcome Session, remove deprecated TrainingRequirements - [#2420](https://github.com/carpentries/amy/pull/2420) by @elichad
* Remove 'evaluated_by' and 'discarded' fields from TrainingProgress - [#2416](https://github.com/carpentries/amy/pull/2416) by @elichad

### Testers
Thanks to the following AMY users for testing this release:
* @JFormoso
* @karenword
* @klbarnes20
* @maneesha
* @quirksahern
* @ragamouf
* @Talishask

## v4.1.2 - 2023-06-04

### Bugfixes
* Allow longer auth tokens for password reset - [#2430](https://github.com/carpentries/amy/pull/2430) by @elichad

### Features
* Bump cryptography from 40.0.2 to 41.0.0 - [#2432](https://github.com/carpentries/amy/pull/2432) by @dependabot[bot]

## v4.1.1 - 2023-05-28

### Features
* Bump requests from 2.27.1 to 2.31.0 - [#2423](https://github.com/carpentries/amy/pull/2423) by @dependabot[bot]
* Bump pymdown-extensions from 9.11 to 10.0 - [#2419](https://github.com/carpentries/amy/pull/2419) by @dependabot[bot]
* Bump django from 3.2.18 to 3.2.19 - [#2406](https://github.com/carpentries/amy/pull/2406) by @dependabot[bot]
* Bump black to 23.3.0 - [#2403](https://github.com/carpentries/amy/pull/2403) by @elichad

## v4.1 - 2023-04-30

### Bugfixes
* Set default filtering for training requests - [#2381](https://github.com/carpentries/amy/pull/2381) by @elichad

### Features
* Combine strategy for training request consents - [#2402](https://github.com/carpentries/amy/pull/2402) by @pbanaszkiewicz
* Bump sqlparse from 0.4.3 to 0.4.4 - [#2386](https://github.com/carpentries/amy/pull/2386) by @dependabot[bot]
* Add Titanium membership variant, remove prepopulation of membership benefits - [#2382](https://github.com/carpentries/amy/pull/2382) by @elichad
* Display person consents when merging - [#2376](https://github.com/carpentries/amy/pull/2376) by @pbanaszkiewicz
* Allow different term content on instructor training application - [#2375](https://github.com/carpentries/amy/pull/2375) by @elichad
* Update docs for consents - [#2374](https://github.com/carpentries/amy/pull/2374) by @elichad
* Display consents history in person edit view - [#2373](https://github.com/carpentries/amy/pull/2373) by @elichad
* update redis to >=4.5.4 - [#2369](https://github.com/carpentries/amy/pull/2369) by @elichad
* Updated docs for server infrastructure and backups - [#2366](https://github.com/carpentries/amy/pull/2366) by @pbanaszkiewicz
* Consents for training requests - [#2363](https://github.com/carpentries/amy/pull/2363) by @pbanaszkiewicz
* Reduce hardcoding of consent labels in UI - [#2361](https://github.com/carpentries/amy/pull/2361) by @elichad
* Colors for different builds - [#2357](https://github.com/carpentries/amy/pull/2357) by @pbanaszkiewicz
* Custom test runner - [#2356](https://github.com/carpentries/amy/pull/2356) by @pbanaszkiewicz
* Cache settings are now configurable via envvars - [#2354](https://github.com/carpentries/amy/pull/2354) by @pbanaszkiewicz
* bump isort to 5.12.0 and black to 22.3.0 - [#2348](https://github.com/carpentries/amy/pull/2348) by @elichad
* Fix internal errors from filters - [#2346](https://github.com/carpentries/amy/pull/2346) by @elichad
* Bump django from 3.2.17 to 3.2.18 - [#2341](https://github.com/carpentries/amy/pull/2341) by @dependabot[bot]
* Minor changes to run without Redis - [#2340](https://github.com/carpentries/amy/pull/2340) by @pbanaszkiewicz
* Improvements to AMY docs and UI - [#2337](https://github.com/carpentries/amy/pull/2337) by @elichad
* Consents: Remove old terms from code - [#2335](https://github.com/carpentries/amy/pull/2335) by @pbanaszkiewicz
* Bump cryptography from 39.0.0 to 39.0.1 - [#2334](https://github.com/carpentries/amy/pull/2334) by @dependabot[bot]
* Run `create_superuser` to create super user on application's start - [#2333](https://github.com/carpentries/amy/pull/2333) by @pbanaszkiewicz
* Seeding scripts - [#2330](https://github.com/carpentries/amy/pull/2330) by @pbanaszkiewicz
* Bump django from 3.2.16 to 3.2.17 - [#2329](https://github.com/carpentries/amy/pull/2329) by @dependabot[bot]
* update guidance about signing up for concurrent workshops - [#2326](https://github.com/carpentries/amy/pull/2326) by @maneesha
* Display timestamps of instructor signups on instructor recruitment page - [#2325](https://github.com/carpentries/amy/pull/2325) by @elichad
* Update text for conflicting workshops at instructor sign-up - [#2323](https://github.com/carpentries/amy/pull/2323) by @elichad
* [#2284] Add environment for building Docker - [#2319](https://github.com/carpentries/amy/pull/2319) by @pbanaszkiewicz* [#2284] Remove condition from develop branch - [#2318](https://github.com/carpentries/amy/pull/2318) by @pbanaszkiewicz
* [#2284] Correct `build` step condition event - [#2317](https://github.com/carpentries/amy/pull/2317) by @pbanaszkiewicz
* [partial #2284] Change python-test to cicd workflow - [#2316](https://github.com/carpentries/amy/pull/2316) by @pbanaszkiewicz
* Deploy to test-amy2 - [#2311](https://github.com/carpentries/amy/pull/2311) by @pbanaszkiewicz
* AWS CDK preparation - [#2309](https://github.com/carpentries/amy/pull/2309) by @pbanaszkiewicz
* Bump certifi from 2022.9.24 to 2022.12.7 - [#2306](https://github.com/carpentries/amy/pull/2306) by @dependabot[bot]
* [#2299] Update mkdocs theme to mkdocs-material - [#2301](https://github.com/carpentries/amy/pull/2301) by @pbanaszkiewicz
* Docker one-off commands - [#2300](https://github.com/carpentries/amy/pull/2300) by @pbanaszkiewicz
* Users guide navigation - [#2298](https://github.com/carpentries/amy/pull/2298) by @pbanaszkiewicz
* Instructor Selection user guide - [#2297](https://github.com/carpentries/amy/pull/2297) by @maneesha
* Remove unused management commands - [#2296](https://github.com/carpentries/amy/pull/2296) by @pbanaszkiewicz
* Documentation: add documentation on base views - [#2292](https://github.com/carpentries/amy/pull/2292) by @pbanaszkiewicz
* Documentation: sending emails - [#2286](https://github.com/carpentries/amy/pull/2286) by @pbanaszkiewicz
* Documentation: update procedures - [#2281](https://github.com/carpentries/amy/pull/2281) by @pbanaszkiewicz
* Documentation: update infrastructure - [#2280](https://github.com/carpentries/amy/pull/2280) by @pbanaszkiewicz
* Documentation: update templates documentation - [#2279](https://github.com/carpentries/amy/pull/2279) by @pbanaszkiewicz
* User doc updates - [#2263](https://github.com/carpentries/amy/pull/2263) by @maneesha

## v4.0.9 - 2023-03-13

### Bugfixes
* fix 500 error after posting invalid community role - [#2358](https://github.com/carpentries/amy/pull/2358) by @elichad

## v4.0.8 - 2023-02-18

### Bugfixes
* hotfix: check for null values when loading custom keys - [#2339](https://github.com/carpentries/amy/pull/2339) by @elichad

## v4.0.7 - 2023-01-28

### Bugfixes
* dev: Fix server error on organizations membership - [#2324](https://github.com/carpentries/amy/pull/2324) by @elichad

## v4.0.6 - 2022-12-05

### Bugfixes
* Fix Re-try button in Admin panel for RQJobs - [#2304](https://github.com/carpentries/amy/pull/2304) by @pbanaszkiewicz

## v4.0.5 - 2022-11-20

### Bugfixes
* Fix re-try button (switch from GET to POST) - [#2295](https://github.com/carpentries/amy/pull/2295) by @pbanaszkiewicz

### Features
* Switch from Yarn to NPM - [#2289](https://github.com/carpentries/amy/pull/2289) by @pbanaszkiewicz
* Update docker commands - [#2278](https://github.com/carpentries/amy/pull/2278) by @pbanaszkiewicz
* [#2268][#2273] Documentation: update applications documentation, update releases - [#2276](https://github.com/carpentries/amy/pull/2276) by @pbanaszkiewicz
* [#2267] Documentation: update database models - [#2275](https://github.com/carpentries/amy/pull/2275) by @pbanaszkiewicz

## v4.0.4 - 2022-11-03

### Bugfixes
* [#2254] Extend AllCountriesFilter, AllCountriesMultipleFilter: conditionally extend countries - [#2266](https://github.com/carpentries/amy/pull/2266) by @pbanaszkiewicz

## v4.0.3 - 2022-10-31

### Bugfixes
* [#2257] Fix: unquote ?next value for redirection - [#2265](https://github.com/carpentries/amy/pull/2265) by @pbanaszkiewicz

## v4.0.2 - 2022-10-24

### Hotfixes

1. Hotfix: Invalid argument name for template tags in upcoming_teaching_opportunities.html - [62bc5db](https://github.com/carpentries/amy/commit/62bc5db021453035f5231d7a61b9dbc12d6ad01b) by @pbanaszkiewicz

## v4.0.1 - 2022-10-23

### Bugfixes
* [#2249] Fix issues with empty event dates on upcoming teaching opportunities - [#2250](https://github.com/carpentries/amy/pull/2250) by @pbanaszkiewicz
* [#2243] Award details and award-delete issues - [#2248](https://github.com/carpentries/amy/pull/2248) by @pbanaszkiewicz

### Features
* [#2244] Sort instructor's workshop activity by event start date - [#2251](https://github.com/carpentries/amy/pull/2251) by @pbanaszkiewicz

## v4.0 - 2022-10-15

### Bugfixes
* [#2224] Community roles: change dates display [+ refactoring, bug fixing] - [#2230](https://github.com/carpentries/amy/pull/2230) by @pbanaszkiewicz
* [#2215] Fix: hide unused requirement types from New training progress form - [#2219](https://github.com/carpentries/amy/pull/2219) by @pbanaszkiewicz
* [#2202] Fix "Decline" Instructor Application error - [#2207](https://github.com/carpentries/amy/pull/2207) by @pbanaszkiewicz
* make new membership start day after previous ends - [#2152](https://github.com/carpentries/amy/pull/2152) by @maneesha
* Bugfix/2113 communityroles date range validation - [#2126](https://github.com/carpentries/amy/pull/2126) by @KamilKulerz

### Features
* [#2237] Edit admin notes for instructor selection - [#2238](https://github.com/carpentries/amy/pull/2238) by @pbanaszkiewicz
* Migrate trainers - [#2234](https://github.com/carpentries/amy/pull/2234) by @pbanaszkiewicz
* #2225 updates after last meeting - [#2233](https://github.com/carpentries/amy/pull/2233) by @pbanaszkiewicz
* [#2221] Autoassign Community Role when award is created - [#2232](https://github.com/carpentries/amy/pull/2232) by @pbanaszkiewicz
* [#2225] Disallow concurent community roles of the same type for the same person - [#2231](https://github.com/carpentries/amy/pull/2231) by @pbanaszkiewicz
* [#2224] Require dates for CommunityRole - [#2229](https://github.com/carpentries/amy/pull/2229) by @pbanaszkiewicz
* Bump oauthlib from 3.2.0 to 3.2.1 - [#2228](https://github.com/carpentries/amy/pull/2228) by @dependabot[bot]
* [#2220][#2222][#2223][#2226] Small fixes - [#2227](https://github.com/carpentries/amy/pull/2227) by @pbanaszkiewicz
* [#2194] Add field "Autoassign when award is created" to Community Role Config - [#2218](https://github.com/carpentries/amy/pull/2218) by @pbanaszkiewicz
* [#2025] Block creating Task if instructor/trainer community role is inactive - [#2217](https://github.com/carpentries/amy/pull/2217) by @pbanaszkiewicz
* [#2203] Reopen closed recruitment - [#2214](https://github.com/carpentries/amy/pull/2214) by @pbanaszkiewicz
* [#2196] Curriculum link - [#2213](https://github.com/carpentries/amy/pull/2213) by @pbanaszkiewicz
* Bump django from 3.2.14 to 3.2.15 - [#2212](https://github.com/carpentries/amy/pull/2212) by @dependabot[bot]
* [#2195][#2199] Additional filters in instructor selection - [#2211](https://github.com/carpentries/amy/pull/2211) by @pbanaszkiewicz
* [#2174][#2198][#2200][#2201] small fixes for instructor selection - [#2210](https://github.com/carpentries/amy/pull/2210) by @pbanaszkiewicz
* [#2171] instructor checkout steps single badge - [#2209](https://github.com/carpentries/amy/pull/2209) by @pbanaszkiewicz
* [#2175] Update verbiage on "Training Progress" contribution form - [#2208](https://github.com/carpentries/amy/pull/2208) by @pbanaszkiewicz
* [#2170] Instructor badge display - [#2206](https://github.com/carpentries/amy/pull/2206) by @pbanaszkiewicz
* [#2169] Use Single Instructor Badge in Trainees view - [#2205](https://github.com/carpentries/amy/pull/2205) by @pbanaszkiewicz
* [#2168] Update workshop staff searching with instructor community role - [#2193](https://github.com/carpentries/amy/pull/2193) by @pbanaszkiewicz
* [#2167] Command to assign instructor community roles + tests - [#2192](https://github.com/carpentries/amy/pull/2192) by @pbanaszkiewicz
* [#1162][#2166] New single Instructor badge - [#2191](https://github.com/carpentries/amy/pull/2191) by @pbanaszkiewicz
* [#2114] Community role award limited to person - [#2190](https://github.com/carpentries/amy/pull/2190) by @pbanaszkiewicz
* Bump waitress from 2.1.1 to 2.1.2 - [#2186](https://github.com/carpentries/amy/pull/2186) by @dependabot[bot]
* [#2155] Filter open Instructor Recruitments by user application - [#2185](https://github.com/carpentries/amy/pull/2185) by @pbanaszkiewicz
* [#1875] No django-compressor, whitenoise instead - [#2184](https://github.com/carpentries/amy/pull/2184) by @pbanaszkiewicz
* [#2072][#2138] Counting person's roles correctly - [#2183](https://github.com/carpentries/amy/pull/2183) by @pbanaszkiewicz
* [#2153][#2154] Recruitment event requirements (date in future + location data) - [#2182](https://github.com/carpentries/amy/pull/2182) by @pbanaszkiewicz
* [#2083] Priority automatic calculation when recruitment is created - [#2181](https://github.com/carpentries/amy/pull/2181) by @pbanaszkiewicz
* [#2125] Custom keys for CommunityRoleConfig - [#2180](https://github.com/carpentries/amy/pull/2180) by @pbanaszkiewicz
* [#2066] Close signups - [#2179](https://github.com/carpentries/amy/pull/2179) by @pbanaszkiewicz
* [#2082] Admin signs up Instructor on their behalf - [#2178](https://github.com/carpentries/amy/pull/2178) by @pbanaszkiewicz
* [#2078] Maintenance: update Django to version 3.2 LTS - [#2177](https://github.com/carpentries/amy/pull/2177) by @pbanaszkiewicz
* [#2069] Resign from recruitment - [#2165](https://github.com/carpentries/amy/pull/2165) by @pbanaszkiewicz
* Bump django from 2.2.27 to 2.2.28 - [#2163](https://github.com/carpentries/amy/pull/2163) by @dependabot[bot]
* Curie -> Skłodowska-Curie - [#2161](https://github.com/carpentries/amy/pull/2161) by @slayoo
* Bump urijs from 1.19.10 to 1.19.11 - [#2160](https://github.com/carpentries/amy/pull/2160) by @dependabot[bot]
* [#2157] Fix: remove interest column from instructor recruitment list - [#2159](https://github.com/carpentries/amy/pull/2159) by @pbanaszkiewicz
* [#2156] Fix column name (Notes from RC->Notes from admin) - [#2158](https://github.com/carpentries/amy/pull/2158) by @pbanaszkiewicz
* Training search - [#2151](https://github.com/carpentries/amy/pull/2151) by @maneesha
* Bump waitress from 2.1.0b0 to 2.1.1 - [#2146](https://github.com/carpentries/amy/pull/2146) by @dependabot[bot]
* [#2065] Confirm and decline instructor signups - [#2143](https://github.com/carpentries/amy/pull/2143) by @pbanaszkiewicz
* Bump urijs from 1.19.9 to 1.19.10 - [#2142](https://github.com/carpentries/amy/pull/2142) by @dependabot[bot]
* Bump urijs from 1.19.7 to 1.19.9 - [#2141](https://github.com/carpentries/amy/pull/2141) by @dependabot[bot]
* add submission date column to all WRF views - [#2137](https://github.com/carpentries/amy/pull/2137) by @maneesha
* [#2068] Instructor Signup form - [#2136](https://github.com/carpentries/amy/pull/2136) by @pbanaszkiewicz
* update email address from checkout to instructor.training - [#2135](https://github.com/carpentries/amy/pull/2135) by @maneesha
* Typos - [#2134](https://github.com/carpentries/amy/pull/2134) by @maneesha
* Instructor training form text  - [#2133](https://github.com/carpentries/amy/pull/2133) by @maneesha
* add link to help guides to menu - [#2132](https://github.com/carpentries/amy/pull/2132) by @maneesha
* How to merge duplicate persons - [#2131](https://github.com/carpentries/amy/pull/2131) by @maneesha
* Some tests misusing assertTrue for comparisons fix - [#2130](https://github.com/carpentries/amy/pull/2130) by @code-review-doctor
* Bump django from 2.2.26 to 2.2.27 - [#2128](https://github.com/carpentries/amy/pull/2128) by @dependabot[bot]
* [#2067] Upcoming Teaching Opportunities on instructor page - [#2127](https://github.com/carpentries/amy/pull/2127) by @pbanaszkiewicz
* [#2064] Edit recruitment notes in UI using async API call - [#2124](https://github.com/carpentries/amy/pull/2124) by @pbanaszkiewicz
* Update text. - [#2123](https://github.com/carpentries/amy/pull/2123) by @sheraaronhurt
* Remove covid-19 and add workshops webpage - [#2122](https://github.com/carpentries/amy/pull/2122) by @sheraaronhurt
* Remove regional coordinators - [#2121](https://github.com/carpentries/amy/pull/2121) by @sheraaronhurt
* [#2063] List instructor recruitments - [#2120](https://github.com/carpentries/amy/pull/2120) by @pbanaszkiewicz
* Update packages - [#2119](https://github.com/carpentries/amy/pull/2119) by @pbanaszkiewicz
* Bump pillow from 8.4.0 to 9.0.0 - [#2116](https://github.com/carpentries/amy/pull/2116) by @dependabot[bot]
* Auto emails docs - [#2112](https://github.com/carpentries/amy/pull/2112) by @maneesha
