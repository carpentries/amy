jQuery(function () {
  $("#id_award-awarded").datepicker({
    format: "yyyy-mm-dd",
    todayHighlight: true,
  });
  $("#tabs").stickyTabs();

  let award_badge; // hold badge filter for award selection
  let content_type;
  let person = $("#id_communityrole-person").val();
  $("#id_communityrole-award").select2({
    ajax: {
      data: (params) => {
        const query = {
          badge: award_badge,
          person,
          // `field_id` is required on backend by django-select2 views
          field_id: $("#id_communityrole-award").data("field_id"),
          ...params,
        };
        return query;
      },
    },
  });
  $("#id_communityrole-generic_relation_pk").select2({
    ajax: {
      data: (params) => {
        const query = {
          content_type,
          // `field_id` is required on backend by django-select2 views
          field_id: $("#id_communityrole-generic_relation_pk").data("field_id"),
          ...params,
        };
        return query;
      },
    },
  });
  $("#id_communityrole-person").on("select2:select", (e) => {
    const data = e.params.data;
    person = data.id;
  });
  $("#id_communityrole-config").on("select2:select", (e) => {
    const data = e.params.data;
    $("#id_communityrole-award").prop("required", data.link_to_award);
    award_badge = data.award_badge_limit;
    $("#id_communityrole-membership").prop("required", data.link_to_membership);
    $("#id_communityrole-partnership").prop("required", data.link_to_partnership);
    $("#id_communityrole-url").prop("disabled", !data.additional_url);
    $("#id_communityrole-url").prop("required", data.additional_url);
    if (!data.additional_url) {
      $("#id_communityrole-url").val("");
    }
    content_type = data.generic_relation_content_type;
    $("#id_communityrole-generic_relation_content_type").val(content_type);
    if (!content_type) {
      $("#id_communityrole-generic_relation_pk").val(null).trigger("change");
    }
  });
});
