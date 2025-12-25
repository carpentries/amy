// show 'id_instructor_availability' if preferred dates < 2mo away OR "other" specified
jQuery(() => {
    const cutoffTime = 1000 * 60 * 60 * 24 * 30 * 2; // default cutoff time: 60 days
    const instructorAvail = $('#div_id_instructor_availability');
    const instructorAvailInput = $('#id_instructor_availability');
    const preferredDatesInput = $('#id_preferred_dates');
    const otherDatesInput = $('#id_other_preferred_dates');
    const klass = 'd-none';

    const logic = () => {
        if (preferredDatesInput.val()) {
            const selectedDate = preferredDatesInput.datepicker('getDate');
            const today = new Date();
            if (selectedDate.getTime() - today.getTime() < cutoffTime) {
                instructorAvail.removeClass(klass);
                instructorAvailInput.prop('required', true);
            } else {
                instructorAvail.addClass(klass);
                instructorAvailInput.prop('required', false);
            }
        } else if (otherDatesInput.val()) {
            instructorAvail.removeClass(klass);
            instructorAvailInput.prop('required', true);
        } else {
            instructorAvail.addClass(klass);
            instructorAvailInput.prop('required', false);
        }
    };
    logic();

    preferredDatesInput.on("changeDate input", () => {
        // update datepicker with current input value
        $(this).datepicker('update');
        logic();
    });

    otherDatesInput.on("change", () => {
        logic();
    });
});
