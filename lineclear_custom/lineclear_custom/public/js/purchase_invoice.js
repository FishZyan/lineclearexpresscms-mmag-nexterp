frappe.ui.form.on('Purchase Invoice', {
	validate: function(frm) {
        frm.doc.items.forEach(item => {
            update_item_tax_amount(frm, item.doctype, item.name);
        });
        update_item_taxes(frm);
    },
    refresh: function(frm) {
        hide_field(frm);
        // frm.set_value('taxes_and_charges', null);
    }
});

frappe.ui.form.on('Purchase Invoice Item', {
	rate: function(frm, cdt, cdn){
	    update_item_tax_amount(frm, cdt, cdn);
	},
	qty: function(frm, cdt, cdn){
	    update_item_tax_amount(frm, cdt, cdn);
	},
	custom_tax_code: function(frm, cdt, cdn){
	    update_item_tax_amount(frm, cdt, cdn);
	},
	custom_tax_amount: function(frm, cdt, cdn){
	    update_item_taxes(frm);
	}
});

function hide_field(frm) {
    frm.set_df_property('is_pos', 'hidden', 1);
    frm.set_df_property('project', 'hidden', 1);
    frm.set_df_property('scan_barcode', 'hidden', 1);
    frm.set_df_property('company', 'hidden', 1);
    frm.set_df_property('posting_time', 'hidden', 1);
    frm.set_df_property('company_tax_id', 'hidden', 1);
    frm.set_df_property('incoterm', 'hidden', 1);
    frm.set_df_property('currency', 'hidden', 1);
    frm.set_df_property('tax_id', 'hidden', 1);
    frm.set_df_property('selling_price_list', 'hidden', 1);
    frm.set_df_property('ignore_pricing_rule', 'hidden', 1);
    frm.set_df_property('is_return', 'hidden', 1);
    frm.set_df_property('is_debit_note', 'hidden', 1);
    frm.set_df_property('is_cash_or_non_trade_discount', 'hidden', 1);
    // frm.set_df_property('taxes_and_charges', 'hidden', 1);
    // frm.set_df_property('taxes', 'hidden', 1);
    // frm.set_df_property('naming_series', 'hidden', 1);
    // frm.set_value('set_posting_time', 1);
}

function update_item_tax_amount(frm, cdt, cdn){
    let row = locals[cdt][cdn];
    if(row.custom_tax_code){
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Purchase Taxes and Charges Template",
                name: row.custom_tax_code
            },
            callback: function(r) {
                if (r.message && r.message.taxes && r.message.taxes.length > 0) {
                    // Assuming you want to apply the first tax rate
                    let tax_rate = r.message.taxes[0].rate;
                    let amount = row.rate * row.qty
                    let tax_amount = amount * (tax_rate / 100);

                    frappe.model.set_value(cdt, cdn, 'custom_tax_amount', tax_amount);
                    frappe.model.set_value(cdt, cdn, 'amount', amount);
                }
            }
        });
    } else {
        frappe.model.set_value(cdt, cdn, 'custom_tax_amount', 0);
    }
}


function update_item_taxes(frm, cdt, cdn) {
    frm.clear_table('taxes');

        // Then, add one tax per item
        (frm.doc.items || []).forEach(item => {
            let row = locals[item.doctype][item.name]

            if(row.custom_tax_code){
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Purchase Taxes and Charges Template",
                        name: row.custom_tax_code
                    },
                    callback: function(r) {
                        if (r.message && r.message.taxes && r.message.taxes.length > 0) {
                            let tax = frm.add_child('taxes');
                            tax.charge_type = 'Actual';
                            tax.account_head = r.message.taxes[0].account_head;
                            tax.description = `Tax for Item: ${item.item_name}`;
                            tax.tax_amount = item.custom_tax_amount;
                            tax.rate = r.message.taxes[0].rate;
                        }
                    }
                });
            };
        });

        frm.refresh_field('taxes');
}