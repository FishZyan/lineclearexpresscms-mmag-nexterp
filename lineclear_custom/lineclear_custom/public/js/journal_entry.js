frappe.ui.form.on('Journal Entry', {    
    onload: (frm) => {
        // Set posting date if not already provided.
        if (!frm.doc.posting_date) {
            frm.set_value("posting_date", frappe.datetime.get_today());
        }
        if (!frm.is_new() && [0, 1].includes(frm.doc.docstatus)) create_download_button(frm);
    },

    refresh: (frm) => {
        // retrieve selected invoices from local storage
        const invoices = JSON.parse(localStorage.getItem("selected_invoices"))

        // clean up localStorage
        localStorage.removeItem("selected_invoices")

        // populate the selected invoices into the table
        if (invoices) {
            frappe.call({
                method:  "lineclear_custom.lineclear_custom.journal_entry_api.get_entries",
                args: { invoices: invoices },
                callback: (response) => {
                    if (response.message) {
                        const entries  = response.message

                        for(let i = entries.length-1; i>=0; i--) {
                            frm.add_child("custom_accounting_entires", {
                                reference_type: entries[i].reference_type,
                                reference: entries[i].reference_name
                            })
                        }

                        // Refresh the child table to display the new rows
                        frm.refresh_field("custom_accounting_entires");
                    }

                    // refresh the table to display the new rows
                    frm.refresh_field("accounts")
                }
            })
        }

        if (!frm.is_new() && [0, 1].includes(frm.doc.docstatus)) create_download_button(frm);
    },

    voucher_type: (frm) => {
        update_naming_series(frm)
    },
    accounting_type: (frm) => {
        update_naming_series(frm)
    }
});



function update_naming_series(frm) {
    accounting_type = frm.doc.accounting_type
    voucher_type = frm.doc.voucher_type

    if (voucher_type == 'Credit Note') {
        if (accounting_type == 'Accounts Receivable') {
            frm.set_value('naming_series','LineClear CN.#####');
        } else if (accounting_type == 'Accounts Payable') {
            frm.set_value('naming_series','PR-.######');
        }
    } else if (voucher_type == 'Debit Note') {
        if (accounting_type == 'Accounts Receivable') {
            frm.set_value('naming_series','LineClear DN-.#####');
        } else if (accounting_type == 'Accounts Payable') {
            frm.set_value('naming_series','DN-.######');
        }
    } else if (voucher_type == 'Journal Entry') {
        frm.set_value('naming_series','JV-.#####');
    }
    frm.refresh_field('naming_series');
}


function create_download_button(frm) {
    if (
        frm.doc.accounting_type === 'Accounts Receivable' && 
        ['Credit Note', 'Debit Note'].includes(frm.doc.voucher_type)
    )
        // export action buttons: Debit Notes and Credit Notes
        frm.add_custom_button("Notes", () => { 
            const url = `/api/method/lineclear_custom.lineclear_custom.journal_entry_api.download_note?doc_no=${frm.doc.name}`;
            window.open(url);
        }, __("Actions"));

    if ( ['Journal Entry', 'Bank Entry', 'Cash Entry'].includes(frm.doc.voucher_type) )
        // export action buttons: Journal Entry, Bank Entry, Cash Entry
        frm.add_custom_button("Entry", () => { 
            const url = `/api/method/lineclear_custom.lineclear_custom.journal_entry_api.download_entry?doc_no=${frm.doc.name}`;
            window.open(url);
        }, __("Actions"));

    if (frm.doc.custom_lhdn_status != "InProgress" && frm.doc.custom_lhdn_status != "Valid") {
        if (frm.doc.voucher_type == "Debit Note" || frm.doc.voucher_type == "Credit Note") {
            frm.add_custom_button("Update LHDN Enable Control", () => { 
                frappe.call({
                    method: "lineclear_custom.lineclear_custom.update_lhdn_enable_control.journal_entry_set_lhdn_control",
                    args: {
                        doc_no: frm.doc.name
                    }
                });
            }, __("Actions"));
        }
    }
}