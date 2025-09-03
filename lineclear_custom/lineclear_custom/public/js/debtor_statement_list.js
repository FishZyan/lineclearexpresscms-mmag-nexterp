function extend_listview_event(doctype, event, callback) {
    if (!frappe.listview_settings[doctype]) frappe.listview_settings[doctype] = {};

    const old_event = frappe.listview_settings[doctype][event];
    frappe.listview_settings[doctype][event] = (listview) => {
        if (old_event) old_event(listview);
        callback(listview);
    };
}

extend_listview_event("Debtor Statement", "refresh", (listview) => {
    $(document).ready(() => {
        $('span[data-filter="custom_status,=,Cleared"]').each(function() {
            $(this).removeClass('gray').addClass('green');
        });
        $('span[data-filter="custom_status,=,Overdue"]').each(function() {
            $(this).removeClass('gray').addClass('red');
        });
    })
});