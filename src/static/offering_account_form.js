jQuery(function () {
  let contentType = null;

  function accountTypeValidation(value) {
    if (["individual", "organisation", "consortium", "partnership"].includes(value)) {
      contentType = value;
    } else {
      contentType = null;
    }
  }

  accountTypeValidation($("#id_account_type").val());
  $("#id_account_type").on("change", (e) => {
    const currentValue = $(e.currentTarget).val();
    accountTypeValidation(currentValue);
  });

  $("#id_generic_relation_pk").djangoSelect2({
    placeholder: "Please select specific item",
    ajax: {
      data: function (params) {
        const query = {
          content_type_name: contentType,
          // `field_id` is required on backend by django-select2 views
          field_id: $("#id_generic_relation_pk").data("field_id"),
          ...params,
        };
        return query;
      },
    },
  });
});
