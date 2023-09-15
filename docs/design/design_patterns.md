# Design Patterns Reference

Due to the size of the AMY codebase and the number of views available, it can be tricky to figure out if something has been done before or not.

This document acts as a reference for where certain design patterns can be found in the UI and code base.

## Forms

### Update choice field options dynamically when a different field is updated

**Demo:** Go to the edit view for any Person with an Instructor badge, and select the "Community Roles" tab. Notice how changing the "Role name" selection between "Maintainer" and "Instructor" updates the options available under "Associated award" and "Generic relation object."

**Method:** It's not possible to make these dynamic updates using Django without submitting the form. Instead, we must use JavaScript.
1. Use JavaScript to change the request that is used to get the available choices for the dynamically changing field. Add the dependent field as a parameter in the request. (e.g. `$("#id_communityrole-award").select2({...})` in [/static/communityrole_form.js](../../amy/static/communityrole_form.js))
2. In the relevant form, ensure that the JS file is included under the `Media` metaclass (e.g. `CommunityRoleForm` in [/communityroles/forms.py](../../amy/communityroles/forms.py))
3. In the relevant lookup view, check for the presence of the extra parameters and use them to filter the results as needed (e.g. `AwardLookupView` in [/workshops/lookups.py](../../amy/workshops/lookups.py))
4. Write tests using different parameter settings (e.g. `TestAwardLookupView` in [/workshops/tests/test_lookups.py](../../amy/workshops/tests/test_lookups.py))

### Make a field required/not required according to another field's value

**Demo**: Go to the edit view for any Person with an Instructor badge, and select the "Community Roles" tab. Leave the rest of the form empty, and notice how changing the "Role name" selection between "Trainer" and "Instructor" changes which fields give a "Please fill in this field" error if you click Submit.

**Method:** It's not possible to make these dynamic updates using Django without submitting the form. Instead, we must use JavaScript.
1. Use JavaScript to set the `required` property on the dynamically changing field when the dependent field is updated. (e.g. in [/static/communityrole_form.js](../../amy/static/communityrole_form.js))
2. In the relevant form, ensure that the JS file is included under the `Media` metaclass (e.g. `CommunityRoleForm` in [/communityroles/forms.py](../../amy/communityroles/forms.py))
3. Ensure that the relevant form/model has validation that matches the dynamic behaviour (e.g. `CommunityRoleForm.clean()` in [/communityroles/forms.py](../../amy/communityroles/forms.py))

## Tests

### Migration tests

Use the `django_test_migrations` package, e.g. [/workshops/tests/test_migrations.py](../../amy/workshops/tests/test_migrations.py)