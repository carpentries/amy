/**
 * Import / update event form fields from a workshop URL.
 * Fetches metadata directly from GitHub (browser-side) using fetchWorkshopMetadata()
 * defined in workshop_metadata.js.
 */

function _fillEventForm(data) {
    $("#id_slug").val(data.slug);
    $("#id_start").val(data.start);
    $("#id_end").val(data.end);
    $("#id_reg_key").val(data.reg_key);
    $("#id_url").val(data._sourceUrl);

    // Select2 doesn't support programmatical search
    // so we're not going to fill the language for now

    // contact requires a couple of steps
    // 1. clear options
    $("#id_contact").find("option").remove();
    // 2. add options
    data.contact.forEach(element => {
        $("#id_contact").append(new Option(element, element, false, false));
    });
    // 3. select
    $("#id_contact").val(data.contact).trigger("change");

    $('#id_venue').val(data.venue);
    $('#id_address').val(data.address);
    $('#id_country').val(data.country);
    $('#id_latitude').val(data.latitude);
    $('#id_longitude').val(data.longitude);
}

async function import_from_url(url) {
    const data = await fetchWorkshopMetadata(url);
    data._sourceUrl = url;

    $("#event_import_url").removeClass('is-invalid');
    $("#url_help").removeClass('invalid-feedback');
    $('#import_url_modal').modal('hide');
    $('#error_message').addClass('d-none');

    _fillEventForm(data);

    $("#id_comment").val(
        "INSTRUCTORS: " + data.instructors.join(", ") + "\n\n" +
        "HELPERS: " + data.helpers.join(", ")
    );
}

async function update_from_url(url, action) {
    const data = await fetchWorkshopMetadata(url);
    data._sourceUrl = url;

    $("#event_update_url").removeClass('is-invalid');
    $("#url_help").removeClass('invalid-feedback');
    $('#update_url_modal').modal('hide');
    $('#error_message').addClass('d-none');

    switch (action) {
        case 'overwrite':
            _fillEventForm(data);
            $("#id_comment").val(
                "INSTRUCTORS: " + data.instructors.join(", ") + "\n\n" +
                "HELPERS: " + data.helpers.join(", ")
            );
            break;

        case 'skip':
        default:
            if ($("#id_slug").val() === "") { $("#id_slug").val(data.slug); }
            if ($("#id_start").val() === "") { $("#id_start").val(data.start); }
            if ($("#id_end").val() === "") { $("#id_end").val(data.end); }
            if ($("#id_reg_key").val() === "") { $("#id_reg_key").val(data.reg_key); }
            if ($("#id_url").val() === "") { $("#id_url").val(data._sourceUrl); }

            // Select2 doesn't support programmatical search
            // so we're not going to fill the language for now

            if ($("#id_contact").val() === "") {
                $("#id_contact").find("option").remove();
                data.contact.forEach(element => {
                    $("#id_contact").append(new Option(element, element, false, false));
                });
                $("#id_contact").val(data.contact).trigger("change");
            }
            if ($("#id_venue").val() === "") { $('#id_venue').val(data.venue); }
            if ($("#id_address").val() === "") { $('#id_address').val(data.address); }
            if ($("#id_country").val() === "") { $('#id_country').val(data.country); }
            if ($("#id_latitude").val() === "") { $('#id_latitude').val(data.latitude); }
            if ($("#id_longitude").val() === "") { $('#id_longitude').val(data.longitude); }

            $("#id_comment").val(
                $("#id_comment").val() +
                "INSTRUCTORS: " + data.instructors.join(", ") + "\n\n" +
                "HELPERS: " + data.helpers.join(", ")
            );
            break;
    }
}

$(function () {
    $('#import_url_form').submit(function (e) {
        e.preventDefault();

        const btn = $(this).find('button[type=submit]');
        btn.attr('disabled', true);

        import_from_url($(this).find(':input[name=url]').val())
            .catch(function (error) {
                $("#event_import_url").addClass('is-invalid');
                $("#url_help").addClass('invalid-feedback');
                $('#error_message').text(error.message);
                $('#error_message').removeClass('d-none');
            })
            .finally(function () {
                btn.attr('disabled', false);
            });
    });

    $('#update_url_form').submit(function (e) {
        e.preventDefault();

        const btn = $(this).find('button[type=submit]');
        btn.attr('disabled', true);

        update_from_url(
            $(this).find(':input[name=url]').val(),
            $(this).find(':input[type=radio]:checked').val()
        )
            .catch(function (error) {
                $("#event_update_url").addClass('is-invalid');
                $("#url_help").addClass('invalid-feedback');
                $('#error_message').text(error.message);
                $('#error_message').removeClass('d-none');
            })
            .finally(function () {
                btn.attr('disabled', false);
            });
    });
});
