from datetime import datetime, timezone
import random
import string
import re
from xml.dom import minidom
import frappe
import xml.etree.ElementTree as ET
from frappe.model.naming import make_autoname
from lhdn_consolidate_item.lhdn_consolidate_item.constants import lhdn_submission_doctype, lhdn_summary_doctype

#Custom XML Tag for digital signed
def custom_xml_tags():
    try: 
        invoice = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" )
        invoice.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
        invoice.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
                
        # Add UBLVersionID
        ubl_version_id = ET.SubElement(invoice, "cbc:UBLVersionID")
        ubl_version_id.text = "2.1"

        return invoice
    except Exception as e:
        frappe.throw("error in xml tags formation:  "+ str(e) )


#This method is fetching sales invoice data
def custom_invoice_data(invoice,invoice_number_list):
    try:
        print("enter in custom consolidate invoice")

        ## Generate a Unique Summary Batch ID
        batch_id = make_autoname("BATCH-.#####")

        ## Use the first Invoice Number from list of consolidate invoice
        consolidate_invoice_doc = frappe.get_doc(lhdn_submission_doctype ,invoice_number_list[0])
                
        cbc_ID = ET.SubElement(invoice, "cbc:ID")   #initialize
        cbc_ID.text = str(consolidate_invoice_doc.name)  # assign

         # Get the current date and time in UTC
        now_utc = datetime.now(timezone.utc)
        issue_date = now_utc.date()
        issue_time = now_utc.time().replace(microsecond=0)  # Remove microseconds for cleaner output

        cbc_IssueDate = ET.SubElement(invoice, "cbc:IssueDate")
        cbc_IssueDate.text = str(issue_date)  #Erp sales invoice  posting_date

        # cbc_IssueDate.text = str(sales_invoice_doc.posting_date)  #Erp sales invoice  posting_date
        print("issue date ",cbc_IssueDate.text)
        # cbc_IssueDate.text = "2024-07-13"

        cbc_IssueTime = ET.SubElement(invoice, "cbc:IssueTime")
        cbc_IssueTime.text = issue_time.isoformat() + 'Z'
        # cbc_IssueTime.text = get_Issue_Time(invoice_number)       #Erp sales invoice  posting_time
        print("issue time",cbc_IssueTime.text)
        # cbc_IssueTime.text = "15:30:00Z"      #Erp sales invoice  posting_time

        # cbc_IssueTime.text = get_Issue_Time(invoice_number)       #Erp sales invoice  posting_time
        return invoice
    except Exception as e:
        frappe.throw("error occured in salesinvoice data"+ str(e) )


def invoice_Typecode_Compliance(invoice,compliance_type):

                    # 01 	Invoice
                    # 02 	Credit Note
                    # 03 	Debit Note
                    # 04 	Refund Note
                    # 11 	Self-billed Invoice
                    # 12 	Self-billed Credit Note
                    # 13 	Self-billed Debit Note
                    # 14 	Self-billed Refund Note
            try:                         
                # cbc_InvoiceTypeCode.set("listVersionID", "1.0")  # Current e-Invoice version

                # cbc_InvoiceTypeCode.set("name", "0200000")
                # cbc_InvoiceTypeCode.text = "388"
                # return invoice



                print("list code")
        

                cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")

                if compliance_type == "1":  # Invoice
                    cbc_InvoiceTypeCode.text = "01"
                elif compliance_type == "2":  # Credit Note
                    cbc_InvoiceTypeCode.text = "02"
                elif compliance_type == "3":  # Debit Note
                    cbc_InvoiceTypeCode.text = "03"
                elif compliance_type == "4":  # Refund Note
                    cbc_InvoiceTypeCode.text = "04"
                elif compliance_type == "11":  # Self-billed Invoice
                    cbc_InvoiceTypeCode.text = "11"
                elif compliance_type == "12":  # Self-billed Credit Note
                    cbc_InvoiceTypeCode.text = "12"
                elif compliance_type == "13":  # Self-billed Debit Note
                    cbc_InvoiceTypeCode.text = "13"
                elif compliance_type == "14":  # Self-billed Refund Note
                    cbc_InvoiceTypeCode.text = "14"

                cbc_InvoiceTypeCode.set("listVersionID", "1.0")  # Current e-Invoice version
                        
                return invoice
                
            except Exception as e:
                    frappe.throw("error occured in Compliance typecode"+ str(e) )

