// make a copy of ancestor to avoid overwriting
const lineclear_custom_journal_entry_list = frappe.listview_settings['Journal Entry'].onload

frappe.listview_settings['Journal Entry'] = {
    onload: (listview) => {

        if (lineclear_custom_journal_entry_list) {
            lineclear_custom_journal_entry_list(listview)
        }

        // button opens a journal entry with debit note as entry type
        let btn_debit_note = listview.page.add_button('+ Add Debit Note', () => {
            frappe.new_doc(
                doctype = 'Journal Entry', 
                {   
                    voucher_type: "Debit Note",
                    // company: frappe.defaults.get_default("company")
                }
            );
        });

        // button opens a journal entry with credit note as entry type
        let btn_credit_note = listview.page.add_button('+ Add Credit Note', () => {
            frappe.new_doc(
                doctype = 'Journal Entry', 
                {   
                    voucher_type: "Credit Note",
                    // company: frappe.defaults.get_default("company")
                }
            );
        });

        // inline css styling for the button
        btn_debit_note.css({ "background-color": "black", "color" : "white" })
        btn_credit_note.css({ "background-color": "black", "color" : "white" })
    }
};