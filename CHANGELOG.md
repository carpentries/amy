# Changelog

All release notes prior to version v4.1 are kept in `docs/releases/` directory.

To add changelog for a given release version use `docs/generate_changelog.py` script,
e.g.:

```shell
$ python docs/generate_changelog.py v4.1
```

Then paste output from that script here.

-----------------------------------------------------------------

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