def doc_Reference(invoice,consolidate_invoice_doc):
            try:
                cbc_DocumentCurrencyCode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
                cbc_DocumentCurrencyCode.text = consolidate_invoice_doc.currency
                
                cbc_TaxCurrencyCode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
                cbc_TaxCurrencyCode.text = "MYR"  # MYR is as LHDN requires tax amount in MYR
                
                return invoice  
            except Exception as e:
                    frappe.throw("Error occured in  reference doc" + str(e) )


def company_Data(invoice,consolidate_invoice_doc): #supplier data
            try:
                company_doc = frappe.get_doc("Company", consolidate_invoice_doc.company)


                address_list = frappe.get_list(
                    "Address", 
                    filters={"is_your_company_address": "1", "name": consolidate_invoice_doc.company_address_name}, 
                    fields=["address_line1", "address_line2", "city", "pincode", "state","custom_state_codes", "custom_country_code"]
                )


                if len(address_list) == 0:
                    frappe.throw("LHDN requires proper address. Please add your company address in address master")
                
                #Supplier
                cac_AccountingSupplierParty = ET.SubElement(invoice, "cac:AccountingSupplierParty")
                cac_Party_1 = ET.SubElement(cac_AccountingSupplierParty, "cac:Party")


                # Supplier’s Malaysia Standard Industrial Classification (MSIC) Code
                #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cbc:IndustryClassificationCode
                cbc_IndustryClassificationCode = ET.SubElement(cac_Party_1, "cbc:IndustryClassificationCode")
                cbc_IndustryClassificationCode.text = company_doc.custom_msic_codes
                cbc_IndustryClassificationCode.set("name", company_doc.custom_misc_description)


                # Supplier’s TIN
                #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’TIN’]
                cac_PartyIdentification = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                cbc_ID_2 = ET.SubElement(cac_PartyIdentification, "cbc:ID")
                cbc_ID_2.set("schemeID", "TIN")
                cbc_ID_2.text = str(company_doc.tax_id )


                #BRN    
                # Supplier’s Registration / Identification Number / Passport Number
                supplier_id_type = company_doc.custom_registration_type  # Example field to determine the type of ID
                supplier_id_number = company_doc.company_registration  # Example field for the ID number
                cac_PartyIdentification_1 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                cbc_ID_Identification = ET.SubElement(cac_PartyIdentification_1, "cbc:ID")
                if supplier_id_type == 'BRN':
                    cbc_ID_Identification.set("schemeID", "BRN")
                elif supplier_id_type == 'NRIC':
                    cbc_ID_Identification.set("schemeID", "NRIC")
                elif supplier_id_type == 'PASSPORT':
                    cbc_ID_Identification.set("schemeID", "PASSPORT")
                elif supplier_id_type == 'ARMY':
                    cbc_ID_Identification.set("schemeID", "ARMY")
                cbc_ID_Identification.text = str(supplier_id_number)

                # Supplier’s SST Registration Number
                #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’SST’]
                if company_doc.custom_sst_registration_no:
                    cac_PartyIdentification_3 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                    cbc_ID_SST = ET.SubElement(cac_PartyIdentification_3, "cbc:ID")
                    cbc_ID_SST.set("schemeID", "SST")
                    cbc_ID_SST.text = company_doc.custom_sst_registration_no
                else:
                    cac_PartyIdentification_3 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                    cbc_ID_SST = ET.SubElement(cac_PartyIdentification_3, "cbc:ID")
                    cbc_ID_SST.set("schemeID", "SST")
                    cbc_ID_SST.text = "NA"

                # Supplier’s Tourism Tax Registration Number
                #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’TTX’]
                if company_doc.custom_tourism_tax_registration:
                    cac_PartyIdentification_4 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                    cbc_ID_TTX = ET.SubElement(cac_PartyIdentification_4, "cbc:ID")
                    cbc_ID_TTX.set("schemeID", "TTX")
                    cbc_ID_TTX.text = company_doc.custom_tourism_tax_registration
                else:
                    cac_PartyIdentification_4 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                    cbc_ID_TTX = ET.SubElement(cac_PartyIdentification_4, "cbc:ID")
                    cbc_ID_TTX.set("schemeID", "TTX")
                    cbc_ID_TTX.text = "NA"



                                # Supplier’s Address
                #. / cac:Party / cac:PostalAddress / cac:AddressLine / cbc:Line
                for address in address_list:
                    cac_PostalAddress = ET.SubElement(cac_Party_1, "cac:PostalAddress")

                    country_3code = frappe.db.get_value('ISO Country Code', {'country_code_a2':address.custom_country_code}, ['country_code_a3'])

                    #. / cac:Party / cac:PostalAddress / cbc:CityName
                    cbc_CityName = ET.SubElement(cac_PostalAddress, "cbc:CityName")
                    cbc_CityName.text = address.city 
                    print("City",cbc_CityName.text)


                    #Postal Zone
                    cbc_PostalZone = ET.SubElement(cac_PostalAddress, "cbc:PostalZone")
                    cbc_PostalZone.text = address.pincode 
                    print("postal zone",cbc_PostalZone.text)



                    # cac:Party / cac:PostalAddress / cbc:CountrySubentityCode
                    cbc_CountrySubentity = ET.SubElement(cac_PostalAddress, "cbc:CountrySubentityCode")
                    cbc_CountrySubentity.text = address.custom_state_codes 
                    # cbc_CountrySubentity.text = "14"
                    print("CountrySubentityCode",cbc_CountrySubentity.text)


                    

                    #Address Line
                    cac_AddressLine_0 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
                    cbc_Line_0 = ET.SubElement(cac_AddressLine_0, "cbc:Line")
                    cbc_Line_0.text = address.address_line1 

                    if address.address_line2:
                        cac_AddressLine_1 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
                        cbc_Line_1 = ET.SubElement(cac_AddressLine_1, "cbc:Line")
                        cbc_Line_1.text = address.address_line2

                    break
                    
                    
                # / cac:Party / cac:PostalAddress / cac:Country / cbc:IdentificationCode [@listID=’ISO3166-1’] [@listAgencyID=’6’]
                cac_Country = ET.SubElement(cac_PostalAddress, "cac:Country")
                cbc_IdentificationCode = ET.SubElement(cac_Country, "cbc:IdentificationCode", {
                    "listID": "ISO3166-1",
                    "listAgencyID": "6"
                })
                # cbc_IdentificationCode = ET.SubElement(cac_Country, "cbc:IdentificationCode")
                cbc_IdentificationCode.text = country_3code if country_3code else "MYS"


                # Supplier’s Name
                #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyLegalEntity / cbc:RegistrationName

                cac_PartyLegalEntity = ET.SubElement(cac_Party_1, "cac:PartyLegalEntity")
                cbc_RegistrationName = ET.SubElement(cac_PartyLegalEntity, "cbc:RegistrationName")
                cbc_RegistrationName.text = consolidate_invoice_doc.company     
                
                # Supplier’s Contact Number
                
                cac_Contact = ET.SubElement(cac_Party_1, "cac:Contact")
                cbc_Telephone = ET.SubElement(cac_Contact, "cbc:Telephone")
                cbc_Telephone.text = company_doc.custom_contact_no

                # Supplier’s e-mail
                if company_doc.email:
                    #cac_Contact = ET.SubElement(cac_Party_1, "cac:Contact")
                    cbc_ElectronicMail = ET.SubElement(cac_Contact, "cbc:ElectronicMail")
                    cbc_ElectronicMail.text = company_doc.email

                return invoice
            except Exception as e:
                    frappe.throw("error occured in company data"+ str(e) )

