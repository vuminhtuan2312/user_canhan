from odoo import models, fields, api, _

class ExperimentalKiemKe(models.Model):
    _name='experimental.kiemke'
    _description='thi nghiem kiem ke'

    name=fields.Char('ten', default='thi nghiem')
    line_ids=fields.One2many('experimental.kiemke.lines', inverse_name='kiemke_id')

    @api.model
    def get_product_by_session_id(self, session_id):
        session = self.browse(session_id).line_ids
        product_list= []
        for detail in session:
            product_dict = {
                'product_id': detail.product_id.id,
                'order_number': detail.order_number,
                'quantity': detail.quantity,
            }
            product_list.append(product_dict)
        return product_list

    @api.model
    def filter_on_barcode(self, barcode, id):
        product = self.env['product.product'].search([('barcode','=',barcode)])
        if product:
            kiem_ke_lines = self.browse(id).line_ids
            for line in kiem_ke_lines:
                if product.id == line.product_id.id:
                    return {
                        'stock_location_id': line.id,
                        'product': line.product_id.id,
                        'order_number': line.order_number,
                        'quantity': line.quantity,
                    }
        return {
            'warning': {
                'message': _("Quét sai quay thi nghiem, vui lòng thử lại")
            }
        }

class ExperimentalKiemKeLine(models.Model):
    _name='experimental.kiemke.lines'
    _description='chi tiet thi nghiem kiem ke'

    product_id = fields.Many2one('product.product')
    order_number = fields.Integer('STT', default=0)
    quantity = fields.Integer('So luong', default=0)
    kiemke_id = fields.Many2one('experimental.kiemke')
