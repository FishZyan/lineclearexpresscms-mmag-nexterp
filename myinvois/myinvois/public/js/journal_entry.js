// frappe.ui.form.on('Journal Entry', {
//     onload: function (frm) {
//         if (frm.is_new()) { // Check if the document is new
//             frm.set_value('custom_created_by', frappe.session.user);
//         }
//     },
//     refresh: function(frm){
//         update_debtor_code(frm);
//         // setTimeout(() => {
//         //     $("div[data-fieldname='accounts']").css({
//         //         "max-height": "100px",
//         //         "overflow-y": "auto"
//         //     });
//         // }, 1000);

//         /* 
//             E-invoice Submit
//         */
//         if (frm.doc.docstatus == "1"){
// 		    if (frm.doc.custom_lhdn_status != "Valid"){
//                 frm.add_custom_button(__("Send invoice"), function() {
//                     frm.call({
//                         method:"lineclear_custom.lineclear_custom.journal_entry_invoice.lhdn_Background",
//                         args: {
//                             "doc_number": frm.doc.name,
//                         },
//                         callback: function(response) {
//                             if (response.message) {  
//                                 frm.reload_doc();
//                             }
//                             frm.reload_doc();
//                         }
//                     });
//                     frm.reload_doc();
//                 }, __("EInvoice"));
//             }
//         }
//         if (!frm.doc.custom_lhdn_status || frm.doc.custom_lhdn_status === "Valid") {
//             frm.set_df_property("refresh_status", 'hidden', 1);
//         } else {
//             frm.set_df_property("refresh_status", 'hidden', 0);
//         }
//     },
//     refresh_status:function(frm){
//         frm.call({
//             method:"lineclear_custom.lineclear_custom.journal_entry_invoice.refresh_doc_status",
//             args: {
//                 "uuid": frm.doc.custom_uuid,
//                 "doc_number":frm.doc.name
//             },
//             callback: function(response) {
//                 if (response.message) {  
//                     frm.reload_doc();
//                 }
//                 frm.reload_doc();
//             }
//         });
//         frm.reload_doc();
//     },
//     custom_lhdn_status: function(frm) {
//         if (!frm.doc.custom_lhdn_status || frm.doc.custom_lhdn_status === "Valid") {
//             frm.set_df_property("refresh_status", 'hidden', 1);
//         } else {
//             frm.set_df_property("refresh_status", 'hidden', 0);
//         }
//     },
// 	customer: function(frm){
// 	    if (frm.doc.customer && frm.doc.from_template) {
// 	       update_customer(frm);
// 	    }
// 	    update_debtor_code(frm);
// 	},
// 	// voucher_type: function(frm){
// 	//     if(frm.doc.voucher_type == "Credit Note") {
// 	//         frm.set_value("from_template", "Credit Note");
// 	//     }
// 	//     else if (frm.doc.voucher_type == "Debit Note") {
// 	//         frm.set_value("from_template", "Debit Note");
// 	//     }
// 	// },
// 	net_total: function(frm){
// 	    if (frm.doc.from_template && frm.doc.net_total) {
// 	       update_customer(frm);
// 	    }
// 	    update_tax(frm);
// 	},
// 	sales_taxes_and_charges_template: function(frm){
// 	    let tax_account_name = "GST - LCESB";
// 	    frappe.call({
//             method: "frappe.client.get",
//             args: {
//                 doctype: "Sales Taxes and Charges Template",  // Specify the template doctype
//                 name: frm.doc.sales_taxes_and_charges_template  // The selected template name
//             },
//             callback: function(response) {
//                 if (response.message) {
//                     // If a valid response is returned
//                     let template = response.message;
                    
//                     // Apply the Sales Taxes and Charges Template to the form
//                     frm.doc.tax = [];  // Clear existing tax lines
                    