#Customer
def consolidate_customer_Data(invoice):
            try:
                # In consolidate invoices, customer data is not needed to supply. All will filled with NA value
                # TIN value will be default to EI00000000010
                # customer type id will default to BRN
                
                # customer_doc= frappe.get_doc("Customer",consolidate_invoice_doc.customer)


                cac_AccountingCustomerParty = ET.SubElement(invoice, "cac:AccountingCustomerParty")
                cac_Party_2 = ET.SubElement(cac_AccountingCustomerParty, "cac:Party")


                 #Customer's TIN
                #/ ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’TIN’]
                cac_PartyIdentification_1 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
                cbc_ID_4 = ET.SubElement(cac_PartyIdentification_1, "cbc:ID")
                cbc_ID_4.set("schemeID", "TIN")
                # Default TIN value for consolidate item
                cbc_ID_4.text = "EI00000000010"


                #BRN
                customer_id_type = "BRN"  # Example field to determine the type of ID
                customer_id_number = "NA"  # Example field for the ID number

                cac_PartyIdentification_2 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
                cbc_ID_Identification = ET.SubElement(cac_PartyIdentification_2, "cbc:ID")

                
                if customer_id_type == 'BRN':
                    cbc_ID_Identification.set("schemeID", "BRN")
                elif customer_id_type == 'NRIC':
                    cbc_ID_Identification.set("schemeID", "NRIC")
                elif customer_id_type == 'PASSPORT':
                    cbc_ID_Identification.set("schemeID", "PASSPORT")
                elif customer_id_type == 'ARMY':
                    cbc_ID_Identification.set("schemeID", "ARMY")             
                cbc_ID_Identification.text = customer_id_number

                # Customer’s SST Registration Number
                #/ ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’SST’]
                cac_PartyIdentification_4 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
                cbc_ID_SST_1 = ET.SubElement(cac_PartyIdentification_4, "cbc:ID")
                cbc_ID_SST_1.set("schemeID", "SST")
                cbc_ID_SST_1.text = "NA"

                #Buyer's Address
                # address = frappe.get_doc("Address", customer_doc.customer_primary_address) 

                country_3code = frappe.db.get_value('ISO Country Code', {'country_code_a2': 'MYS'}, ['country_code_a3'])

                #. / cac:Party / cac:PostalAddress / cac:AddressLine / cbc:Line
                cac_PostalAddress = ET.SubElement(cac_Party_2, "cac:PostalAddress")

                #. / cac:Party / cac:PostalAddress / cbc:CityName
                cbc_CityName = ET.SubElement(cac_PostalAddress, "cbc:CityName")
                cbc_CityName.text = "NA"

                cbc_PostalZone = ET.SubElement(cac_PostalAddress, "cbc:PostalZone")
                cbc_PostalZone.text = "NA"

                cbc_CountrySubentity = ET.SubElement(cac_PostalAddress, "cbc:CountrySubentityCode")
                ## Default value for consolidate invoices, the country code will 14
                ## 14 – Wilayah Persekutuan Kuala Lumpur
                cbc_CountrySubentity.text = "14"

                cac_AddressLine_0 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
                cbc_Line_0 = ET.SubElement(cac_AddressLine_0, "cbc:Line")
                cbc_Line_0.text = "NA"

                

                #. / cac:Party / cac:PostalAddress / cac:Country / cbc:IdentificationCode [@listID=’ISO3166-1’] [@listAgencyID=’6’]
                cac_Country = ET.SubElement(cac_PostalAddress, "cac:Country")
                # cbc_IdentificationCode = ET.SubElement(cac_Country, "cbc:IdentificationCode")
                cbc_IdentificationCode = ET.SubElement(cac_Country, "cbc:IdentificationCode", {
                    "listID": "ISO3166-1",
                    "listAgencyID": "6"
                })
                cbc_IdentificationCode.text = country_3code if country_3code else "MYS"
 
                #Customer's Name
                #/ ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyLegalEntity / cbc:RegistrationName
                cac_PartyLegalEntity_1 = ET.SubElement(cac_Party_2, "cac:PartyLegalEntity")
                cbc_RegistrationName_1 = ET.SubElement(cac_PartyLegalEntity_1, "cbc:RegistrationName")
                cbc_RegistrationName_1.text = "NA"


                # Customer’s Contact Number
                print("customer contact")
                cac_Contact = ET.SubElement(cac_Party_2, "cac:Contact")
                cbc_Telephone = ET.SubElement(cac_Contact, "cbc:Telephone")

                #cbc_Telephone.text = customer_doc.mobile_no
                cbc_Telephone.text = "NA"
                
                return invoice
            except Exception as e:
                    frappe.throw("error occured in customer data"+ str(e) )

