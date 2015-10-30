var DATEPICKER_DEFAULTS = {
    autoclose: true,
    clearBtn: true,
    format: "yyyy-mm-dd",
    todayHighlight: true
};

var first_startdate_selected = false;

$(document).ready(function() {
    $("#id_start, #id_end").datepicker(DATEPICKER_DEFAULTS);
    $("#id_event-start, #id_event-end").datepicker(DATEPICKER_DEFAULTS);
    $("#id_todo-due, #id_form-0-due, #id_form-1-due, #id_form-2-due, " +
      "#id_form-3-due, #id_form-4-due, #id_form-5-due, #id_form-6-due, " +
      "#id_form-6-due, #id_form-7-due, #id_form-8-due, #id_form-9-due, " +
      "#id_form-10-due, #id_form-11-due, #id_due"
    ).datepicker({
        autoclose: true,
        clearBtn: true,
        format: "yyyy-mm-dd",
        todayHighlight: true,
        orientation: "bottom auto"
    });

    $('#id_start').on('changeDate', function(e) {
        // if user selects start date for the first time, set end date to +1d
        if (e.date && !first_startdate_selected) {
            first_startdate_selected = true;
            d = e.date;
            d.setUTCDate(d.getUTCDate() + 1);  // +1d to the start date
            $('#id_end').datepicker('update', d);
        }
    });
    $('#id_end').on('changeDate', function(e) {
        // disallow changing end date by logic if the end date was selected
        // earlier than start date
        first_startdate_selected = true;
    });
});
