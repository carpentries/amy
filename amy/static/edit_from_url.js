function import_from_url(url) {
  return $.get("/workshops/events/import/", {'url': url}, function(data) {
    $("#event_import_url").removeClass('is-invalid');
    $("#url_help").removeClass('invalid-feedback');
    $('#import_url_modal').modal('hide');
    $('#error_message').addClass('d-none');

    $("#id_slug").val(data.slug);
    $("#id_start").val(data.start);
    $("#id_end").val(data.end);
    $("#id_reg_key").val(data.reg_key);
    $("#id_url").val(url);

    // Select2 doesn't support programmatical search
    // so we're not going to fill the language for now

    $("#id_contact").val(data.contact);
    $('#id_venue').val(data.venue);
    $('#id_address').val(data.address);
    $('#id_country').val(data.country);
    $('#id_latitude').val(data.latitude);
    $('#id_longitude').val(data.longitude);

    $("#id_notes").val(
      "INSTRUCTORS: " + data.instructors.join(", ") + "\n\n" +
      "HELPERS: " + data.helpers.join(", ")
    );
  });
}

function update_from_url(url, action) {
  return $.get("/workshops/events/import/", {'url': url}, function(data) {
    $("#event_update_url").removeClass('is-invalid');
    $("#url_help").removeClass('invalid-feedback');
    $('#update_url_modal').modal('hide');
    $('#error_message').addClass('d-none');

    switch (action) {
      case 'overwrite':
        $("#id_slug").val(data.slug);
        $("#id_start").val(data.start);
        $("#id_end").val(data.end);
        $("#id_reg_key").val(data.reg_key);
        $("#id_url").val(url);

        // Select2 doesn't support programmatical search
        // so we're not going to fill the language for now

        $("#id_contact").val(data.contact);
        $('#id_venue').val(data.venue);
        $('#id_address').val(data.address);
        $('#id_country').val(data.country);
        $('#id_latitude').val(data.latitude);
        $('#id_longitude').val(data.longitude);
        $("#id_notes").val(
          "INSTRUCTORS: " + data.instructors.join(", ") + "\n\n" +
          "HELPERS: " + data.helpers.join(", ")
        );
        break;

      case 'skip':
      default:
        if ($("#id_slug").val() == "") {
          $("#id_slug").val(data.slug);
        }
        if ($("#id_start").val() == "") {
          $("#id_start").val(data.start);
        }
        if ($("#id_end").val() == "") {
          $("#id_end").val(data.end);
        }
        if ($("#id_reg_key").val() == "") {
          $("#id_reg_key").val(data.reg_key);
        }
        if ($("#id_url").val() == "") {
          $("#id_url").val(url);
        }
        if ($("#id_language").val() == "") {
          // Select2 doesn't support programmatical search
          // so we're not going to fill the language for now
        }
        if ($("#id_contact").val() == "") {
          $("#id_contact").val(data.contact);
        }
        if ($("#id_venue").val() == "") {
          $("#id_venue").val(data.venue);
        }
        if ($("#id_address").val() == "") {
          $("#id_address").val(data.address);
        }
        if ($("#id_country").val() == "") {
          $("#id_country").val(data.country);
        }
        if ($("#id_latitude").val() == "") {
          $("#id_latitude").val(data.latitude);
        }
        if ($("#id_longitude").val() == "") {
          $("#id_longitude").val(data.longitude);
        }
        // append notes
        var today = new Date();
        var today_str = "\n\n---------\nUPDATE " + today.yyyymmdd() + ":\n";
        $("#id_notes").val(
          $("#id_notes").val() + today_str +
          "INSTRUCTORS: " + data.instructors.join(", ") + "\n\n" +
          "HELPERS: " + data.helpers.join(", ")
        );

        break;
    }
  })
}

$(function() {
  $('#import_url_form').submit(function(e) {
    e.preventDefault();

    // indicate loading data
    var btn = $(this).find('button[type=submit]');
    btn.attr('disabled', true);

    // load data from URL
    import_from_url(
      $(this).find(':input[name=url]').val()
    )
    .fail(function(data) {
      // something went wrong, let's indicate it
      $("#event_import_url").addClass('is-invalid');
      $("#url_help").addClass('invalid-feedback');
      $('#error_message').text(data.responseText);
      $('#error_message').removeClass('d-none');
    })
    .always(function(data) {
      // let's always reenable the form's submit when the request finishes
      btn.attr('disabled', false);
    });
  });

  $('#update_url_form').submit(function(e) {
    e.preventDefault();

    // indicate loading data
    var btn = $(this).find('button[type=submit]');
    btn.attr('disabled', true);

    // load data from URL
    update_from_url(
      $(this).find(':input[name=url]').val(),
      $(this).find(':input[type=radio]:checked').val()
    )
    .fail(function(data) {
      // something went wrong, let's indicate it
      $("#event_update_url").addClass('is-invalid');
      $("#url_help").addClass('invalid-feedback');
      $('#error_message').text(data.responseText);
      $('#error_message').removeClass('d-none');
    })
    .always(function(data) {
      // let's always reenable the form's submit when the request finishes
      btn.attr('disabled', false);
    });
  });
});
