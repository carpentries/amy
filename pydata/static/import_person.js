function import_from_url(url) {
  return $.get("/workshops/person/import/", {'url': url}, function(data) {
    $("#event_import_url").parent().removeClass('has-error');
    $('#import_url_modal').modal('hide');
    $('#error_message').addClass('hidden');

    $("#id_personal").val(data.personal);
    $("#id_family").val(data.family);
    $("#id_email").val(data.email);
    $("#id_url").val(url);
  });
}

$('#import_url_button').click(function() {
  $('#import_url_modal').modal();
});
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
    $("#event_import_url").parent().addClass('has-error');
    $('#error_message').text(data.responseText);
    $('#error_message').removeClass('hidden');
  })
  .always(function(data) {
    // let's always reenable the form's submit when the request finishes
    btn.attr('disabled', false);
  });
});
