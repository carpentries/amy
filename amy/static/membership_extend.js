window.addEventListener("load", (e) => {
    const extension_input = document.querySelector("#id_extension");
    const agreement_end_input = document.querySelector("#id_agreement_end");
    const new_agreement_end_input = document.querySelector("#id_new_agreement_end");
    const agreement_end_date = new Date(agreement_end_input.value);

    const one_day = 1000 * 60 * 60 * 24;

    if (!!extension_input) {
        let new_agreement_end_date = new Date();
        extension_input.addEventListener("change", ({target}) => {
            new_agreement_end_date.setTime(agreement_end_date.getTime() + target.value * one_day);
            new_agreement_end_input.value = new_agreement_end_date.yyyymmdd();
        });
    }
});
