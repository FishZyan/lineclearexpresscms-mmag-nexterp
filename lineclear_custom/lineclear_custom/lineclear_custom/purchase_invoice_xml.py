import frappe
import os
import xml.etree.ElementTree as ET
from lxml import etree
import xml.dom.minidom as minidom
import uuid 
from frappe.utils import now
import re
from lxml import etree
from frappe.utils.data import  get_time
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import json
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

# This method is for digital signature
def xml_tags():
    try: 
        purchase_invoice = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" )
        purchase_invoice.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
        purchase_invoice.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
                
        # Add UBLVersionID
        ubl_version_id = ET.SubElement(purchase_invoice, "cbc:UBLVersionID")
        ubl_version_id.text = "2.1"
               
        return purchase_invoice
    except Exception as e:
        frappe.throw("error in xml tags formation:  "+ str(e) )

def purchase_invoice_data(purchase_invoice, invoice_number):
    try:
        purchase_invoice_doc = frappe.get_doc('Purchase Invoice' ,invoice_number)
                
        cbc_ID = ET.SubElement(purchase_invoice, "cbc:ID")   #initialize
        cbc_ID.text = str(purchase_invoice_doc.name)  # assign

         # Get the current date and time in UTC
        now_utc = datetime.now(timezone.utc)
        issue_date = now_utc.date()
        issue_time = now_utc.time().replace(microsecond=0)  # Remove microseconds for cleaner output

        cbc_IssueDate = ET.SubElement(purchase_invoice, "cbc:IssueDate")
        cbc_IssueDate.text = str(issue_date)  #Erp Journal Entry  posting_date

        cbc_IssueTime = ET.SubElement(purchase_invoice, "cbc:IssueTime")
        cbc_IssueTime.text = issue_time.isoformat() + 'Z'
                
        return purchase_invoice ,purchase_invoice_doc
    except Exception as e:
        frappe.throw("error occured in purchase_invoice_data"+ str(e) )
        
def doc_Reference(purchase_invoice , purchase_invoice_doc):
    try:
        cbc_DocumentCurrencyCode = ET.SubElement(purchase_invoice, "cbc:DocumentCurrencyCode")
        cbc_DocumentCurrencyCode.text = purchase_invoice_doc.currency

        cbc_TaxCurrencyCode = ET.SubElement(purchase_invoice, "cbc:TaxCurrencyCode")
        cbc_TaxCurrencyCode.text = "MYR"  # MYR is as LHDN requires tax amount in MYR

        return purchase_invoice  
    except Exception as e:
        frappe.throw("Error occured in  reference doc" + str(e) )
        
