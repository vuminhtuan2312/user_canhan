from odoo.exceptions import UserError
from odoo import api, fields, models
from collections import defaultdict

class ReportTemplateEvaluationForm(models.AbstractModel):
    _name = 'report.ttb_purchase.template_goods_distribution_form_document'
    _description = 'Mẫu in phiếu chia hàng'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['goods.distribution.ticket'].browse(docids)
        if len(docs)>1:
            raise UserError("Chỉ được in 1 phiếu phân phối hàng một lần!")
        list_branch = []

        processed_data = []
        for doc in docs:
            product_dict = defaultdict(list)
            for line in doc.goods_distribution_ticket_line_ids:
                if line.branch_id not in list_branch:
                    list_branch.append(line.branch_id)

                key = (line.product_id, line.ttb_request_line_id.product_image, line.ttb_request_line_id.item, line.ttb_request_line_id.description,
                       line.po_line_id.qty_received, line.ttb_request_line_id.number_of_cases, line.po_line_id.ttb_stock_qty)
                product_dict[key].append(line.actual_qty)
            data_row = {
                'id': doc.id,
                'partner_id': doc.partner_id if doc.partner_id else '',
                'purchase_order': doc.po_id if doc.po_id else '',
                'exchange_rate': doc.po_id.exchange_rate,
                'qty': product_dict
            }
            processed_data.append(data_row)

        return {
            'doc_ids': docids,
            'doc_model': 'goods.distribution.ticket',
            'docs': processed_data,  # Trả về original Odoo records
            'company': self.env.company,
            'list_branch': list_branch,
            'o': docs[0] if docs else None,
        }

