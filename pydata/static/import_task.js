function import_task(url) {
  return $.get("/workshops/tasks/import/", {'url': url}, function(data) {
    $("#task_url").parent().removeClass('has-error');
    $('#import_task_modal').modal('hide');
    $('#error_message').addClass('hidden');

    var elem = $("#id_task-person_0");
    // select the first results of a search
    elem.on("autocompleteresponse", function(event, ui) {
      ui.item = ui.content[0];
      $(this).data('ui-djselectable')._trigger('select', null, ui);
    });
    elem.djselectable("search", data.person);
    elem.on("autocompleteresponse", null);
    elem.djselectable('close');

    $("#id_task-role").val(data.role)
    $("#id_task-title").val(data.title);
    $("#id_task-url").val(url);
  });
}

$('#import_task_button').click(function() {
  $('#import_task_modal').modal();
});

$('#import_task_form').submit(function(e) {
  e.preventDefault();

  // indicate loading data
  var btn = $(this).find('button[type=submit]');
  btn.attr('disabled', true);

  // load data from URL
  import_task(
    $(this).find(':input[name=url]').val()
  )
  .fail(function(data) {
    // something went wrong, let's indicate it
    $("#task_url").parent().addClass('has-error');
    $('#task_error_message').text(data.responseText);
    $('#task_error_message').removeClass('hidden');
  })
  .always(function(data) {
    // let's always reenable the form's submit when the request finishes
    btn.attr('disabled', false);
  });
});