def company_Data(purchase_invoice, purchase_invoice_doc): #supplier data
    try:
        supplier_doc = frappe.get_doc("Supplier", purchase_invoice_doc.supplier)

        # address_name = frappe.get_value("Dynamic Link", {
        #     "link_doctype": "Supplier",
        #     "link_name": purchase_invoice_doc.supplier,
        #     "parenttype": "Address"
        # }, "parent")
        
        # if address_name is None:
        #     frappe.throw("LHDN requires proper address. Please add your supplier address in Supplier Primary Address")

        if(not supplier_doc.custom_lhdn_enable_control):
            frappe.throw("LHDN requires proper Tax ID. " \
            "Please fill in the tin number in Supplier")

        if len(supplier_doc.supplier_primary_address) == 0:
            frappe.throw("LHDN requires proper address. Please add your supplier address in Supplier Primary Address")
        
        address_doc = frappe.get_doc("Address", supplier_doc.supplier_primary_address)
        if not address_doc:
            frappe.throw("LHDN requires proper address. Please add your company address in address master")

        #Supplier
        cac_AccountingSupplierParty = ET.SubElement(purchase_invoice, "cac:AccountingSupplierParty")
        cac_Party_1 = ET.SubElement(cac_AccountingSupplierParty, "cac:Party")

        # Supplier’s Malaysia Standard Industrial Classification (MSIC) Code
        #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cbc:IndustryClassificationCode
        cbc_IndustryClassificationCode = ET.SubElement(cac_Party_1, "cbc:IndustryClassificationCode")
        cbc_IndustryClassificationCode.text = supplier_doc.custom_misc_code
        cbc_IndustryClassificationCode.set("name", supplier_doc.custom_misc_descriptions)

        # Supplier’s TIN
        #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’TIN’]
        cac_PartyIdentification = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
        cbc_ID_2 = ET.SubElement(cac_PartyIdentification, "cbc:ID")
        cbc_ID_2.set("schemeID", "TIN")
        cbc_ID_2.text = str(supplier_doc.custom_lhdn_tax_id )
                
        #BRN    
        # Supplier’s Registration / Identification Number / Passport Number
        supplier_id_type = supplier_doc.custom_registration_type  # Example field to determine the type of ID
        supplier_id_number = supplier_doc.custom_registration_no  # Example field for the ID number
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
        if supplier_doc.custom_sst_registration_no:
            cac_PartyIdentification_3 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
            cbc_ID_SST = ET.SubElement(cac_PartyIdentification_3, "cbc:ID")
            cbc_ID_SST.set("schemeID", "SST")
            cbc_ID_SST.text = supplier_doc.custom_sst_registration_no
        else:
            cac_PartyIdentification_3 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
            cbc_ID_SST = ET.SubElement(cac_PartyIdentification_3, "cbc:ID")
            cbc_ID_SST.set("schemeID", "SST")
            cbc_ID_SST.text = "NA"

        # Supplier’s Tourism Tax Registration Number
        #/ ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’TTX’]
        
        if supplier_doc.custom_tourism_tax_registration:
            cac_PartyIdentification_4 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
            cbc_ID_TTX = ET.SubElement(cac_PartyIdentification_4, "cbc:ID")
            cbc_ID_TTX.set("schemeID", "TTX")
            cbc_ID_TTX.text = supplier_doc.custom_tourism_tax_registration
        else:
            cac_PartyIdentification_4 = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
            cbc_ID_TTX = ET.SubElement(cac_PartyIdentification_4, "cbc:ID")
            cbc_ID_TTX.set("schemeID", "TTX")
            cbc_ID_TTX.text = "NA"

        # Supplier’s Address
        #. / cac:Party / cac:PostalAddress / cac:AddressLine / cbc:Line
        cac_PostalAddress = ET.SubElement(cac_Party_1, "cac:PostalAddress")

        country_3code = frappe.db.get_value('ISO Country Code', {'country_code_a2':address_doc.custom_country_code}, ['country_code_a3'])

        #. / cac:Party / cac:PostalAddress / cbc:CityName
        cbc_CityName = ET.SubElement(cac_PostalAddress, "cbc:CityName")
        cbc_CityName.text = address_doc.city 

        #Postal Zone
        cbc_PostalZone = ET.SubElement(cac_PostalAddress, "cbc:PostalZone")
        cbc_PostalZone.text = address_doc.pincode 

        # cac:Party / cac:PostalAddress / cbc:CountrySubentityCode
        cbc_CountrySubentity = ET.SubElement(cac_PostalAddress, "cbc:CountrySubentityCode")
        cbc_CountrySubentity.text = address_doc.custom_state_codes 
        # cbc_CountrySubentity.text = "14"

        #Address Line
        cac_AddressLine_0 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
        cbc_Line_0 = ET.SubElement(cac_AddressLine_0, "cbc:Line")
        if address_doc.unit_number:
            cbc_Line_0.text = address_doc.unit_number + "," + address_doc.address_line1 
        else:
            cbc_Line_0.text = address_doc.address_line1

        if address_doc.address_line2:
            cac_AddressLine_1 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
            cbc_Line_1 = ET.SubElement(cac_AddressLine_1, "cbc:Line")
            cbc_Line_1.text = address_doc.address_line2
                    
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
        cbc_RegistrationName.text = supplier_doc.supplier_name

        # The mapping for this field will depend on the field type which can be one of the following options:
        # / ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’NRIC’]
        # OR
        # / ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’BRN’]
        # OR
        # / ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’PASSPORT’]
        # OR
        # / ubl:Invoice / cac:AccountingSupplierParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’ARMY’]
        # Supplier’s Contact Number
        if not address_doc.phone:
            frappe.throw("LHDN requires proper contact number. Please add your supplier contact number in Supplier Primary Address")
        cac_Contact = ET.SubElement(cac_Party_1, "cac:Contact")
        cbc_Telephone = ET.SubElement(cac_Contact, "cbc:Telephone")
        cbc_Telephone.text = address_doc.phone

        # Supplier’s e-mail
        if supplier_doc.custom_email_address:
            #cac_Contact = ET.SubElement(cac_Party_1, "cac:Contact")
            cbc_ElectronicMail = ET.SubElement(cac_Contact, "cbc:ElectronicMail")
            cbc_ElectronicMail.text = supplier_doc.custom_email_address
               
        return purchase_invoice
    except Exception as e:
        frappe.throw("Seller data")
        
