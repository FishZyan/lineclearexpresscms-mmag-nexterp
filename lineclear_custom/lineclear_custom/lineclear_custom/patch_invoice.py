import sys
import requests
import json
from datetime import datetime, timedelta
import csv
import frappe
import os
import time
from collections import defaultdict

def get_unique_filename(filename):
    #status file name sales_invoice_status-YYMM-###.csv
    # Get current year and month in YYMM format
    date_part = datetime.now().strftime("%y%m")
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    directory = current_dir + "/status/"
    base_filename = f"{filename}-{date_part}"
    ext = ".csv"

    counter = 1
    new_filename = f"{directory}{base_filename}-001{ext}"  # Start with 001
    
    # Loop to check existing files and increment the number
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{directory}{base_filename}-{counter:03}{ext}"  # Format as ### (e.g., 001, 002, etc.)
        counter += 1

    return new_filename

def fetch_data(input_file):
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    input_file= current_dir + "/" + input_file
    
    try:
        #Track the time of the process
        start_time = time.time()

        # Open the input and output files
        output_file = get_unique_filename("Patch_Invoice_Status")
        with open(input_file, mode='r') as infile, open(output_file, mode='w', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            next(reader, None)
            
            # patch_invoice(reader, writer)
            patch_credit_note(reader, writer)
            # patch_journal_entry(reader, writer)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            print(f"Process took {int(minutes)} minutes and {int(seconds):.2f} seconds.")

    except FileNotFoundError:
        print(f"The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
def patch_invoice(rows, writer):
    logger = frappe.logger("invoice_patch")
    grouped_data = defaultdict(list)
    
    failed_docs, failed_rows = [], []
    count = 0
    
    for row in rows:
        id_ = row[0]
        grouped_data[id_].append(row)

    for id_, entries in grouped_data.items():
        first = entries[0]
        docdate = first[1]
        dt = datetime.strptime(docdate, "%d/%m/%Y")
        docdate_obj = dt.date()
        skip = False
        
        try:
            invoice = frappe.get_doc("Sales Invoice", first[2].strip())
        except:
            writer.writerow(["Invoice Not Found", first[0], first[2].strip()])
            continue
        
        #check if cancel
        if invoice.docstatus == 2:
            invoice = frappe.get_doc("Sales Invoice", first[2].strip() + ' Amend')
            if invoice.docstatus == 2:
                writer.writerow(["Invoice Cancelled", first[0]])
                continue
        
        if invoice.posting_date != docdate_obj:
            print(f"Posting date mismatch for invoice {first[0]}: {invoice.posting_date} != {docdate_obj}")
            writer.writerow(["Posting Date Mismatch", first[0], invoice.posting_date, docdate])
            continue
        
        tax_count = -1
        try:
            for i in range(len(entries)):
                if not invoice.items[i] or not entries[i]:
                    writer.writerow(["Item Not Found", first[0], first[2].strip(), i])
                    skip = True
                    break
                if round(float(invoice.items[i].amount), 2) != round(float(entries[i][8]), 2):
                    writer.writerow(["Amount Mismatch", first[0], first[2], invoice.items[i].amount, entries[i][8]])
                    skip = True
                    break
                if invoice.items[i].custom_tax_code:
                    if invoice.items[i].custom_tax_code.split(" - ")[0] != entries[i][6]:
                        writer.writerow(["Tax Code Mismatch", first[0], first[2], invoice.items[i].custom_tax_code, entries[i][6]])
                        skip = True
                        break
                if invoice.items[i].income_account.split(" - ")[0] != entries[i][3]:
                    writer.writerow(["Income Account Mismatch", first[0], first[2], invoice.items[i].income_account, entries[i][3]])
                    skip = True
                    break
                if round(float(entries[i][7]), 2) != 0.00:
                    tax_count += 1
                    if not invoice.taxes[tax_count]:
                        writer.writerow(["Tax Not Found", first[0], first[2], i])
                        skip = True
                        break
                    if round(float(invoice.taxes[tax_count].tax_amount), 2) != round(float(entries[i][7]), 2):
                        writer.writerow(["Tax Amount Mismatch", first[0], first[2], invoice.taxes[tax_count].tax_amount, entries[i][7]])
                        break
                invoice.items[i].custom_tax_amount = entries[i][7]
                if entries[i][5]:
                    try:
                        cost_centered = frappe.get_doc("Cost Center", entries[i][5])
                        if cost_centered:
                            invoice.items[i].cost_center = cost_centered.name
                            if invoice.taxes and invoice.taxes[tax_count]:
                                invoice.taxes[tax_count].cost_center = cost_centered.name
                    except frappe.DoesNotExistError:
                        writer.writerow(["Cost Center Not Found", first[0], first[2], entries[i][5]])
                        skip = True
                        break
                invoice.custom_autocount_dockey = first[0]
            invoice.save()
            frappe.db.commit()
            count += 1
            print(f"Progressing...{count}/{len(grouped_data)}")
        except Exception as e:
            logger.error(f"❌ Failed to update invoice {first[0]}: {e}", exc_info=True)
            writer.writerow(["Update Failed", first[0], str(e)])
            failed_docs.append(first[0])
            failed_rows.append(entries)
            continue
        
def patch_journal_entry(rows, writer):
    logger = frappe.logger("journal_patch")
    grouped_data = defaultdict(list)
    
    failed_docs, failed_rows = [], []
    count = 0
    
    for row in rows:
        id_ = row[0]
        grouped_data[id_].append(row)

    for id_, entries in grouped_data.items():
        first = entries[0]
        docdate = first[1]
        dt = datetime.strptime(docdate, "%d/%m/%Y")
        docdate_obj = dt.date()
        skip = False
        
        try:
            invoice = frappe.get_doc("Journal Entry", first[2].strip())
        except:
            writer.writerow(["Journal Entry Not Found", first[0], first[2].strip()])
            continue
        
        #check if cancel
        if invoice.docstatus == 2:
            invoice = frappe.get_doc("Journal Entry", first[2].strip() + ' Amend')
            if invoice.docstatus == 2:
                writer.writerow(["Journal Entry Cancelled", first[0]])
                continue
        
        if invoice.posting_date != docdate_obj:
            print(f"Posting date mismatch for Journal Entry {first[0]}: {invoice.posting_date} != {docdate_obj}")
            writer.writerow(["Posting Date Mismatch", first[0], invoice.posting_date, docdate])
            continue
        
        if invoice.voucher_type != first[8]:
            print(f"Creditor mismatch for Journal Entry {first[0]}, {first[8]}")
            writer.writerow(["Entry Type Mismatch", first[0], first[8]])
            continue
        
        if invoice.accounting_type != "Accounts Receivable":
            writer.writerow(["Invoice is not receviable", first[0], first[2]])
            continue
        
        
        try:
            for i in range(len(entries)):
                if not invoice.accounts[i] or not entries[i] or not invoice.accounts[(i*2)+1]:
                    writer.writerow(["Account Row Not Found", first[0], first[2].strip(), i])
                    skip = True
                    break
                if invoice.accounts[i*2].account.split(" - ")[0] != entries[i][3]:
                    writer.writerow(["Income Account Mismatch", first[0], first[2], invoice.accounts[i].account, entries[i][3]])
                    skip = True
                    break
                
                if first[8] == "Credit Note":
                    if(round(float(entries[i][6]), 2) != 0.00):
                        if round(float(invoice.accounts[i*2].debit_in_account_currency), 2) != round(float(entries[i][6]), 2):
                            writer.writerow(["Amount Mismatch", first[0], first[2], invoice.accounts[i].debit_in_account_currency, entries[i][6]])
                            skip = True
                            break
                    else:
                        if round(float(invoice.accounts[i*2].debit_in_account_currency), 2) != -round(float(entries[i][7]), 2):
                            writer.writerow(["Amount Mismatch", first[0], first[2], invoice.accounts[i].debit_in_account_currency, -round(float(entries[i][7]))])
                            skip = True
                            break
                elif first[8] == "Debit Note":
                    if(round(float(entries[i][7]), 2) != 0.00):
                        if round(float(invoice.accounts[i*2].credit_in_account_currency), 2) != round(float(entries[i][7]), 2):
                            writer.writerow(["Amount Mismatch", first[0], first[2], invoice.accounts[i].credit_in_account_currency, entries[i][7],"t"])
                            skip = True
                            break
                    else:
                        if round(float(invoice.accounts[i*2].credit_in_account_currency), 2) != -round(float(entries[i][6]), 2):
                            writer.writerow(["Amount Mismatch", first[0], first[2], invoice.accounts[i].credit_in_account_currency, -round(float(entries[i][6])), "fd"])
                            skip = True
                            break
                    
                if (entries[i][5]):
                    try:
                        tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": entries[i][5]})
                        if tax_code:
                            invoice.accounts[i*2].tax_code = entries[i][5]
                    except frappe.DoesNotExistError:
                        writer.writerow(["Tax Code Not Found", first[0], first[2], entries[i][5]])
                        skip = True
                        break
                
                if entries[i][4]:
                    try:
                        cost_centered = frappe.get_doc("Cost Center", entries[i][4])
                        if cost_centered:
                            invoice.accounts[i*2].cost_center = cost_centered.name
                    except frappe.DoesNotExistError:
                        writer.writerow(["Cost Center Not Found", first[0], first[2], entries[i][5]])
                        skip = True
                        break
            invoice.custom_autocount_dockey = first[0]
            invoice.save()
            frappe.db.commit()
            count += 1
            print(f"Progressing...{count}/{len(grouped_data)}")
        except Exception as e:
            logger.error(f"❌ Failed to update invoice {first[0]}: {e}", exc_info=True)
            writer.writerow(["Update Failed", first[0], str(e)])
            failed_docs.append(first[0])
            failed_rows.append(entries)
            continue
        
        
def patch_credit_note(rows, writer):
    logger = frappe.logger("journal_patch")
    grouped_data = defaultdict(list)
    
    failed_docs, failed_rows = [], []
    count = 0
    
    for row in rows:
        id_ = row[0]
        grouped_data[id_].append(row)

    for id_, entries in grouped_data.items():
        first = entries[0]
        docdate = first[1]
        dt = datetime.strptime(docdate, "%d/%m/%Y")
        docdate_obj = dt.date()
        skip = False
        
        try:
            invoice = frappe.get_doc("Journal Entry", first[2].strip())
        except:
            writer.writerow(["Journal Entry Not Found", first[0], first[2].strip()])
            continue
        
        #check if cancel
        if invoice.docstatus == 2:
            invoice = frappe.get_doc("Journal Entry", first[2].strip() + ' Amend')
            if invoice.docstatus == 2:
                writer.writerow(["Journal Entry Cancelled", first[0]])
                continue
        
        if invoice.posting_date != docdate_obj:
            print(f"Posting date mismatch for Journal Entry {first[0]}: {invoice.posting_date} != {docdate_obj}")
            writer.writerow(["Posting Date Mismatch", first[0], invoice.posting_date, docdate])
            continue
        
        if invoice.voucher_type != first[8]:
            print(f"Creditor mismatch for Journal Entry {first[0]}, {first[8]}")
            writer.writerow(["Entry Type Mismatch", first[0], first[8]])
            continue
        
        if invoice.accounting_type != "Accounts Receivable":
            writer.writerow(["Invoice is not receviable", first[0], first[2]])
            continue
        
        try:
            for i in range(len(invoice.accounts)):
                if (invoice.accounts[i].party_type):
                    continue
                    
                if not first[4]:
                    break
                try:
                    cost_centered = frappe.get_doc("Cost Center", entries[0][4])
                    if cost_centered:
                        invoice.accounts[i].cost_center = cost_centered.name
                except frappe.DoesNotExistError:
                    writer.writerow(["Cost Center Not Found", first[0], first[2], entries[i][5]])
                    break
                    
                    
            invoice.custom_autocount_dockey = first[0]
            invoice.save()
            frappe.db.commit()
            count += 1
            print(f"Progressing...{count}/{len(grouped_data)}")
        except Exception as e:
            logger.error(f"❌ Failed to update invoice {first[0]}: {e}", exc_info=True)
            writer.writerow(["Update Failed", first[0], str(e)])
            failed_docs.append(first[0])
            failed_rows.append(entries)
            continue
        
        # try:
        #     rowed = len(entries)
        #     for i in range(len(invoice.accounts)):
        #         if (invoice.accounts[i].party_type):
        #             continue
                    
        #         rowed -= 1    
        #         if not invoice.accounts[i] or not entries[rowed]:
        #             writer.writerow(["Account Row Not Found", first[0], first[2].strip(), i])
        #             break
        #         if invoice.accounts[i].account.split(" - ")[0] != entries[rowed][3]:
        #             writer.writerow(["Income Account Mismatch", first[0], first[2], invoice.accounts[i].account, entries[rowed][3]])
        #             break
                
        #         if first[8] == "Credit Note":
        #             if(round(float(entries[rowed][6]), 2) != 0.00):
        #                 if round(float(invoice.accounts[i].debit_in_account_currency), 2) != round(float(entries[rowed][6]), 2):
        #                     writer.writerow(["Amount Mismatch", first[0], first[2], invoice.accounts[i].debit_in_account_currency, entries[rowed][6]])
        #                     break
        #             else:
        #                 if round(float(invoice.accounts[i].debit_in_account_currency), 2) != -round(float(entries[rowed][7]), 2):
        #                     writer.writerow(["Amount Mismatch", first[0], first[2], invoice.accounts[i].debit_in_account_currency, -round(float(entries[rowed][7]))])
        #                     break
                    
        #         if (entries[rowed][5]):
        #             try:
        #                 tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": entries[rowed][5]})
        #                 if tax_code:
        #                     invoice.accounts[i].tax_code = entries[rowed][5]
        #             except frappe.DoesNotExistError:
        #                 writer.writerow(["Tax Code Not Found", first[0], first[2], entries[rowed][5]])
        #                 break
                
        #         if entries[rowed][4]:
        #             try:
        #                 cost_centered = frappe.get_doc("Cost Center", entries[rowed][4])
        #                 if cost_centered:
        #                     invoice.accounts[i].cost_center = cost_centered.name
        #             except frappe.DoesNotExistError:
        #                 writer.writerow(["Cost Center Not Found", first[0], first[2], entries[rowed][5]])
        #                 break
                    
                    
        #     invoice.custom_autocount_dockey = first[0]
        #     invoice.save()
        #     frappe.db.commit()
        #     count += 1
        #     print(f"Progressing...{count}/{len(grouped_data)}")
        # except Exception as e:
        #     logger.error(f"❌ Failed to update invoice {first[0]}: {e}", exc_info=True)
        #     writer.writerow(["Update Failed", first[0], str(e)])
        #     failed_docs.append(first[0])
        #     failed_rows.append(entries)
        #     continue