def tax_Data(invoice,json_invoice_list,consolidate_invoice_doc,total_local_tax, total_taxable_amount, total_final_amount):
    try:
                
                # Currently front end only support MYR
                #for foreign currency
                # if consolidate_invoice_doc.currency != "MYR":
                #     conversion_rate = frappe.get_list("Currency Exchange",  filters={"from_currency": consolidate_invoice_doc.currency, "to_currency": "MYR"}, fields=["exchange_rate"])


                #     cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
                #     cbc_TaxAmount_MYR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
                #     cbc_TaxAmount_MYR.set("currencyID", "MYR") # MYR is as lhdn requires tax amount in lhdn
                #     tax_amount_without_retention_myr =  round(conversion_rate * abs(get_tax_total_from_items(consolidate_invoice_doc)),2)
                #     cbc_TaxAmount_MYR.text = str(round( tax_amount_without_retention_myr,2))     # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
                # #end for foreign currency
                
                
                # Constructing Tax Data Body

                #for MYR currency
                if consolidate_invoice_doc.currency == "MYR":
                    cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
                    
                    cbc_TaxAmount_MYR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
                    cbc_TaxAmount_MYR.set("currencyID", "MYR") # MYR is as lhdn requires tax amount in MYR
                    tax_amount_without_retention_myr = str(total_local_tax)
                    cbc_TaxAmount_MYR.text = str(tax_amount_without_retention_myr)     # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
                #end for MYR currency
                
                #Total Tax Amount Per Tax Type
                cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")

                #Amount Exempted from Tax(Invoice level tax exemption)
                cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
                cbc_TaxableAmount.set("currencyID", consolidate_invoice_doc.currency)
                cbc_TaxableAmount.text = str(total_taxable_amount)

                cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
                cbc_TaxAmount_2.set("currencyID", consolidate_invoice_doc.currency)
                cbc_TaxAmount_2.text = str(total_local_tax)

                cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
                cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")
                # By Default for consolidate Tax Type will be 06
                cbc_ID_8.text = "06"
                cac_TaxScheme = ET.SubElement(cac_TaxCategory_1, "cac:TaxScheme")
                cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
                cbc_TaxSchemeID.set("schemeID", "UN/ECE 5153")
                cbc_TaxSchemeID.set("schemeAgencyID", "6")
                cbc_TaxSchemeID.text = "OTH"     

                #Total Excluding Tax
                cac_LegalMonetaryTotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
                cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
                cbc_TaxExclusiveAmount.set("currencyID", consolidate_invoice_doc.currency)
                cbc_TaxExclusiveAmount.text = str(total_taxable_amount)

        
                #/ ubl:Invoice / cac:LegalMonetaryTotal / cbc:TaxInclusiveAmount [@currencyID=’MYR’]
                #Total Including Tax
                cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
                cbc_TaxInclusiveAmount.set("currencyID", consolidate_invoice_doc.currency)
                cbc_TaxInclusiveAmount.text = str(total_final_amount)


                #Total Payable Amount
                cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
                cbc_PayableAmount.set("currencyID", consolidate_invoice_doc.currency)
                cbc_PayableAmount.text = str(total_final_amount)

        
                return invoice
             
    except Exception as e:
                    frappe.throw("error occured in tax data"+ str(e) )  

