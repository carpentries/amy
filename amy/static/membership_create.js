jQuery(function() {
    $('#id_main_organization').on('change.select2', (e) => {
        // additional data is sent from the backend and it's stored in
        // select2 `data` parameter
        const fullname = $(e.target).select2("data")[0].fullname;
        const id_name = $("#id_name");

        // only write the new name if "name" field is empty
        if (!!fullname && !!id_name && !id_name.val()) {
            id_name.val(fullname);
        }
    });
});