def customer_Data(purchase_invoice, purchase_invoice_doc):
    try:
        company_doc = frappe.get_doc("Company",purchase_invoice_doc.company)

        cac_AccountingCustomerParty = ET.SubElement(purchase_invoice, "cac:AccountingCustomerParty")
        cac_Party_2 = ET.SubElement(cac_AccountingCustomerParty, "cac:Party")

        #Customer's TIN
        #/ ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’TIN’]
        cac_PartyIdentification_1 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
        cbc_ID_4 = ET.SubElement(cac_PartyIdentification_1, "cbc:ID")
        cbc_ID_4.set("schemeID", "TIN")
        
        cbc_ID_4.text = company_doc.tax_id

        #BRN
        if(not company_doc.custom_registration_type):
            frappe.throw("LHDN requires proper Registration Type." \
            "Please fill in the Registration Type in customer")
        if(not company_doc.company_registration):
            frappe.throw("LHDN requires proper Registration No." \
            "Please fill in the Registration No in customer")
        customer_id_type = company_doc.custom_registration_type  # Example field to determine the type of ID
        customer_id_number = company_doc.company_registration  # Example field for the ID number

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
        if company_doc.custom_sst_registration_no:
            cac_PartyIdentification_3 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
            cbc_ID_SST = ET.SubElement(cac_PartyIdentification_3, "cbc:ID")
            cbc_ID_SST.set("schemeID", "SST")
            cbc_ID_SST.text = company_doc.custom_sst_registration_no
        else:
            cac_PartyIdentification_4 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
            cbc_ID_SST_1 = ET.SubElement(cac_PartyIdentification_4, "cbc:ID")
            cbc_ID_SST_1.set("schemeID", "SST")
            cbc_ID_SST_1.text = "NA"
        
        # Customer's Registration / Identification Number / Passport Number 
        #/ ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’NRIC’]
        # OR
        # / ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’BRN’]
        # OR
        # / ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’PASSPORT’]
        # OR
        # / ubl:Invoice / cac:AccountingCustomerParty / cac:Party / cac:PartyIdentification / cbc:ID [@schemeID=’ARMY’]
                
        #Buyer's Address
        if int(frappe.__version__.split('.')[0]) == 13:
            address = frappe.get_doc("Address", purchase_invoice_doc.customer_address)    #check
        else:
            address_name = frappe.get_value("Dynamic Link", {
                "link_doctype": "Company",
                "link_name": purchase_invoice_doc.company,
                "parenttype": "Address"
            }, "parent")
            address = frappe.get_doc("Address", address_name) 

        country_3code = frappe.db.get_value('ISO Country Code', {'country_code_a2':address.custom_country_code}, ['country_code_a3'])

        #. / cac:Party / cac:PostalAddress / cac:AddressLine / cbc:Line
        cac_PostalAddress = ET.SubElement(cac_Party_2, "cac:PostalAddress")

        #. / cac:Party / cac:PostalAddress / cbc:CityName
        cbc_CityName = ET.SubElement(cac_PostalAddress, "cbc:CityName")
        cbc_CityName.text = address.city 

        cbc_PostalZone = ET.SubElement(cac_PostalAddress, "cbc:PostalZone")
        cbc_PostalZone.text = address.pincode

        cbc_CountrySubentity = ET.SubElement(cac_PostalAddress, "cbc:CountrySubentityCode")
        cbc_CountrySubentity.text = address.custom_state_codes 


        cac_AddressLine_0 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
        cbc_Line_0 = ET.SubElement(cac_AddressLine_0, "cbc:Line")
        cbc_Line_0.text = address.address_line1 if address.address_line1 else "NA"

        if address.address_line2:
            cac_AddressLine_1 = ET.SubElement(cac_PostalAddress, "cac:AddressLine")
            cbc_Line_1 = ET.SubElement(cac_AddressLine_1, "cbc:Line")
            cbc_Line_1.text = address.address_line2

        
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
        cbc_RegistrationName_1.text = purchase_invoice_doc.company

        # Customer’s Contact Number
        # if customer_doc.customer_primary_contact:
        print("customer contact")
        cac_Contact = ET.SubElement(cac_Party_2, "cac:Contact")
        cbc_Telephone = ET.SubElement(cac_Contact, "cbc:Telephone")
        cbc_Telephone.text = company_doc.custom_contact_no
                
        if company_doc.email:
            #cac_Contact = ET.SubElement(cac_Party_2, "cac:Contact")
            cbc_ElectronicMail = ET.SubElement(cac_Contact, "cbc:ElectronicMail")
            cbc_ElectronicMail.text = company_doc.email

        return purchase_invoice
    except Exception as e:
        frappe.throw("Buyer data")
        
