frappe.ui.form.on('Sales Invoice', {
    onload(frm) {
        if (!frm.is_new() && frm.doc.docstatus in [0, 1]) create_download_button(frm);
	},
	refresh(frm) {
        if (!frm.is_new() && frm.doc.docstatus in [0, 1]) create_download_button(frm);
	},
});


function create_download_button(frm) {
    // export action buttons: Sales Invoice
    frm.add_custom_button("Invoices", () => { 
        const url = `/api/method/lineclear_custom.lineclear_custom.sales_invoice_api.download_invoice?doc_no=${frm.doc.name}`;
        window.open(url);
    }, __("Actions"));
}