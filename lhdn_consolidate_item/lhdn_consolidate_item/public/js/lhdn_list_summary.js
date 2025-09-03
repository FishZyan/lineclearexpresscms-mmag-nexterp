// No longer use it and update it

frappe.listview_settings['LHDN Consolidate Summary'] = {
    onload: function(listview) {
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
        
                        frappe.show_progress('Processing Items', progress, 100, message);
        
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