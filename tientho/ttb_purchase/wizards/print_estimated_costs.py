from odoo.exceptions import UserError
from odoo import api, fields, models
from collections import defaultdict

class ReportEstimatedCosts(models.AbstractModel):
    _name = 'report.ttb_purchase.template_print_estimated_costs_document'
    _description = 'Mẫu in đề nghị tạm ứng'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        if len(docs) >1:
            raise UserError("Chỉ được in một phiếu một lần!")

        request_name= docs.ttb_request_id.name
        po_name= docs.name
        partner= docs.partner_id.name

        list_prd = docs.ttb_request_id.line_ids
        price_by_prd_dict = {}
        for line in docs.order_line:
            if line.ttb_product_code not in price_by_prd_dict:
                price_by_prd_dict[line.ttb_product_code] = [line.price_unit,line.price_unit_cn,line.purchase_price,
                                                            line.selling_price, line.price_subtotal, line.price_total]

        return {
            'doc_ids': docids,
            'doc_model': 'stock.move',
            'docs': list_prd,
            'price_by_prd_dict': price_by_prd_dict,
            'request_name': request_name,
            'po_name': po_name,
            'partner': partner,
        }
