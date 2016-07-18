function import_sponsor(url) {
  return $.get("/workshops/sponsors/import/", {'url': url}, function(data) {
    $("#sponsor_url").parent().removeClass('has-error');
    $('#import_sponsor_modal').modal('hide');
    $('#error_message').addClass('hidden');

    var elem = $("#id_sponsor-organization_0");
    // select the first results of a search
    elem.on("autocompleteresponse", function(event, ui) {
      ui.item = ui.content[0];
      $(this).data('ui-djselectable')._trigger('select', null, ui);
    });
    elem.djselectable('search', data.organization);
    elem.on("autocompleteresponse", null);
    elem.djselectable('close');
  });
}

$('#import_sponsor_button').click(function() {
  $('#import_sponsor_modal').modal();
});

$('#import_sponsor_form').submit(function(e) {
  e.preventDefault();

  // indicate loading data
  var btn = $(this).find('button[type=submit]');
  btn.attr('disabled', true);

  // load data from URL
  import_sponsor(
    $(this).find(':input[name=url]').val()
  )
  .fail(function(data) {
    // something went wrong, let's indicate it
    $("#sponsor_url").parent().addClass('has-error');
    $('#sponsor_error_message').text(data.responseText);
    $('#sponsor_error_message').removeClass('hidden');
  })
  .always(function(data) {
    // let's always reenable the form's submit when the request finishes
    btn.attr('disabled', false);
  });
});
