frappe.ui.form.on('Payment Entry', {
    onload(frm) {
        if (!frm.is_new() && 
            [0, 1].includes(frm.doc.docstatus)
        ) create_download_button(frm);
	},
	refresh(frm) {
        if (!frm.is_new() && 
        [0, 1].includes(frm.doc.docstatus)
    ) create_download_button(frm);
	},
    payment_type: (frm) => {
        update_naming_series(frm)
    },
    mode_of_payment: (frm) => {
        update_naming_series(frm)
    },
    party: (frm) => {
        update_party_code(frm);
    },
    party_name: (frm) => {
        update_party_code(frm);
    }
});

function update_party_code(frm) {
    const { payment_type, party_type, party } = frm.doc;

    if (!party_type || !party) return;

    if (payment_type == 'Pay' && party_type == 'Supplier') {
        frappe.db.get_value('Supplier', party, 'creditor_code')
            .then(r => {
                if (r && r.message) {
                    frm.set_value('creditor_code', r.message.creditor_code);
                    frm.set_value('debtor_code', null);
                    frm.refresh_field('creditor_code');
                }
            });
    } else if (payment_type == 'Receive' && party_type == 'Customer') {
        frappe.db.get_value('Customer', party, 'debtor_code')
            .then(r => {
                if (r && r.message) {
                    frm.set_value('debtor_code', r.message.debtor_code);
                    frm.set_value('creditor_code', null);
                    frm.refresh_field('debtor_code');
                }
            });
    } else {
        frm.set_value('debtor_code', null);
        frm.set_value('creditor_code', null);
    }
}


function update_naming_series(frm) {
    payment_type = frm.doc.payment_type
    payment_method = frm.doc.mode_of_payment || ''

    if (payment_type === 'Receive') {

        if (payment_method.includes('MBB - KD (CONTRA)'))
            frm.set_value('naming_series','R-MBBKD-C-.#####');

        else if (payment_method.includes('MBB (USJ 10)'))
            frm.set_value('naming_series','R-MBBUSJ.#####');

        else if (payment_method.includes('MBB (Sec 14)'))
            frm.set_value('naming_series','R-MBBS14-.#####');

        else if (payment_method.includes('RHBSS2', 'RHB SS2'))
            frm.set_value('naming_series','R-RHBSS2 .#####');

        else if (payment_method.includes('CONTRA ACCOUNT'))
            frm.set_value('naming_series','Contra AR.#####');

        else if (payment_method.includes('CIMB'))
            frm.set_value('naming_series','R-CIMB.#####');
        
        // else if (payment_method.includes('OCBC'))
        //     frm.doc.naming_series = 'R-OCBC.#####';

        else if (payment_method.includes('PBB'))
            frm.set_value('naming_series','R-PBB.#####');

        else if (payment_method.includes('RHB'))
            frm.doc.naming_series = 'R-RHB.#####';

        // else if (payment_method.includes('LVH'))
        //     frm.doc.naming_series = 'R-LVH.#####';

        else
            frm.set_value('naming_series','R-RHB.#####');

    } else if (payment_type === 'Pay') {

        if (payment_method.includes('MBB (USJ 10)'))
            frm.set_value('naming_series','PV-MBBUSJ.#####');

        else if (payment_method.includes('MBB (Sec 14)'))
            frm.set_value('naming_series','PV-MBBS14-.#####');

        else if (payment_method.includes('RHBSS2', 'RHB SS2'))
            frm.set_value('naming_series','PV-RHBSS2 .#####');

        else if (payment_method.includes('CONTRA ACCOUNT'))
            frm.set_value('naming_series','Contra AP.#####');

        else if (payment_method.includes('CIMB'))
            frm.set_value('naming_series','PV-CIMB.#####');
        
        else if (payment_method.includes('OCBC'))
            frm.set_value('naming_series','PV-OCBC.#####');

        else if (payment_method.includes('PBB'))
            frm.set_value('naming_series','PV-PBB.#####');

        else if (payment_method.includes('RHB'))
            frm.set_value('naming_series','PV-RHB.#####');

        else if (payment_method.includes('LVH'))
            frm.set_value('naming_series','PV-LVH.#####');

        else
            frm.set_value('naming_series','PVM.#####');
    }

    frm.refresh_field('naming_series');
}


function create_download_button(frm) {
    // export action buttons: Journal Entry
    btn_name = (frm.doc.payment_type === 'Pay') ? "Payment Voucher" : "Official Receipt";
    
    frm.add_custom_button(btn_name, () => { 
        const url = `/api/method/lineclear_custom.lineclear_custom.payment_entry_api.download_payment?doc_no=${frm.doc.name}`;
        window.open(url);
    }, __("Actions"));
}