def tax_Data(purchase_invoice, purchase_invoice_doc):
    try:
        ##########My code start##########
        #/ ubl:Invoice / cac:TaxTotal / cbc:TaxAmount [@currencyID=’MYR’]
        #Total Tax Amount

        #for foreign currency
        if purchase_invoice_doc.currency != "MYR":
            frappe.throw("Currency other than MYR is not supported for now")
            # cac_TaxTotal = ET.SubElement(journal_entry, "cac:TaxTotal")
            # cbc_TaxAmount_MYR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            # cbc_TaxAmount_MYR.set("currencyID", "MYR") # MYR is as lhdn requires tax amount in lhdn
            # tax_amount_without_retention_myr =  round(journal_entry_doc.conversion_rate * abs(get_tax_total_from_items(journal_entry_doc)),2)
            # cbc_TaxAmount_MYR.text = str(round( tax_amount_without_retention_myr,2))     # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
        #end for foreign currency
                
                
        #for MYR currency
        if purchase_invoice_doc.currency == "MYR":
            cac_TaxTotal = ET.SubElement(purchase_invoice, "cac:TaxTotal")
                    
            cbc_TaxAmount_MYR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_MYR.set("currencyID", "MYR") # MYR is as lhdn requires tax amount in MYR
            tax_amount_without_retention_myr =  round(abs(purchase_invoice_doc.total_taxes_and_charges),2)
            cbc_TaxAmount_MYR.text = str(round( tax_amount_without_retention_myr,2))     # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
        #end for MYR currency
                
        # Aggregate tax by type
        tax_by_type = aggregate_tax_by_type(purchase_invoice_doc)

        # Add each tax type to TaxTotal
        for tax_type, tax_data in tax_by_type.items():
                    
            #/ ubl:Invoice / cac:TaxTotal / cac:TaxSubtotal / cbc:TaxAmount [@currencyID=’MYR’]
            #Total Tax Amount Per Tax Type
            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")

            #Amount Exempted from Tax(Invoice level tax exemption)
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
            cbc_TaxableAmount.set("currencyID", purchase_invoice_doc.currency)
            cbc_TaxableAmount.text =str(round(tax_data['taxable_amount'], 2))
            # cbc_TaxableAmount.text =str(abs(round(sales_invoice_doc.base_net_total,2)))

            cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
            cbc_TaxAmount_2.set("currencyID", purchase_invoice_doc.currency)
            cbc_TaxAmount_2.text = str(round(tax_data['tax_amount'], 2))
            # cbc_TaxAmount_2.text = str(round( tax_amount_without_retention_myr,2)) 

            cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
            cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")
        
            if tax_type  == 'E':   #Tax Exemption                        
                cbc_ID_8.text = "E"
                cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReason")
                cbc_TaxExemptionReason.text = tax_data['exemption_description']
            else:
                #Details of Tax Exemption (Invoice level tax exemption)
                # cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
                # cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")
                cbc_ID_8.text = str(tax_type)
                # cbc_ID_8.text = str(sales_invoice_doc.custom_lhdn_tax_type_code)

                # # Tax Rate in percentage
                # cbc_TaxRatePercent = ET.SubElement(cac_TaxCategory_1, "cbc:Percent")
                # cbc_TaxRatePercent.text =  f"{float(sales_invoice_doc.taxes[0].rate):.2f}" 

            cac_TaxScheme = ET.SubElement(cac_TaxCategory_1, "cac:TaxScheme")
            cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
            cbc_TaxSchemeID.set("schemeID", "UN/ECE 5153")
            cbc_TaxSchemeID.set("schemeAgencyID", "6")
            cbc_TaxSchemeID.text = "OTH"

                
        # / ubl:Invoice / cac:LegalMonetaryTotal / cbc:TaxExclusiveAmount [@currencyID=’MYR’]

        #Total Excluding Tax
        cac_LegalMonetaryTotal = ET.SubElement(purchase_invoice, "cac:LegalMonetaryTotal")
        cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
        cbc_TaxExclusiveAmount.set("currencyID", purchase_invoice_doc.currency)
        cbc_TaxExclusiveAmount.text = str(round(abs(purchase_invoice_doc.net_total),2))

        
        #/ ubl:Invoice / cac:LegalMonetaryTotal / cbc:TaxInclusiveAmount [@currencyID=’MYR’]
        #Total Including Tax
        cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
        cbc_TaxInclusiveAmount.set("currencyID", purchase_invoice_doc.currency)
        tax_amount_without_retention =  round(abs(purchase_invoice_doc.total_taxes_and_charges),2)
        cbc_TaxInclusiveAmount.text = str(round(abs(purchase_invoice_doc.net_total) + abs(tax_amount_without_retention),2))

        #Rounding Adjustment
        cbc_PayableRoundingAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableRoundingAmount")
        cbc_PayableRoundingAmount.set("currencyID", purchase_invoice_doc.currency)
        cbc_PayableRoundingAmount.text = str(purchase_invoice_doc.rounding_adjustment)

        #Total Payable Amount
        cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
        cbc_PayableAmount.set("currencyID", purchase_invoice_doc.currency)
        cbc_PayableAmount.text = str(round(abs(purchase_invoice_doc.net_total) + abs(tax_amount_without_retention) +purchase_invoice_doc.rounding_adjustment,2))
                                                                      
        return purchase_invoice
             
    except Exception as e:
                    frappe.throw("error occured in tax data"+ str(e) )

