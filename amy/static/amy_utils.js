/* A file with functionality that is enabled on each page. */

function bulk_email() {
    /*
    Look at all selected <input type="checkbox" email="example@example.org">
    tags on the webpage and join email addresses using comma as a separator
    (i.e. "first@example.org,second@example.org").

    If there is no selected checkbox with email address, display alert. If
    any of the selected email addresses is blank, display alert. Otherwise,
    open email client and pass those addresses.
    */
    var emails, href, blank_email_selected;
    emails = $('input[type=checkbox][email]:checked')
             .map(function () { return $(this).attr("email"); });
    blank_email_selected = emails.is(function() { return this == ""; });
    if (blank_email_selected) {
        alert("We don't know email address of some of the selected persons. First, unselect them.");
    } else if (emails.length == 0) {
        alert("Select at least one person.");
    } else {
        href = "mailto:?bcc=" + emails.toArray().join(",");
        window.location.href = href;
    }
}

/* See http://learn.jquery.com/plugins/basic-plugin-creation/ */
$.fn.updateSelectAllCheckbox = function () {
  return this.each(function() {
    /* At this moment, `this` is "select all" checkbox. */

    var checkboxes = $(this).closest('form').find(':checkbox[respond-to-select-all-checkbox]');
    var checked = checkboxes.filter(':checked');
    if (checked.length == 0) { // all checkboxes are unchecked
      $(this).prop('checked', false);
      $(this).prop('indeterminate', false);
    } else if (checked.length == checkboxes.length) { // all checkboxes are checked
      $(this).prop('checked', true);
      $(this).prop('indeterminate', false);
    } else { // some checkboxes are checked and some are unchecked
      $(this).prop('checked', false);
      $(this).prop('indeterminate', true);
    }
    return this;
  });
};

/* See http://learn.jquery.com/plugins/basic-plugin-creation/ */
$.fn.updateIdsInHref = function () {
  // checked checkboxes
  var checked = $(this).closest('form').find(':checkbox[respond-to-select-all-checkbox]').filter(':checked');
  // current URL
  var href = $(this).attr('href');
  // make URI.js object out of the URL
  var uri = URI(href);

  // extend query params
  uri = uri.query(function(data) {
    var ids = [];
    checked.map(function() {
      ids.push($(this).val());
    });
    data.ids = ids.join(",");
  });

  // update URL with new query parameters
  $(this).attr('href', uri.toString());

  return this;
}

function updateTrainingProgressForm() {
  /* At this moment, `this` should be <select> tag of "Type" field. */
  var type = $(this).find(":selected").text();
  var training_div = $(this).closest('form').find('#div_id_event');
  var url_div = $(this).closest('form').find('#div_id_url');

  if (type == 'Training') {
    training_div.show();
  } else {
    training_div.hide();
    var event = training_div.find('#id_event');
    if (event.val() != undefined) {
      event.val(null).trigger('change');
    }
  }

  if (type == 'SWC Homework' || type == 'DC Homework' || type == 'LC Homework') {
    url_div.show();
  } else {
    url_div.hide();
    url_div.find('#id_url').val("");
  }
}

