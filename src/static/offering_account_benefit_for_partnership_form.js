jQuery(function () {
  function handleDateFields(record) {
    const id_start_date = $("#id_start_date");
    const id_end_date = $("#id_end_date");

    if (record.agreement_start) {
      id_start_date.datepicker("update", new Date(record.agreement_start));
      id_start_date.attr("disabled", "disabled");
    } else {
      // id_start_date.datepicker("update", "");
      id_start_date.removeAttr("disabled");
    }
    if (record.agreement_end) {
      id_end_date.datepicker("update", new Date(record.agreement_end));
      id_end_date.attr("disabled", "disabled");
    } else {
      // id_end_date.datepicker("update", "");
      id_end_date.removeAttr("disabled");
    }
  }
  function handleRegistrationCode(record) {
    const id_registration_code = $("#id_registration_code");
    if (record.id) {
      id_registration_code.attr("disabled", "disabled");
      id_registration_code.removeAttr("required");
    } else {
      id_registration_code.removeAttr("disabled");
      id_registration_code.attr("required", "required");
    }
  }

  $("#id_partnership").on("change.select2", (e) => {
    const record = $(e.target).select2("data")[0];
    handleDateFields(record);
    handleRegistrationCode(record);
    e.preventDefault();
  });

  // Clear selected partnership if account changes
  $("#id_account").on("change.select2", (e) => {
    $("#id_partnership").val(null).trigger("change");
  });
});
