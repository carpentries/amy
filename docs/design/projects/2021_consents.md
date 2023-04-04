# Consents

[GitHub project](https://github.com/carpentries/amy/projects/3).

This project aims to provide more configurable, more extensible and more descriptive
consents for the users.

## Previous design

Consents were stored in the Person model.

## New design

New models have been created for consent terms (Term), the options for each particular term (TermOption), and the relationship between a Person and their preferred option for each term (Consent). This new structure makes it easier to create and edit terms/options without making a database migration. If a new term is added, all users will be asked for their consent the next time they log in to AMY.

Consents are also collected in the instructor training application form. These consents are managed with the TrainingRequestConsent model, and if a Person is created from a training request, the TrainingRequestConsents from that request will be converted to Consents for that Person.