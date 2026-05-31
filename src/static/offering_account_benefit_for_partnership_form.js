jQuery(function () {
  function handleDateFields(record) {
    const startEl = document.getElementById("id_start_date");
    const endEl = document.getElementById("id_end_date");

    if (record.agreement_start && startEl) {
      const dp = Datepicker.getInstance(startEl);
      if (dp) dp.setDate(new Date(record.agreement_start));
      startEl.setAttribute("disabled", "disabled");
    } else if (startEl) {
      startEl.removeAttribute("disabled");
    }
    if (record.agreement_end && endEl) {
      const dp = Datepicker.getInstance(endEl);
      if (dp) dp.setDate(new Date(record.agreement_end));
      endEl.setAttribute("disabled", "disabled");
    } else if (endEl) {
      endEl.removeAttribute("disabled");
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
  function handleDiscount(record) {
    const id_discount = $("#id_discount");
    if (record.id) {
      id_discount.attr("disabled", "disabled");
    } else {
      id_discount.removeAttr("disabled");
    }
  }

  $("#id_partnership").on("change.select2", (e) => {
    const record = $(e.target).select2("data")[0];
    handleDateFields(record);
    handleRegistrationCode(record);
    handleDiscount(record);
    e.preventDefault();
  });

  // Clear selected partnership if account changes
  $("#id_account").on("change.select2", (e) => {
    $("#id_partnership").val(null).trigger("change");
  });
});