$(document).ready(function() {
  /* Enable Bootstrap Tooltips by default. */
  $('[data-toggle="tooltip"]').tooltip();

  /*
  Enable Bootstrap Popovers by default.

  Example usage:

  <span class="btn btn-primary"
        data-toggle="popover"
        data-content="Content of a popup">Hover, focus or click me!</span>
  */
  $('[data-toggle="popover"]').popover({placement: "auto"});

  /* Some pages may have checkboxes in tables selected by default; in those
  cases, we should update URL in a[amy-download-selected] when the page
  loads. */
  $('a[amy-download-selected]').each(function(i, obj) {
    $(this).updateIdsInHref();
  });

  /*
  Add <input type="checkbox" select-all-checkbox> to your form to let user
  select/unselect all checkboxes with respond-to-select-all-checkbox attribute
  in the form with single click.

  Based on http://stackoverflow.com/a/2228401.
  */
  /* Select/unselect all checkboxes when users clicks on "select all" checkbox. */
  $('[select-all-checkbox]').change(function() {
    var checkboxes = $(this).closest('form').find(':checkbox[respond-to-select-all-checkbox]');
    if($(this).is(':checked')) {
        checkboxes.prop('checked', true);
    } else {
        checkboxes.prop('checked', false);
    }
    // below runs `updateIdsInHref` for all matching <a> (`.each` is required)
    $(this).closest('form').find('a[amy-download-selected]').each(function(i, obj) {
      $(this).updateIdsInHref();
    });
  });

  /* When a checkbox is clicked, update "select all" checkbox state to checked,
  unchecked or indeterminate (neither checked nor unchecked) depending
  on the state of all checkboxes. */
  $('[respond-to-select-all-checkbox]').change(function () {
    $(this).closest('form').find(':checkbox[select-all-checkbox]').updateSelectAllCheckbox();
    // below runs `updateIdsInHref` for all matching <a> (`.each` is required)
    $(this).closest('form').find('a[amy-download-selected]').each(function(i, obj) {
      $(this).updateIdsInHref();
    });
  });

  /* Set "select all" checkboxes to proper initial state. */
  $(':checkbox[select-all-checkbox]').updateSelectAllCheckbox();

  /*
  Add <a bulk-email-on-click class="btn btn-primary">Mail selected people</a>
  to your form to let the user write email to a group of selected people. You
  need to set up emails addresses on checkboxes:

      <input type="checkbox" email="example@example.org">

  Blank emails and checkboxes without email attribute will be ignored.
  */
  $('[bulk-email-on-click]').click(function () {
    bulk_email();
  });

  /*
  TrainingProgress forms: show/hide training and url fields, depending on
  selected TrainingProgress type.
  */

  var selectField = $('form.training-progress #id_requirement')
  selectField.change(updateTrainingProgressForm);
  updateTrainingProgressForm.call(selectField);

  /*
  When there is any autocomplete field with invalid value, prevent form
  submission. Focus on the invalid field when user tries to submit the form.
  */

  $('form').submit(function (event) {
    var invalidAutocompleteFields = $('.ui-autocomplete-input.ui-state-error');
    if (invalidAutocompleteFields.length > 0) {
      var firstInvalidField = invalidAutocompleteFields.first();
      firstInvalidField.focus();
      event.preventDefault();  // prevent submission
    }
  });

  /* Fix select2 widgets losing their focus. */
  $('select').on("select2:close", function () { $(this).focus(); });

  /* react on comment tab change: resize preview div */
  $('.comment-form a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    var target_pane = $(e.target).attr("href");
    var prev_target_pane = $(e.relatedTarget).attr("href");

    if (target_pane == "#preview") {
      if ($(target_pane).height() < $(prev_target_pane).height()) {
        $(target_pane).height($(prev_target_pane).height());
      }
    }
  })

  /* Additional messages for forms: they show up when a specific value is
     entered into the field */

  // check initial value for this proficient computing level
  if ($("#id_computing_levels_3").is(":checked")) {
    $("#computing_levels_warning").removeClass("d-none");
  } else {
    $("#computing_levels_warning").addClass("d-none");
  }

  $("#id_computing_levels_3").change(function() {
    // show warning if someone selects "Proficient"
    if($(this).is(':checked')) {
      $("#computing_levels_warning").removeClass("d-none");
    } else {
      $("#computing_levels_warning").addClass("d-none");
    }
  })

  // default cutoff time: 60 days
  var DEFAULT_WARNING_TIME = 1000 * 60 * 60 * 24 * 30 * 2;

  // check initial value for the preferred dates
  if ($("#id_preferred_dates").val()) {
    $("#id_preferred_dates").datepicker('update');

    // read current input value and today's date
    var value = $("#id_preferred_dates").datepicker('getDate');
    var today = new Date();
    var time_diff = value.getTime() - today.getTime();

    // 2 months
    if (time_diff < DEFAULT_WARNING_TIME) {
      $("#preferred_dates_warning").removeClass("d-none");
    } else {
      $("#preferred_dates_warning").addClass("d-none");
    }
  }

  $("#id_preferred_dates").on("changeDate input", function(e){
    // update datepicker with current input value
    $(this).datepicker('update');

    // read current input value and today's date
    var value = $(this).datepicker('getDate');
    var today = new Date();
    var time_diff = value.getTime() - today.getTime();

    // 2 months
    if (time_diff < DEFAULT_WARNING_TIME) {
      $("#preferred_dates_warning").removeClass("d-none");
    } else {
      $("#preferred_dates_warning").addClass("d-none");
    }
  })

  // load template by the slug when someone opens up the modal for editing template
  // before its sent
  $("#email_edit").on("show.bs.modal", function(e) {
    let btn = $(e.relatedTarget);
    let template_slug = btn.data("templateSlug");
    let modal = $(this);

    $.get("/api/v1/emailtemplates/" + template_slug, {}, function(data) {
      modal.find(".modal-body #email_slug").text(data.slug);
      modal.find(".modal-body #email_subject").text(data.subject);

      // form below
      modal.find(".modal-body #id_slug").val(data.slug);
      modal.find(".modal-body #id_subject").val(data.subject);
      modal.find(".modal-body #id_to_header").val(data.to_header);
      modal.find(".modal-body #id_from_header").val(data.from_header);
      modal.find(".modal-body #id_cc_header").val(data.cc_header);
      modal.find(".modal-body #id_bcc_header").val(data.bcc_header);
      modal.find(".modal-body #id_reply_to_header").val(data.reply_to_header);
      modal.find(".modal-body #id_body_template").text(data.body_template);

      // force reload of markdownx
      modal.find(".modal-body #id_body_template").trigger("input");
    });
  })

  $("#email_edit").on("hide.bs.modal", function(e) {
    let modal = $(this);

    modal.find(".modal-body #id_subject").val("");
    modal.find(".modal-body #id_template").text("");
  })

  // when "TTT" tag is selected on new event form, automatically select
  // "TTT Open applications" checkbox
  $("#id_tags").on("change", function(event) {
    const checkbox = $("#id_open_TTT_applications");
    $.each(event.target.selectedOptions, function(idx, val) {
      if (val.text == "TTT") {
        checkbox.prop("checked", true);
      }
    })
  })
  // on page load, select the checkbox if "TTT" option was preselected
  $("#id_tags").find(":selected").each(function(idx, val) {
    const checkbox = $("#id_open_TTT_applications");
    if (val.text == "TTT") {
      checkbox.prop("checked", true);
    }
  })

  // warning for membership agreement duration != 1 year
  const agreement_duration_warning = $("#agreement_duration_warning");
  const agreement_start = $("#id_agreement_start");
  const agreement_end = $("#id_agreement_end");
  const duration_warning = function(start_element, end_element, warning_element) {
    const next_year = start_element.datepicker("getDate");
    const end_date = end_element.datepicker("getDate");
    next_year.setFullYear(next_year.getFullYear() + 1);

    if (next_year.getTime() != end_date.getTime()) {
      warning_element.removeClass("d-none");
    } else {
      warning_element.addClass("d-none");
    }
  }
  if (!!agreement_start.val() && !!agreement_end.val()) {
    duration_warning(agreement_start, agreement_end, agreement_duration_warning);
  }
  agreement_start.on("changeDate input", function(e) {
    // update datepicker with current input value
    $(this).datepicker("update");
    duration_warning(agreement_start, agreement_end, agreement_duration_warning);
  });
  agreement_end.on("changeDate input", function(e) {
    // update datepicker with current input value
    $(this).datepicker("update");
    duration_warning(agreement_start, agreement_end, agreement_duration_warning);
  });

  // assignment form autosubmit
  $("#id_assigned_to").on("change", function(e) {
    e.preventDefault();
    $("#assignment-form").trigger("submit");
  })

  // formset
  $("#formset").formset({
    animateForms: false,
    reorderMode: 'dom',
  })
 });
