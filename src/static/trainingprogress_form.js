function updateTrainingProgressForm() {
    /* At this moment, `this` should be <select> tag of "Type" field. */
    var type = $(this).find(":selected").text();
    var training_div = $(this).closest('form').find('#div_id_event');
    var url_div = $(this).closest('form').find('#div_id_url');
    var involvement_type_div = $(this).closest('form').find('#div_id_involvement_type');
    var date_div = $(this).closest('form').find('#div_id_date');
    var trainee_notes_div = $(this).closest('form').find('#div_id_trainee_notes');

    if (type == 'Training') {
        training_div.show();
    } else {
        training_div.hide();
        var event = training_div.find('#id_event');
        if (event.val() != undefined) {
            event.val(null).trigger('change');
        }
    }

    if (type == 'Get Involved') {
        url_div.show();
        involvement_type_div.show();
        date_div.show();
        trainee_notes_div.show();
    } else {
        url_div.hide();
        url_div.find('#id_url').val("");
        involvement_type_div.hide();
        involvement_type_div.find('input[name=involvement_type]').prop('checked', false);
        date_div.hide();
        date_div.find('#id_date').val(null);
        trainee_notes_div.hide();
    }
}

$(document).ready(function () {
    /*
    TrainingProgress forms: show/hide training and url fields, depending on
    selected TrainingProgress type.
    */

    var selectField = $('form.training-progress #id_requirement')
    selectField.change(updateTrainingProgressForm);
    updateTrainingProgressForm.call(selectField);

    let trainee = $("#id_trainee").val();
    $("#id_event").select2({
        ajax: {
            data: (params) => {
                const query = {
                    trainee: trainee,
                    // `field_id` is required on backend by django-select2 views
                    field_id: $("#id_event").data("field_id"),
                    ...params,
                };
                return query;
            },
        },
    });
});