def item_data(purchase_invoice, purchase_invoice_doc):
    try:
        for single_item in purchase_invoice_doc.items:
            item_tax_percentage = 0

            # Create InvoiceLine element
            cac_InvoiceLine = ET.SubElement(purchase_invoice, "cac:InvoiceLine")
            
            #ID
            cbc_ID_10 = ET.SubElement(cac_InvoiceLine, "cbc:ID")
            cbc_ID_10.text = str(single_item.idx)

            # Quantity 
            cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity")
            # cbc_InvoicedQuantity.set("unitCode", str(single_item.uom))
            cbc_InvoicedQuantity.text = str(abs(single_item.qty))         

            # Total Excluding Tax
            cbc_LineExtensionAmount_1 = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount")   #100
            cbc_LineExtensionAmount_1.set("currencyID", purchase_invoice_doc.currency)
            cbc_LineExtensionAmount_1.text = str(single_item.base_net_amount)    #including only charges or discount and exclsing tax

            # Tax Type  / ubl:Invoice / cac:InvoiceLine / cac:TaxTotal / cac:TaxSubtotal / cac:TaxCategory / cbc:ID 
            cac_TaxTotal = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
           
            if single_item.custom_lhdn_tax_type_code == "E":  # lhdn Tax type  Exempted
                # # Tax Amount   / ubl:Invoice / cac:InvoiceLine / cac:TaxTotal / cbc:TaxAmount [@currencyID=’MYR’]
                cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
                cbc_TaxAmount_3.set("currencyID", purchase_invoice_doc.currency)
                cbc_TaxAmount_3.text = "0"
                # cbc_TaxAmount_3.text = str(abs(round(item_tax_percentage * single_item.base_net_amount / 100, 2)))  # 100 * 6 % = 6

                #TaxSubtotal
                cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")

                #Amount Exempted from Tax(Invoice level tax exemption)
                cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
                cbc_TaxableAmount.set("currencyID", purchase_invoice_doc.currency)
                cbc_TaxableAmount.text = str(single_item.base_net_amount)   # 100  # #including only charges or discount and exclsing tax
                # cbc_TaxableAmount.text = str(abs(round(sales_invoice_doc.base_net_total,2)))               
              
                #tax amount                
                cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
                cbc_TaxAmount_2.set("currencyID", purchase_invoice_doc.currency)                
                cbc_TaxAmount_2.text = "0"

                cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")            
                cbc_TaxCategoryID = ET.SubElement(cac_TaxCategory, "cbc:ID")
                cbc_TaxCategoryID.text = "E" # set taxable type provided by lhdn
                # cbc_TaxCategoryID.text = single_item.custom_lhdn_tax_code  # set taxable type provided by lhdn

                # Details of Tax Exemption
                cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory, "cbc:TaxExemptionReason")
                cbc_TaxExemptionReason.text = single_item.custom_exemption_description_

                cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
                cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
                cbc_TaxSchemeID.set("schemeID", "UN/ECE 5153")
                cbc_TaxSchemeID.set("schemeAgencyID", "6")
                cbc_TaxSchemeID.text = "OTH"


            else:
                # # Tax Amount   / ubl:Invoice / cac:InvoiceLine / cac:TaxTotal / cbc:TaxAmount [@currencyID=’MYR’]
                cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
                cbc_TaxAmount_3.set("currencyID", purchase_invoice_doc.currency)   #Tax Amount of each item
                # cbc_TaxAmount_3.text = str(abs(round(item_tax_percentage * single_item.base_net_amount / 100, 2)))  # 100 * 6 % = 6
                cbc_TaxAmount_3.text = str(abs(round(single_item.custom_tax_amount, 2)))

                #if Tax Rate in percentage then we add tabsubtotal so in this way we ahve to add lineextensionamount as it is in taxablemaount

                #TaxSubtotal
                cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")


                #Amount Exempted from Tax(Invoice level tax exemption)
                cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
                cbc_TaxableAmount.set("currencyID", purchase_invoice_doc.currency)
                cbc_TaxableAmount.text = str(single_item.base_net_amount)   # 100  # #including only charges or discount and exclsing tax

            
                cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
                cbc_TaxAmount_2.set("currencyID", purchase_invoice_doc.currency)                
                cbc_TaxAmount_2.text =  str(abs(round(single_item.custom_tax_amount, 2)))

                  
                cac_TaxCategory = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")            
                
                cbc_TaxCategoryID = ET.SubElement(cac_TaxCategory, "cbc:ID")
                cbc_TaxCategoryID.text = single_item.custom_lhdn_tax_type_code

                # Tax Rate in percentage
                if(single_item.custom_tax_code):
                    item_tax_rate = frappe.get_doc("Purchase Taxes and Charges Template", single_item.custom_tax_code)
                    if(item_tax_rate.taxes and item_tax_rate.taxes[0]):
                        item_tax_percentage = item_tax_rate.taxes[0].rate
                    else:
                        item_tax_percentage = 0
                else:
                    item_tax_percentage = 0
                cbc_TaxRatePercent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
                cbc_TaxRatePercent.text = f"{item_tax_percentage:.2f}"

                cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
                cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
                cbc_TaxSchemeID.set("schemeID", "UN/ECE 5153")
                cbc_TaxSchemeID.set("schemeAgencyID", "6")
                cbc_TaxSchemeID.text = "OTH"


           
            # Item
            cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
           
            # Description of Product or Service
            cbc_Description = ET.SubElement(cac_Item, "cbc:Description")
            cbc_Description.text = single_item.description

            #Classification
            cac_CommodityClassification = ET.SubElement(cac_Item, "cac:CommodityClassification")
            cbc_ItemClassificationCode = ET.SubElement(cac_CommodityClassification, "cbc:ItemClassificationCode")
            cbc_ItemClassificationCode.set("listID", "CLASS")
            cbc_ItemClassificationCode.text = single_item.custom_item_classification_code

            # Unit Price
            cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")            
            cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount")
            cbc_PriceAmount.set("currencyID", purchase_invoice_doc.currency)
            cbc_PriceAmount.text = str(abs(single_item.rate))


            # Subtotal
            cac_ItemPriceExtension = ET.SubElement(cac_InvoiceLine, "cac:ItemPriceExtension")
            cbc_Amount = ET.SubElement(cac_ItemPriceExtension, "cbc:Amount")
            cbc_Amount.set("currencyID", purchase_invoice_doc.currency)
            cbc_Amount.text = str((single_item.rate) * (single_item.qty))   #excluding any charges , discount and tax

        return purchase_invoice
    except Exception as e:
        frappe.throw("Error occurred in item data: " + str(e))

