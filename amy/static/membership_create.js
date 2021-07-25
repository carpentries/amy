jQuery(function () {
  $("#id_main_organization").on("change.select2", (e) => {
    // additional data is sent from the backend and it's stored in
    // select2 `data` parameter
    const fullname = $(e.target).select2("data")[0].fullname;
    const id_name = $("#id_name");

    // only write the new name if "name" field is empty
    if (!!fullname && !!id_name && !id_name.val()) {
      id_name.val(fullname);
    }
  });

  // prepopulate some fields based on selected variant
  const variantChange = (e) => {
    const parameters = {
      bronze: {
        it_seats_public: 0,
        workshops: 2,
      },
      silver: {
        it_seats_public: 6,
        workshops: 4,
      },
      gold: {
        it_seats_public: 15,
        workshops: 6,
      },
    };

    const publicInstructorTrainingSeats = $(
      "#id_public_instructor_training_seats"
    );
    const workshopsWithoutAdminFee = $(
      "#id_workshops_without_admin_fee_per_agreement"
    );
    const changedFieldValues = $("#standard_packages_prepopulation_warning");

    const variant = e ? $(e.target) : $("#id_variant");

    if (variant.val() in parameters) {
      // set values from parameters
      publicInstructorTrainingSeats.val(
        parameters[variant.val()].it_seats_public
      );
      workshopsWithoutAdminFee.val(parameters[variant.val()].workshops);

      // set visual indication
      publicInstructorTrainingSeats.addClass("border-warning");
      workshopsWithoutAdminFee.addClass("border-warning");
      changedFieldValues.removeClass("d-none");
    } else {
      // remove visual indication (if any set)
      publicInstructorTrainingSeats.removeClass("border-warning");
      workshopsWithoutAdminFee.removeClass("border-warning");
      changedFieldValues.addClass("d-none");
    }
  };
  variantChange(); // on load
  $("#id_variant").on("change", (e) => {
    variantChange(e);
  });
});
