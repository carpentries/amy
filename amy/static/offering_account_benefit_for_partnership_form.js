jQuery(function () {
  $("#id_partnership").on("change.select2", (e) => {
    const record = $(e.target).select2("data")[0];
    const id_start_date = $("#id_start_date");
    const id_end_date = $("#id_end_date");

    if (record.agreement_start) {
      id_start_date.datepicker("update", new Date(record.agreement_start));
    }
    if (record.agreement_end) {
      id_end_date.datepicker("update", new Date(record.agreement_end));
    }

    e.preventDefault();
  });
});