def item_data(invoice, json_invoice_list):
    try:
        consolidate_item_list = frappe.get_list(lhdn_submission_doctype, filters=[["name", "in", json_invoice_list]], fields=["name", "tax", "sub_total_ex", "total","tax_percentage", "currency"])
        running_number = 1

        for item in consolidate_item_list: 

            # Create InvoiceLine element
            cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")

            #ID
            cbc_ID_10 = ET.SubElement(cac_InvoiceLine, "cbc:ID")
            cbc_ID_10.text = str(running_number) 

            # Quantity 
            cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity")
            cbc_InvoicedQuantity.set("unitCode","C62")
            # In consolidate invoice item quantity is always one
            cbc_InvoicedQuantity.text = "1"  

            # Total Excluding Tax
            cbc_LineExtensionAmount_1 = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount")   #100
            cbc_LineExtensionAmount_1.set("currencyID", item.currency)
            cbc_LineExtensionAmount_1.text = str(item.sub_total_ex)     #including only charges or discount and exclsing tax

            # Tax Type  / ubl:Invoice / cac:InvoiceLine / cac:TaxTotal / cac:TaxSubtotal / cac:TaxCategory / cbc:ID 
            cac_TaxTotal = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")

            ## Tax Amount   / ubl:Invoice / cac:InvoiceLine / cac:TaxTotal / cbc:TaxAmount [@currencyID=’MYR’]
            cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_3.set("currencyID", item.currency)   #Tax Amount of each item
            cbc_TaxAmount_3.text = str(item.tax)  

            #TaxSubtotal
            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")

            #Amount Exempted from Tax(Invoice level tax exemption)
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
            cbc_TaxableAmount.set("currencyID", item.currency)
            cbc_TaxableAmount.text = str(item.sub_total_ex)   # 100  # #including only charges or discount and exclsing tax

            cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
            cbc_TaxAmount_2.set("currencyID", item.currency)                
            cbc_TaxAmount_2.text = "0"

                  
            cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")            
                
            cbc_TaxCategoryID = ET.SubElement(cac_TaxCategory, "cbc:ID")
            # LHDN Tax Code by default is 06
            cbc_TaxCategoryID.text = "06"

            # Tax Rate in percentage
            cbc_TaxRatePercent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
            cbc_TaxRatePercent.text = str(abs(round(float(item.tax_percentage)/100, 2)))

            cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
            cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
            cbc_TaxSchemeID.set("schemeID", "UN/ECE 5153")
            cbc_TaxSchemeID.set("schemeAgencyID", "6")
            cbc_TaxSchemeID.text = "OTH"

            # Item
            cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
           
            # Description of Product or Service
            cbc_Description = ET.SubElement(cac_Item, "cbc:Description")
            cbc_Description.text = str(item.name)

            # Origin Country
            cac_origin_country = ET.SubElement(cac_Item, "cac:OriginCountry")
            cbc_identification_code = ET.SubElement(cac_origin_country, "cbc:IdentificationCode")
            cbc_identification_code.text = "MYS" ## Default Malaysia Country Code

            #Classification
            cac_CommodityClassification_1 = ET.SubElement(cac_Item, "cac:CommodityClassification")
            cbc_ItemClassificationCode_1 = ET.SubElement(cac_CommodityClassification_1, "cbc:ItemClassificationCode")
            cbc_ItemClassificationCode_1.set("listID", "PTC")

            cac_CommodityClassification = ET.SubElement(cac_Item, "cac:CommodityClassification")
            cbc_ItemClassificationCode = ET.SubElement(cac_CommodityClassification, "cbc:ItemClassificationCode")
            cbc_ItemClassificationCode.set("listID", "CLASS")
            ## Default Consolidate item classification code
            cbc_ItemClassificationCode.text = "004"

            # Unit Price
            cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")            
            cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount")
            cbc_PriceAmount.set("currencyID", item.currency)
            ## Default unit price will always be zero in consolidate item
            cbc_PriceAmount.text = "0"


            # Subtotal
            cac_ItemPriceExtension = ET.SubElement(cac_InvoiceLine, "cac:ItemPriceExtension")
            cbc_Amount = ET.SubElement(cac_ItemPriceExtension, "cbc:Amount")
            cbc_Amount.set("currencyID", item.currency)
            cbc_Amount.text = str(item.sub_total_ex)

            running_number += 1

        return invoice
    except Exception as e:
        frappe.throw("Error occurred in item data: " + str(e))