def xml_structuring(purchase_invoice, purchase_invoice_doc):
            try:
                xml_declaration = "<?xml version='1.0' encoding='UTF-8'?>\n"
                tree = ET.ElementTree(purchase_invoice)
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
                    if frappe.db.exists("File",{ "attached_to_name": purchase_invoice_doc.name, "attached_to_doctype": purchase_invoice_doc.doctype }):
                        frappe.db.delete("File",{ "attached_to_name":purchase_invoice_doc.name, "attached_to_doctype": purchase_invoice_doc.doctype })
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
                
                try:
                    fileX = frappe.get_doc(
                        {   "doctype": "File",        
                            "file_type": "xml",  
                            "file_name":  "E-invoice-" + purchase_invoice_doc.name + ".xml",
                            "attached_to_doctype":purchase_invoice_doc.doctype,
                            "attached_to_name":purchase_invoice_doc.name, 
                            "content": pretty_xml_string,
                            "is_private": 1,})
                    fileX.save()
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
                
                try:
                    frappe.db.get_value('File', {'attached_to_name':purchase_invoice_doc.name, 'attached_to_doctype': purchase_invoice_doc.doctype}, ['file_name'])
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
            except Exception as e:
                    frappe.throw("Error occured in XML structuring and attach. Please contact your system administrator"+ str(e) )

