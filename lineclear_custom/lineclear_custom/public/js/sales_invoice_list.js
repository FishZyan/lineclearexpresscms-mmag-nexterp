// make a copy of ancestor to avoid overwriting
const lineclear_custom_sales_invoice_list = frappe.listview_settings['Sales Invoice'].onload

frappe.listview_settings['Sales Invoice'] = {
    onload: (listview) => {

        if (lineclear_custom_sales_invoice_list) {
            lineclear_custom_sales_invoice_list(listview)
        }
        
        /*
            direct the selected invoices to Journal Entry page
        */
        listview.page.add_action_item('Create Journal Entry', () => {
            // Get the selected documents
            let selected_docs = listview.get_checked_items();

            // Check if any documents are selected
            if (selected_docs.length === 0) {
                frappe.msgprint(__('Please select at least one document.'));
                return;
            }
            
            const invoices = JSON.stringify(selected_docs.map(doc => doc.name))
            localStorage.setItem("selected_invoices", invoices)
            frappe.open_in_new_tab = true
            frappe.set_route("List", "Journal Entry");
        });
    }
}