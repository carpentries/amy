Date.prototype.yyyymmdd = function() {
    // adapted from http://stackoverflow.com/a/3067896
    var yyyy = this.getFullYear();
    var mm_aux = this.getMonth() + 1;  // getMonth() is zero-based
    var mm = mm_aux < 10 ? "0" + mm_aux : mm_aux;
    var dd_aux = this.getDate();
    var dd  = dd_aux < 10 ? "0" + dd_aux : dd_aux;
    return "".concat(yyyy, "-", mm, "-", dd);
};