//                     // Assuming template contains a child table 'taxes' (adjust based on actual template structure)
//                     $.each(template.taxes, function(index, tax_row) {
//                         let new_row = frm.add_child('tax');  // Add a new row in the 'tax' table
//                         new_row.charge_type = tax_row.charge_type;  // Copy charge_type
//                         new_row.account_head = tax_row.account_head;  // Copy account_head
//                         new_row.rate = tax_row.rate;  // Copy rate
//                         new_row.tax_amount = tax_row.tax_amount;  // Copy tax_amount
//                         new_row.description = tax_row.description;
//                     });
//                     // Refresh the field to show the newly added rows in the table
//                     frm.refresh_field('tax');
//                 }
//                 if (frm.doc.sales_taxes_and_charges_template == "ESV-6 - LCESB" || frm.doc.sales_taxes_and_charges_template == "SV-0 - LCESB") {
//                     // frm.doc.accounts.splice(0, 1);
//                     let table = frm.doc.accounts;
            
//                     // Filter out rows where head_account is GST
//                     frm.doc.accounts = table.filter(row => row.account !== tax_account_name);
//                     frm.refresh_field('accounts');
//                 } else {
//                     let table = frm.doc.accounts;
            
//                     // Filter out rows where head_account is GST
//                     frm.doc.accounts = table.filter(row => row.account !== tax_account_name);
                    
//                     // Add Tax Row
//                     let row = frm.add_child('accounts');
//                     row.account = tax_account_name;
//                     frm.refresh_field('accounts');
//                 }
//                 update_tax(frm);
//             }
//         });
// 	}
// });

// frappe.ui.form.on('Journal Entry Account', {
// 	account: function(frm, cdt, cdn) {
//         update_customer(frm);
//         // update_account_property(frm, cdt, cdn);
//     },
//     party_type: function(frm) {
//         update_customer(frm);
//     },
//     credit_in_account_currency: function(frm, cdt, cdn){
//         let row = locals[cdt][cdn];
//         if(frm.doc.from_template == "Debit Note"){
//             if (row.party_type == "Customer"){
//                 frappe.model.set_value(cdt, cdn, 'credit_in_account_currency', '0');
//             }
//         } 
//         count_net_total(frm);
//     },
//     debit_in_account_currency: function(frm, cdt, cdn){
//         let row = locals[cdt][cdn];
//         count_net_total(frm);
//     }
// });

// frappe.ui.form.on("Sales Taxes and Charges", {
//     charge_type: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         if(row.charge_type == "On Net Total"){
//             frm.set_df_property('tax', 'read_only', 1, frm.docname, 'tax_amount', row.name);
//             frm.set_df_property('tax', 'read_only', 0, frm.docname, 'rate', row.name);
//             if(!row.rate){
//                 frappe.model.set_value(cdt, cdn, 'rate', '6');
//             }
//         }
//         else if(row.charge_type == "Actual"){
//             frm.set_df_property('tax', 'read_only', 0, frm.docname, 'tax_amount', row.name);
//             frm.set_df_property('tax', 'read_only', 1, frm.docname, 'rate', row.name);
//             frappe.model.set_value(cdt, cdn, 'rate', '0');
//         } else {
//             frm.set_df_property('tax', 'read_only', 0, frm.docname, 'tax_amount', row.name);
//             frm.set_df_property('tax', 'read_only', 0, frm.docname, 'rate', row.name);
//         }
//         update_tax(frm);
//         frappe.model.set_value(cdt, cdn, 'account_head', "GST - LCESB");
//         frappe.model.set_value(cdt, cdn, 'description', "Calculate Tax");
//     },
//     rate: function(frm, cdt, cdn){
//         let row = locals[cdt][cdn];
//         if(row.rate && frm.doc.net_total){
//             update_tax(frm);
//         } else {
//             frappe.model.set_value(cdt, cdn, 'tax_amount', '0');
//         }
//     },
//     tax_amount: function(frm, cdt, cdn){
//         let row = locals[cdt][cdn];
//         update_total(frm);
//     }
// });

// function update_account_property(frm, cdt, cdn){
//     let row = locals[cdt][cdn];
//     if(row.party_type){
//         frm.set_df_property('accounts', 'read_only', 0, frm.docname, 'custom_description', row.name);
//     } else {
//         frm.set_df_property('accounts', 'read_only', 1, frm.docname, 'custom_description', row.name);
//     }
// }