def aggregate_tax_by_type(purchase_invoice_doc):
    tax_by_type = {}
    # tax_type = sales_invoice_doc.custom_lhdn_tax_type_code
    # tax_by_type[tax_type] = {
    #     'tax_amount': 0.0,
    #     'taxable_amount': 0.0
    # }
    for item in purchase_invoice_doc.items:
        tax_type = item.custom_lhdn_tax_type_code
        if tax_type not in tax_by_type:
            tax_by_type[tax_type] = {
                'tax_amount': 0.0,
                'taxable_amount': 0.0,
                'exemption_description': "" 
            }
        if item.custom_lhdn_tax_type_code == 'E':
            tax_by_type[tax_type]['exemption_description'] = item.custom_exemption_description_
        tax_by_type[tax_type]['taxable_amount'] += item.base_net_amount
        tax_by_type[tax_type]['tax_amount'] += item.custom_tax_amount
        # item_tax_amount, item_tax_percentage = get_Tax_for_Item(sales_invoice_doc.taxes[0].item_wise_tax_detail, item.item_code)
        # tax_type = item.custom_lhdn_tax_type_code if item.custom_lhdn_tax_type_code else sales_invoice_doc.custom_lhdn_tax_type_code
        # if tax_type not in tax_by_type:
        #     tax_by_type[tax_type] = {
        #         'tax_amount': 0.0,
        #         'tax_percentage': item_tax_percentage,
        #         'taxable_amount': 0.0
        #     }
        # tax_by_type[tax_type]['tax_amount'] += item_tax_amount
        # tax_by_type[tax_type]['taxable_amount'] += item.base_net_amount
    return tax_by_type

