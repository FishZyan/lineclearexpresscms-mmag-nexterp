frappe.ui.form.on('Bank Clearance', {
    onload: (frm) => {
        frm.custom_buttons_added = false; 
    },
    refresh: (frm) => {
        frm.custom_buttons_added = false;
        try_add_button(frm);
    },
    account: try_add_button,
    bank_account: try_add_button,
    from_date: try_add_button,
    to_date: try_add_button
})


function try_add_button(frm) {
    if (frm.doc.account && frm.doc.bank_account && frm.doc.from_date && frm.doc.to_date) {
        add_custom_button(frm);
    }
}


function add_custom_button(frm) {
    // Avoid adding duplicate buttons
    if (!frm.custom_buttons_added) {
        frm.add_custom_button("Sync Date", () => { 
            frappe.call({
                method: 'lineclear_custom.lineclear_custom.bank_clearance_api.update_clearance_date',
                args: {
                    bank_account: frm.doc.bank_account,
                    from_date: frm.doc.from_date,
                    to_date: frm.doc.to_date
                },
                callback: (response) => {
                    const result = response.message;
                    let message = `Synced: ${result.synced}\nFailed: ${result.failed}`;
                    
                    if (result.file_url) window.open(result.file_url);

                    frappe.msgprint({
                        title: "Clearance Update Summary",
                        message: message.replace(/\n/g, "<br>"),
                        indicator: result.failed > 0 ? 'red' : 'green'
                    });
                }
            });
        }, __("Action"));
        frm.custom_buttons_added = true;
    }
}