// function update_debtor_code(frm){
//     frappe.db.get_value('Customer', frm.doc.customer, 'debtor_code')
//         .then(response => {
//             if(response.message.debtor_code != frm.doc.debtor_code){
//                 frm.set_value('debtor_code', response.message.debtor_code);
//             }
//         });
// }

// function update_tax(frm){
//     $.each(frm.doc.tax || [], function(index, row) {
//         if(row.charge_type == "On Net Total"){
//             frappe.model.set_value(row.doctype, row.name, 'tax_amount', row.rate/100 * frm.doc.net_total);
//         }
//     });
//     update_total(frm);
// }

// function update_total(frm){
//     let total_amount = frm.doc.net_total;
//     let total_tax = 0;
//     $.each(frm.doc.tax || [], function(index, row) {
//         if(row.tax_amount) {
//             total_amount = total_amount + row.tax_amount;
//             total_tax = total_tax + row.tax_amount;
//             // frappe.model.set_value(row.doctype, row.name, 'total', total_amount);
//         } else {
//             // frappe.model.set_value(row.doctype, row.name, 'total', total_amount);
//         }
//     });
//     frm.set_value("custom_total_tax_amount", total_tax);
//     update_customer(frm);
// }


// function count_net_total(frm) {
//     let net_total = 0;
//     $.each(frm.doc.accounts || [], function(index, row) {
//         if(frm.doc.from_template == "Credit Note") {
//             if (row.credit_in_account_currency) {
//                 net_total = net_total + row.credit_in_account_currency;
//             }
//         } else if (frm.doc.from_template == "Debit Note") {
//             if (row.debit_in_account_currency) {
//                 net_total = net_total + row.debit_in_account_currency;
//             }
//         }
//     });
//     frm.set_value("net_total", net_total);
// }

// function update_customer(frm) {
//     // To change the tax account name modify here
//     let tax_account_name = "GST - LCESB";
    
    
//     $.each(frm.doc.accounts || [], function(index, row) {
//         if (row.party_type === 'Customer') { // Only update if party_type is 'Customer'
//             frappe.model.set_value(row.doctype, row.name, 'party', frm.doc.customer);
//             if ((frm.doc.accounts || []).length < 3) {
//                 if(frm.doc.net_total && (frm.doc.from_template == 'Debit Note')){
//                     frappe.model.set_value(row.doctype, row.name, 'debit_in_account_currency', frm.doc.net_total);
//                 }
//                 else if(frm.doc.net_total && (frm.doc.from_template == 'Credit Note')){
//                     frappe.model.set_value(row.doctype, row.name, 'credit_in_account_currency', frm.doc.net_total);
//                 }
//             }
//         }
//         else if(row.account == tax_account_name) {
//             if(frm.doc.net_total && (frm.doc.from_template == 'Debit Note')){
//                 frappe.model.set_value(row.doctype, row.name, 'credit_in_account_currency', frm.doc.custom_total_tax_amount);
//             }
//             else if(frm.doc.net_total && (frm.doc.from_template == 'Credit Note')){
//                 frappe.model.set_value(row.doctype, row.name, 'debit_in_account_currency', frm.doc.custom_total_tax_amount);
//             }
//         }
//         else{
//             if(frm.doc.net_total && (frm.doc.from_template == 'Debit Note')){
//                 if (frm.doc.custom_total_tax_amount){
//                     frappe.model.set_value(row.doctype, row.name, 'credit_in_account_currency', frm.doc.net_total - frm.doc.custom_total_tax_amount);
//                 } else {
//                     frappe.model.set_value(row.doctype, row.name, 'credit_in_account_currency', frm.doc.net_total);
//                 }
//             }
//             else if(frm.doc.net_total && (frm.doc.from_template == 'Credit Note')){
//                 if (frm.doc.custom_total_tax_amount){
//                     frappe.model.set_value(row.doctype, row.name, 'debit_in_account_currency', frm.doc.net_total - frm.doc.custom_total_tax_amount);
//                 } else {
//                     frappe.model.set_value(row.doctype, row.name, 'debit_in_account_currency', frm.doc.net_total);
//                 }
//             }
//         }
//     });
// }
