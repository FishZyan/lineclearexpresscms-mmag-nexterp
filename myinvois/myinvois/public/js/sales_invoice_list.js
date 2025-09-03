// make a copy of ancestor to avoid overwriting
const myinvois_sales_invoice_list = frappe.listview_settings['Sales Invoice'].onload

frappe.listview_settings['Sales Invoice'] = {
    onload: function(listview) {

        if (myinvois_sales_invoice_list) {
            myinvois_sales_invoice_list(listview)
        }

        /*  
            Submit E-invoices
        */
        listview.page.add_action_item(__('Submit E-invoices'), function() {
            // Get the selected documents
            let selected_docs = listview.get_checked_items();

            // Check if any documents are selected
            if (selected_docs.length === 0) {
                frappe.msgprint(__('Please select at least one document.'));
                return;
            }
            frappe.msgprint(__('Sending E-invoice...'));
            // Call the server-side method
            frappe.call({
                method: 'myinvois.myinvois.bulk_submit.send_lhdn_invois', // Correct method path
                args: {
                    invoices: selected_docs.map(doc => doc.name) // Pass selected invoice names
                },
                callback: function(response) {
                    console.log("Test", response)
                    if (response.message && response.message.status === "queued") {
                        let job_id = response.message.job_id;
                        // check_job_status(job_id, selected_docs.map(doc => doc.name), listview);
                    } else {  
                        frappe.msgprint(__('Failed to start process.'));
                    }
                },
                error: function(error) {
                    frappe.msgprint(__('An error occurred: {0}', [error.message]));
                }
            });
        });
        
        function check_job_status(job_id, invoices, listview) {
            const total = invoices.length;
            let completed = 0;
            let interval = setInterval(function() {
                frappe.call({
                    method: "myinvois.myinvois.bulk_submit.check_invoice_job_status",
                    args: { job_id: job_id, invoices: invoices},
                    callback: function(response) {
                        console.log(response)
                        clearInterval(interval);
                        let data = JSON.parse(response.message);
                        let successInvoices = data.success;
                        let pendingInvoices = data.pending;
                        let failedInvoices = data.failed;
                        
                        completed = successInvoices.length + failedInvoices.length;

                        let message = "";
                        if (successInvoices.length > 0) {
                            message += "<div>Successful Invoices:</div>";
                            successInvoices.forEach(invoice => {
                                message += `
                                    <div style="display: flex; align-items: center;">
                                        <span style="height: 10px; width: 10px; background-color: green; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>
                                        <a href="/app/sales-invoice/${invoice}" target="_blank">${invoice}</a>
                                    </div>
                                `;
                            });
                        }
                        
                        if (pendingInvoices.length > 0) {
                            message += "<div>Pending Invoices:</div>";
                            pendingInvoices.forEach(invoice => {
                                message += `
                                    <div style="display: flex; align-items: center;">
                                        <span style="height: 10px; width: 10px; background-color: yellow; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>
                                        <a href="/app/sales-invoice/${invoice}" target="_blank">${invoice}</a>
                                    </div>
                                `;
                            });
                        }
                        
                        if (failedInvoices.length > 0) {
                            message += "<div>Failed Invoices:</div>";
                            failedInvoices.forEach(invoice => {
                                message += `
                                    <div style="display: flex; align-items: center;">
                                        <span style="height: 10px; width: 10px; background-color: red; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>
                                        <a href="/app/sales-invoice/${invoice}" target="_blank">${invoice}</a>
                                    </div>
                                `;
                            });
                        }
                        frappe.msgprint(message);
                    }
                });
            }, 3000); // Poll every 2 seconds
        }
    }
};
