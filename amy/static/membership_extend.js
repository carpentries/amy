window.addEventListener("load", (e) => {
    const extension_input = document.querySelector("#id_extension");
    const agreement_end_input = document.querySelector("#id_agreement_end");
    const new_agreement_end_input = document.querySelector("#id_new_agreement_end");
    const agreement_end_date = new Date(agreement_end_input.value);

    const one_day = 1000 * 60 * 60 * 24;

    if (!!new_agreement_end_input) {
        $(new_agreement_end_input).on("changeDate", (event) => {
            const new_agreement_end_date = new Date(event.target.value);
            extension_input.value = (new_agreement_end_date - agreement_end_date) / one_day;
        });
    }
});
