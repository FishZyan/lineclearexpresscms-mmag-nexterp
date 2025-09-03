
frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        if (frm.doc.docstatus == "1"){

            frm.set_df_property('custom_cancel_reason', 'hidden', 0)
            frm.set_df_property('custom_cancel_reason', 'reqd', 1)

            if (frm.doc.custom_lhdn_status != "Valid"){

                frm.add_custom_button(__("Send invoice"), function() {
                    frm.call({
                        // method:"myinvois.myinvois.myinvoissdkcode.myinvois_Call",
                        // method:"myinvois.myinvois.sign_invoice.myinvois_Call",
                        method:"myinvois.myinvois.sign_invoice.lhdn_Background",
                        
                        
                        args: {
                            "invoice_number": frm.doc.name,
    
                        },
                        // args: {
                        //     "invoice_number": frm.doc.name,
                        //     "company_name" : frm.doc.company_name,
                        //     "compliance_type": "1"
                        // },
                        callback: function(response) {
                            if (response.message) {  
                                // frappe.msgprint(response.message);
                                frm.reload_doc();
        
                            }
                            frm.reload_doc();
                        }
                    });
                    frm.reload_doc();
                }, __("EInvoice"));

                
            }

            
        }
      
    },
    custom_refresh_status:function(frm){
        frm.call({
            // method:"myinvois.myinvois.myinvoissdkcode.myinvois_Call",
            // method:"myinvois.myinvois.sign_invoice.myinvois_Call",
            method:"myinvois.myinvois.sign_invoice.refresh_doc_status",
            
            
            args: {
                "uuid": frm.doc.custom_uuid,
                "invoice_number":frm.doc.name

            },
            // args: {
            //     "invoice_number": frm.doc.name,
            //     "company_name" : frm.doc.company_name,
            //     "compliance_type": "1"
            // },
            callback: function(response) {
                if (response.message) {  
                    // frappe.msgprint(response.message);
                    frm.reload_doc();

                }
                frm.reload_doc();
            }
            
        
        });
        frm.reload_doc();
    }
});