def xml_structuring(invoice,batch_id,doc_type,document_type):
            try:
                xml_declaration = "<?xml version='1.0' encoding='UTF-8'?>\n"
                tree = ET.ElementTree(invoice)
                with open(frappe.local.site + "/private/files/xml_files.xml", 'wb') as file:
                    tree.write(file, encoding='utf-8', xml_declaration=True)
                with open(frappe.local.site + "/private/files/xml_files.xml", 'r') as file:
                    xml_string = file.read()
                xml_dom = minidom.parseString(xml_string)
                pretty_xml_string = xml_dom.toprettyxml(indent="  ")   # created xml into formatted xml form 
                with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'w') as file:
                    file.write(pretty_xml_string)
                          # Attach the getting xml for each invoice
                try:
                    if frappe.db.exists("File",{ "attached_to_name": batch_id, "attached_to_doctype": doc_type }):
                        frappe.db.delete("File",{ "attached_to_name":batch_id, "attached_to_doctype": doc_type })
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
                
                try:
                    fileX = frappe.get_doc(
                        {   "doctype": "File",        
                            "file_type": "xml",  
                            "file_name":  "E-invoice-" + batch_id + ".xml",
                            "attached_to_doctype": doc_type,
                            "attached_to_name":batch_id, 
                            "content": pretty_xml_string,
                            "is_private": 1,})
                    fileX.save()
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
                
                try:
                    frappe.db.get_value('File', {'attached_to_name':batch_id, 'attached_to_doctype': doc_type}, ['file_name'])
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
            except Exception as e:
                    frappe.throw("Error occured in XML structuring and attach. Please contact your system administrator"+ str(e) )
                
