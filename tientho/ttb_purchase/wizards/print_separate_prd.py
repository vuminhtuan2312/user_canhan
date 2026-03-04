from odoo.exceptions import UserError
from odoo import api, fields, models
from collections import defaultdict

class ReportSeparatePrd(models.AbstractModel):
    _name = 'report.ttb_purchase.template_print_separate_prd_document'
    _description = 'Mẫu in hàng tách mã'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.picking'].browse(docids)
        if len(docs) >1:
            raise UserError("Chỉ được in một phiếu một lần!")

        request_name= docs.purchase_id.ttb_request_id.name
        po_name= docs.purchase_id.name
        partner= docs.purchase_id.partner_id.name

        list_separate_prd = docs.move_ids.filtered(lambda r: r.purchase_line_id.ttb_request_line_id.separate_prd)
        if not list_separate_prd:
            raise UserError("Không có hàng tách mã để in!")

        return {
            'doc_ids': docids,
            'doc_model': 'stock.move',
            'docs': list_separate_prd,
            'request_name': request_name,
            'po_name': po_name,
            'partner': partner,
        }

