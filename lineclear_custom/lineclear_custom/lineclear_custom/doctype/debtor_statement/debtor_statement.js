// Copyright (c) 2025, Ku Zheng Yan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Debtor Statement", {
    after_save(frm) {
        // refresh UI after the schedule events is generated
        frm.reload_doc();
    },
    onload(frm) {
        if (frm.doc.docstatus == 1) {
            create_download_button(frm);
            lock_field(frm);
        }
	},
	refresh(frm) {
        localStorage.setItem("table_scheduled_events", JSON.stringify(frm.doc.table_scheduled_events))
        
        if (frm.doc.docstatus == 1) {
            create_download_button(frm);
            lock_field(frm);
        }
	},
    onload_post_render(frm) {
		// browser back button: remove table_scheduled_events from localStorage
		addEventListener('popstate', () => {
            localStorage.removeItem("table_scheduled_events");
		})

		// SPA route change: remove table_scheduled_events from localStorage
        frappe.router.on("change", () => {
            localStorage.removeItem("table_scheduled_events");
        });

    }
});


frappe.ui.form.on("Debtor Statement Events", {
    date: (frm, cdt, cdn) => {
        validate_event_date(frm, cdt, cdn);
        frm.refresh_field("table_scheduled_events");
    }
});



/* -------------------------------
        Helper Functions
------------------------------- */
function validate_event_date(frm, cdt, cdn) {
    const prev_events = JSON.parse(localStorage.getItem("table_scheduled_events"));
    const events = frm.doc.table_scheduled_events;

    if (!events || events.length === 0) return;

    let last_date = null;

    for (let i=0; i < events.length; i++) {
        if (events[i].name == cdn) {
            if (events[i].sent == 1) {
                events[i].date = prev_events[i].date;
                frappe.throw("Date cannot changed after sent.");
                break;
            } else if (events[i].date < last_date) {
                events[i].date = prev_events[i].date;
                frappe.throw("Date cannot be earlier than the date of its previous event.");
                break;
            }
        }
        last_date = events[i].date;
    }
}


function lock_field(frm) {
    if (frm.doc.custom_status == "Cleared") frm.set_df_property("custom_status", "read_only", 1);
}


function create_download_button(frm) {
    frappe.call({
        method: "lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.get_schedule_events",
        args: {
            doc_no: frm.doc.name
        },
        callback: (r) => {
            if (!r.message) return;

            const files = r.message;

            for (let file of files) {
                switch (file.doc_name) {

                    /* -------------------------------
                            Debtor Statement
                    ------------------------------- */
                    case "Debtor Statement":
                        frm.add_custom_button("Statements", () => {
                            const url = `/api/method/lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.download_statement?doc_no=${frm.doc.name}&include_payment_details=0`;
                            window.open(url);
                        }, __("Download"));

                        frm.add_custom_button("Statements", () => {
                            frappe.call({
                                method: 'lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.send_statement',
                                args: {
                                    doc_no: frm.doc.name,
                                    include_payment_details: '0'
                                },
                                callback: (r) => {
                                    frm.reload_doc();
                                    if (!r.exc) frappe.msgprint(__('Email sent successfully!'));
                                }
                            })
                        }, __("Send"));
                        break;

                    /* ------------------------------------
                        Debtor Statement (With Details)
                    ------------------------------------ */
                    case "Debtor Statement (With Details)":
                        frm.add_custom_button("Detail Statements", () => {
                            const url = `/api/method/lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.download_statement?doc_no=${frm.doc.name}&include_payment_details=1`;
                            window.open(url);
                        }, __("Download"));

                        frm.add_custom_button("Detail Statements", () => {
                            frappe.call({
                                method: 'lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.send_statement',
                                args: {
                                    doc_no: frm.doc.name,
                                    include_payment_details: '1'
                                },
                                callback: (r) => {
                                    frm.reload_doc();
                                    if (!r.exc) frappe.msgprint(__('Email sent successfully!'));
                                }
                            })
                        }, __("Send"));
                        break;

                    /* -------------------------------
                            First Reminder Letter
                    ------------------------------- */
                    case "First Reminder Letter":
                        frm.add_custom_button("First Reminder", () => {
                            const url = `/api/method/lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.download_reminder?doc_no=${frm.doc.name}&reminder=FIRST`;
                            window.open(url);
                        }, __("Download"));

                        frm.add_custom_button("First Reminder", () => {
                            frappe.call({
                                method: 'lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.send_reminder',
                                args: { doc_no: frm.doc.name, reminder: 'FIRST' },
                                callback: (r) => {
                                    frm.reload_doc();
                                    if (!r.exc) frappe.msgprint(__('Email sent successfully!'));
                                }
                            })
                        }, __("Send"));
                        break;

                    /* -------------------------------
                            Second Reminder Letter
                    ------------------------------- */
                    case "Second Reminder Letter":
                        frm.add_custom_button("Second Reminder", () => {
                            const url = `/api/method/lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.download_reminder?doc_no=${frm.doc.name}&reminder=SECOND`;
                            window.open(url);
                        }, __("Download"));

                        frm.add_custom_button("Second Reminder", () => {
                            frappe.call({
                                method: 'lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.send_reminder',
                                args: { doc_no: frm.doc.name, reminder: 'SECOND' },
                                callback: (r) => {
                                    frm.reload_doc();
                                    if (!r.exc) frappe.msgprint(__('Email sent successfully!'));
                                }
                            })
                        }, __("Send"));
                        break;

                    /* -------------------------------
                            Third Reminder Letter
                    ------------------------------- */
                    case "Third Reminder Letter":
                        frm.add_custom_button("Third Reminder", () => {
                            const url = `/api/method/lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.download_reminder?doc_no=${frm.doc.name}&reminder=THIRD`;
                            window.open(url);
                        }, __("Download"));

                        frm.add_custom_button("Third Reminder", () => {
                            frappe.call({
                                method: 'lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.send_reminder',
                                args: { doc_no: frm.doc.name, reminder: 'THIRD' },
                                callback: (r) => {
                                    frm.reload_doc();
                                    if (!r.exc) frappe.msgprint(__('Email sent successfully!'));
                                }
                            })
                        }, __("Send"));
                        break;

                    /* -------------------------------
                                Overdue Letter
                    ------------------------------- */
                    case "Overdue Letter":
                        frm.add_custom_button("Overdue Letter", () => {
                            const url = `/api/method/lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.download_overdue?doc_no=${frm.doc.name}`;
                            window.open(url);
                        }, __("Download"));

                        frm.add_custom_button("Overdue Letter", () => {
                            frappe.call({
                                method: 'lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.send_overdue',
                                args: { doc_no: frm.doc.name },
                                callback: (r) => {
                                    frm.reload_doc();
                                    if (!r.exc) frappe.msgprint(__('Email sent successfully!'));
                                }
                            })
                        }, __("Send"));
                        break;
                }
            }
        }
    });
}
