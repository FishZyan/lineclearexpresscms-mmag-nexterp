frappe.listview_settings['LHDN Log'] = {
    onload: (listview) => {
        let button = listview.page.add_button('Get LHDN Log', () => {
            frappe.call({
                method: 'lineclear_custom.lineclear_custom.update_log.get_all_submission', // your backend method
            });
        });
        button.css({ "background-color": "black", "color" : "white" })
    }
};