def invoice_Typecode_Compliance(purchase_invoice, compliance_type):
    # 01 	Invoice
    # 02 	Credit Note
    # 03 	Debit Note
    # 04 	Refund Note
    # 11 	Self-billed Invoice
    # 12 	Self-billed Credit Note
    # 13 	Self-billed Debit Note
    # 14 	Self-billed Refund Note
    try:                         
        cbc_InvoiceTypeCode = ET.SubElement(purchase_invoice, "cbc:InvoiceTypeCode")
        cbc_InvoiceTypeCode.set("listVersionID", "1.0")  # Current e-Invoice version

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
    
        return purchase_invoice
                
    except Exception as e:
        frappe.throw("error occured in Compliance typecode"+ str(e) )
        
def invoice_Typecode_Simplified(purchase_invoice, purchase_invoice_doc):
    try:                             
        cbc_InvoiceTypeCode = ET.SubElement(purchase_invoice, "cbc:InvoiceTypeCode")
        if purchase_invoice_doc.is_return == 0:         
            cbc_InvoiceTypeCode.set("name", "0200000") # Simplified
            cbc_InvoiceTypeCode.text = "388"
        elif purchase_invoice_doc.is_return == 1:       # return items and simplified invoice
            cbc_InvoiceTypeCode.set("name", "0200000")  # Simplified
            cbc_InvoiceTypeCode.text = "381"  # Credit note
        return purchase_invoice
    except Exception as e:
        frappe.throw("error occured in simplified invoice typecode"+ str(e) )

def invoice_Typecode_Standard(purchase_invoice, purchase_invoice_doc):
    try:
        cbc_InvoiceTypeCode = ET.SubElement(purchase_invoice, "cbc:InvoiceTypeCode")
        cbc_InvoiceTypeCode.set("name", "0100000") # Standard
        if purchase_invoice_doc.is_return == 0:
            cbc_InvoiceTypeCode.text = "388"
        elif purchase_invoice_doc.is_return == 1:     # return items and simplified invoice
            cbc_InvoiceTypeCode.text = "381" # Credit note
        return purchase_invoice
    except Exception as e:
        frappe.throw("Error in standard invoice type code: "+ str(e))