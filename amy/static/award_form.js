
$(document).ready(function () {
    let person = $("#id_award-person").val();
    $("#id_award-event").select2({
        ajax: {
            data: (params) => {
                const query = {
                    person: person,
                    // `field_id` is required on backend by django-select2 views
                    field_id: $("#id_award-event").data("field_id"),
                    ...params,
                };
                return query;
            },
        },
    });
});

