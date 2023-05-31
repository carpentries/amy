
function updateTrainingProgressForm() {
    // TODO: move this to a dedicated file
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
        // TODO: remove values from involvement_type and date
        url_div.hide();
        involvement_type_div.hide();
        date_div.hide();
        trainee_notes_div.hide();
        url_div.find('#id_url').val("");
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
});
