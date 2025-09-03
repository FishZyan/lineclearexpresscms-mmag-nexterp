#!/bin/bash
cd /opt/frappe-bench/frappe-bench
source env/bin/activate
# bench --site lceerptest.local execute lineclear_custom.lineclear_custom.apinvoice_import.import_apinvoice
# bench --site lceerptest.local execute lineclear_custom.lineclear_custom.apdebit_import.import_apdebit
bench --site lceerptest.local execute lineclear_custom.lineclear_custom.appayment_import.import_appayment
