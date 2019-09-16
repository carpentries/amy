var DATEPICKER_DEFAULTS = {
    autoclose: true,
    clearBtn: true,
    orientation: "bottom auto",
    format: "yyyy-mm-dd",
    todayHighlight: true
};

var DATEPICKER_DEFAULTS_FUTUREONLY = {
    autoclose: true,
    clearBtn: true,
    orientation: "bottom auto",
    format: "yyyy-mm-dd",
    todayHighlight: true,
    startDate: new Date()
}

var first_startdate_selected = false;

$(document).ready(function() {
    $('input.nopastdates').datepicker(DATEPICKER_DEFAULTS_FUTUREONLY);
    $('input.dateinput').datepicker(DATEPICKER_DEFAULTS);
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
