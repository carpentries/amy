# Community Roles

[GitHub project](https://github.com/carpentries/amy/projects/5).

This project is an extension, and continuation of a concept of "badges" in AMY. Every
member of The Carpentries community is assigned a specific role (most often it's
"instructor", but some people can be "lesson maintainers", "regional coordinators",
"task force members", and others). Every role may require different configuration (e.g.
link to a specific award type, additional URLs, link to a membership), it can also
allow for auto-assignment of a role when given badge is awarded to a person.

Interesting consequence of configurable community role (`CommunityRoleConfig` model) is
dynamic form for assigning community roles to people. This form needs to respond to
selected role configuration.

Important advantage of community roles over badges is inactivation reason and activity
period (start / end of the role).