def calculate_consolidate_amount(invoice_number_list):
     
    invoice_item_list = frappe.get_list(lhdn_submission_doctype, filters=[["name", "in", invoice_number_list]], fields=["name", "tax", "sub_total_ex", "total"])

    total_tax = 0.0;
    total_taxable_amount = 0.0;
    total_final_amount = 0.0;

    for single_item in invoice_item_list:
        total_tax += single_item.tax
        total_taxable_amount += single_item.sub_total_ex
        total_final_amount += single_item.total

    total_tax  = round(abs(total_tax), 2)
    total_taxable_amount = round(abs(total_taxable_amount), 2)
    total_final_amount = round(abs(total_final_amount), 2)

    return total_tax, total_taxable_amount, total_final_amount

def generate_batch_id(prefix="LHDN"):
    timestamp = datetime.now().strftime("%Y%m%d")  # Format: YYYYMMDD
    last_number = 0

    ## Using Database query to arrange data order by creation DESC
    last_entry = frappe.db.get_value(lhdn_summary_doctype, 
                                       {"batch_id": ["like", f"{prefix}-{timestamp}-%"]}, 
                                       "batch_id", 
                                       order_by="creation DESC")
    
    if last_entry:
        match = re.search(r"-(\d{4})$", last_entry)
        if match:
            last_number = int(match.group(1)) + 1
        else: 
            last_number = 1
    else:
        last_number =1

    running_number = f"{last_number:04d}" ## Running number which is always start with 1 if there is no existing data and 4 digit
    batch_id = f"{prefix}-{timestamp}-{running_number}"

    return batch_id




