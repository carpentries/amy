jQuery(function () {
    let person, role, event;
    $("#id_task-seat_membership").select2({
        ajax: {
            data: (params) => {
                const query = {
                    person: person,
                    role: role,
                    event: event,
                    // `field_id` is required on backend by django-select2 views
                    field_id: $("#id_task-seat_membership").data("field_id"),
                    ...params,
                };
                return query;
            },
        },
    });
    // update variables when a selection is made
    $("#id_task-person").on("select2:select", (e) => {
        const data = e.params.data;
        person = data.id;
    });
    $("#id_task-role").on("change", (e) => {
        console.log(e.target.value);
        role = e.target.value
    });
    $("#id_task-event").on("select2:select", (e) => {
        const data = e.params.data;
        event = data.id;
    });
});
