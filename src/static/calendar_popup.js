var DATEPICKER_DEFAULTS = {
    autohide: true,
    clearButton: true,
    orientation: "bottom auto",
    format: "yyyy-mm-dd",
    todayHighlight: true
};

var DATEPICKER_DEFAULTS_FUTUREONLY = {
    autohide: true,
    clearButton: true,
    orientation: "bottom auto",
    format: "yyyy-mm-dd",
    todayHighlight: true,
    minDate: new Date()
}

var first_startdate_selected = false;

$(document).ready(function() {
    document.querySelectorAll('input.nopastdates').forEach(function(el) {
        new Datepicker(el, DATEPICKER_DEFAULTS_FUTUREONLY);
    });
    document.querySelectorAll('input.dateinput').forEach(function(el) {
        new Datepicker(el, DATEPICKER_DEFAULTS);
    });

    var startEl = document.getElementById('id_start');
    if (startEl) {
        startEl.addEventListener('changeDate', function(e) {
            // if user selects start date for the first time, set end date to +1d
            var dp = Datepicker.getInstance(startEl);
            if (dp && dp.getDate() && !first_startdate_selected) {
                first_startdate_selected = true;
                var d = new Date(dp.getDate());
                d.setUTCDate(d.getUTCDate() + 1);  // +1d to the start date
                var endEl = document.getElementById('id_end');
                if (endEl) {
                    var endDp = Datepicker.getInstance(endEl);
                    if (endDp) endDp.setDate(d);
                }
            }
        });
    }

    var endEl = document.getElementById('id_end');
    if (endEl) {
        endEl.addEventListener('changeDate', function(e) {
            // disallow changing end date by logic if the end date was selected
            // earlier than start date
            first_startdate_selected = true;
        });
    }

    var agreementStartEl = document.getElementById('id_agreement_start');
    if (agreementStartEl) {
        agreementStartEl.addEventListener('changeDate', function(e) {
            var dp = Datepicker.getInstance(agreementStartEl);
            var agreementEndEl = document.getElementById('id_agreement_end');
            if (dp && dp.getDate() && agreementEndEl && !agreementEndEl.value) {
                var d = new Date(dp.getDate());
                d.setFullYear(d.getFullYear() + 1);
                d.setDate(d.getDate() - 1);
                var endDp = Datepicker.getInstance(agreementEndEl);
                if (endDp) endDp.setDate(d);
            }
        });
    }
});
