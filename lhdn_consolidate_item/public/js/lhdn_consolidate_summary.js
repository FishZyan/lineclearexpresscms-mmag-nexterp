frappe.ui.form.on('LHDN Consolidate Summary', {
    refresh_status_btn: function (frm) {
        let uuid = frm.doc.uuid;
        let batch_id = frm.doc.batch_id;
        let user_email = frappe.session.user_email

        frappe.call({
            method: "lhdn_consolidate_item.lhdn_consolidate_item.lhdn_refresh_status.refresh_doc_status",
            args: {
                "uuid": uuid,
                "batch_id": batch_id,
                "isDirect": true,
                "user_email": user_email
            },
            callback: function(response) {
                let data = response.message;

                if (data.length > 0) {
                    frappe.msgprint({
                        title: __('Success'),
                        message: __(data + ' had been updated successfully!'),
                        indicator: 'green',
                        primary_action: {
                            label: 'OK',
                            action: function() {
                                location.reload();  // Refresh page after user clicks OK
                            }
                        }
                    });
                }
            } 
        })
    }

});