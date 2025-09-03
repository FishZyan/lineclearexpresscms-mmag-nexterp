// Check any existing E-Invoice List View function JavaScript
const original_e_invoice_listview = frappe.listview_settings['E-Invoice Summary']?.onload

frappe.listview_settings['E-Invoice Summary'] = {
    onload: function(listview) {

        let finishTriggered = false; 

        // Appened E-Inoivce Listview function
        if (original_e_invoice_listview) {
            original_e_invoice_listview(listview)
        }

        listview.page.add_button(__('Consolidate Submission'), function () {
            
            //Constant Fixed Value
            let today = frappe.datetime.now_date();
            let seven_days_before = frappe.datetime.add_days(today, -7);
            let item_list = []

            //Pop Out Modal
            let dialog = new frappe.ui.Dialog({
                title: "E-Invoice Bulk Submission",
                fields: [
                    {
                        label: "Invoice Start Date",
                        fieldname: "invoice_from_date",
                        fieldtype: "Date",
                        default: seven_days_before,
                        reqd: 1
                    },
                    {
                        label: "Invoice End Date",
                        fieldname: "invoice_end_date",
                        fieldtype: "Date",
                        default: today,
                        reqd: 1
                    },
                    {
                        label: "Source Type",
                        fieldname: "source_type",
                        fieldtype: "Select",
                        options: [
                            "ERPNEXT System",
                            //"Manual"
                        ],
                        default: "ERPNEXT System",
                        reqd: 1
                    },
                    {
                        label: "Docuement Type",
                        fieldname: "document_type",
                        fieldtype: "Select",
                        options: [
                            "Invoice",
                            "Credit Note",
                            "Debit Note",
                            //"Refund Note",
                            "Self-billed Invoice",
                            "Self-billed Credit Note",
                            "Self-billed Debit Note",
                            "Self-billed Refund Note"
                        ],
                        default: "Invoice",
                        reqd: 1
                    },
                    {
                        label: "Currency",
                        fieldname: "currency",
                        fieldtype: "Select",
                        option: ["MYR"],
                        read_only: 1,
                        default: "MYR",
                        reqd: 1
                    },
                    {
                        label: "Total Item",
                        fieldname: "total_item",
                        fieldtype: "Int",
                        read_only: 1,
                        default: 0
                    },
                    {
                        label: "Total Final Amount",
                        fieldname: "total_final_amount",
                        fieldtype: "Float",
                        precision: 2,
                        read_only: 1,
                        default: 0.00
                    },
                    {
                        label: "Total Tax Amount",
                        fieldname: "total_tax_amount",
                        fieldtype: "Float",
                        precision: 2,
                        read_only: 1,
                        default: 0.00
                    },
                    {
                        label: "Total Taxable Amount",
                        fieldname: "total_taxable_amount",
                        fieldtype: "Float",
                        precision: 2,
                        read_only: 1,
                        default: 0.00
                    },
                    {
                        label: "Remark",
                        fieldname: "remark",
                        fieldtype: "Text",
                        read_only: 1,
                        default: ""
                    },

                ],
                size: "large",
                primary_action_label: "Submit Consolidate Item",
                primary_action() {
                    let progress_key = setupProgressId()
                    if (item_list.length > 0) {
                        track_progress(progress_key);
                        bulk_submission(progress_key); 
                    }
                    dialog.hide();
                }
            });

            function item_fetch_list() {

                //Parameter
                let start_date = dialog.get_value("invoice_from_date");
                let end_date = dialog.get_value("invoice_end_date");
                let document_type = dialog.get_value("document_type");
                let currency = dialog.get_value("currency")
                let source_type = dialog.get_value("source_type")

                if (start_date && end_date && document_type && currency) {
                    frappe.call({
                        method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_fetch_list.get_lhdn_consolidate_list",
                        args: {
                            start_date: start_date,
                            end_date: end_date,
                            document_type: document_type,
                            currency: currency,
                            source_type: source_type
                        },
                        callback: function(response) {
                            let data = response.message;
                            
                            if (data.item_list.length > 0) {
                                reset_remark;
                                dialog.set_value("total_item",data.total_item);
                                dialog.set_value("total_final_amount",data.total_final_amount);
                                dialog.set_value("total_tax_amount",data.total_tax_amount);
                                dialog.set_value("total_taxable_amount",data.total_taxable_amount);
                                dialog.set_value("remark","");
                                item_list = data.item_list;
                            } else {
                                dialog.set_value("total_item",data.total_item);
                                dialog.set_value("total_final_amount",data.total_final_amount);
                                dialog.set_value("total_tax_amount",data.total_tax_amount);
                                dialog.set_value("total_taxable_amount",data.total_taxable_amount);
                                dialog.set_value("remark","There is no item within these date range and document type.");
                            }

                            
                            
                        }
                    });
                }
            }

            function reset_remark() {
                dialog.set_value("total_final_amount",0.00);
                dialog.set_value("total_tax_amount",0.00);
                dialog.set_value("total_taxable_amount",0.00);
                dialog.set_value("remark","");
                item_list = [];
            }

            function bulk_submission(progress_key) {
                if (item_list.length > 0) {
                    frappe.call({
                        method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_consolidate_api.lhdn_batch_call_async",
                        // method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_consolidate_api.lhdn_batch_call",
                        args: {
                            invoice_number_list: item_list,
                            document_type: dialog.get_value("document_type"),
                            user_email: frappe.session.user_email,
                            progress_key: progress_key,
                            start_date: dialog.get_value("invoice_from_date"),
                            end_date: dialog.get_value("invoice_end_date"),
                            source_type: dialog.get_value("source_type")
                        }
                    });
                }
            }

            function setupProgressId() {
                return Math.random().toString(36).substring(2, 12); // Generate a 10-char hash
            }

            // Attach event listener to select field
            dialog.fields_dict.invoice_from_date.df.change = item_fetch_list;
            dialog.fields_dict.invoice_end_date.df.change = item_fetch_list;
            dialog.fields_dict.document_type.df.change = item_fetch_list;
            dialog.fields_dict.currency.df.change = item_fetch_list;
            dialog.fields_dict.source_type.df.change = item_fetch_list;

            dialog.show();

        });

        listview.page.add_button(__('Refresh Status'), function () {
            let user_email = frappe.session.user_email

            frappe.call({
                method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_refresh_status.refresh_status_enqueue",
                args: {
                    user_email: user_email
                },
                callback: function(response) {
                    let data = response.message;
                    track_progress(data);
                }
            })
        });

        function track_progress(progress_key) {
            frappe.show_progress('Processing Items', 0, 100, "System processing..");

            let interval = setInterval(() => {
                frappe.call({
                    method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_progress_handling.get_progress",
                    args: { progress_key: progress_key },
                    callback: function(response) {
                        let progressData = response.message;
                        let is_complete = progressData.is_complete;
                        let message = progressData.message;
                        let summary_message = formatItemListmessage(progressData.processed_items);
                        let final_message = message + " " + summary_message
                        let progress = parseInt(progressData.progress);
                        let summary_uuid = progressData.summary_uuid
                        let user_email = progressData.user_email
                        let progress_id = progressData.progress_id
                        let processed_count = progressData.process_count
                        let total_items = progressData.total_items
        
                        frappe.show_progress('Processing Items', progress, 100, message);
        
                        if (processed_count >= total_items && !finishTriggered) {
                            finishTriggered = true;
                            frappe.call({
                                method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_consolidate_api.finish_consolidate_refresh_function",
                                args: {
                                    progress_id: progress_id,
                                    summary_uuid: summary_uuid,
                                    user_email: user_email
                                }    
                            })
                        }

                        if (is_complete) {
                            clearInterval(interval);
                            frappe.msgprint({
                                message: final_message,
                                indicator: "green",
                                title: "Success",
                                primary_action: {
                                    label: "OK",
                                    action: function() {
                                         location.reload(); // Reload when user clicks OK
                                    }
                                }
                            });
                        }
                    }
                });
            }, 3000);
        }

        // Update message over to line space below
        function formatItemListmessage(itemList) {
            if (!itemList || itemList.length === 0) {
                return "No items were processed.";
            }
        
            return `Processed Items: \n\n ${itemList.join("\n\n")}`;
        }
    }
}