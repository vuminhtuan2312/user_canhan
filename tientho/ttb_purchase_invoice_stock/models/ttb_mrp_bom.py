from odoo import api, fields, models
from odoo.tools import float_round

class TtbMrpBom(models.Model):
    """ Defines bills of material for a product or a product template """
    _name = 'ttb.mrp.bom'
    _description = 'Định mức nguyên vật liệu'
    _inherit = ['mail.thread']
    _rec_name = 'product_tmpl_id'
    _order = "sequence, id"
    _check_company_auto = True

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    active = fields.Boolean('Active', default=True)
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        check_company=True, index=True,
        domain="[('type', '=', 'consu')]", required=True)
    bom_line_ids = fields.One2many('ttb.mrp.bom.line', 'bom_id', 'Thành phần', copy=True)
    product_qty = fields.Float(
        'Số lượng', default=1.0,
        digits='Product Unit of Measure', required=True,
        help="This should be the smallest quantity that this product can be produced in. If the BOM contains operations, make sure the work center capacity is accurate.")
    product_uom_id = fields.Many2one(
        'uom.uom', 'Đơn vị',
        default=_get_default_product_uom_id, required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control", domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_tmpl_id.uom_id.category_id')
    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)

    def ttb_explode(self, need_quantity, uom_id=False):
        product_qty = self.product_qty
        if uom_id and uom_id != self.product_uom_id:
            product_qty = self.product_uom_id._compute_quantity(product_qty, uom_id)

        lines_done = []
        for bom_line in self.bom_line_ids:
            line_quantity = bom_line.product_qty * (need_quantity / product_qty)
            rounding = bom_line.product_uom_id.rounding
            line_quantity = float_round(line_quantity, precision_rounding=rounding, rounding_method='UP')

            lines_done.append((bom_line, {'qty': line_quantity}))

        return lines_done


class TtbMrpBomLine(models.Model):
    _name = 'ttb.mrp.bom.line'
    _order = "sequence, id"
    _rec_name = "product_id"
    _description = 'Bill of Material Line'
    _check_company_auto = True

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    product_id = fields.Many2one('product.product', 'Thành phần', required=True, check_company=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id', store=True, index=True)
    company_id = fields.Many2one(
        related='bom_id.company_id', store=True, index=True, readonly=True)
    product_qty = fields.Float(
        'Số lượng', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Đơn vị tính',
        default=_get_default_product_uom_id,
        required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control", domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    sequence = fields.Integer(
        'Sequence', default=1,
        help="Gives the sequence order when displaying.")
    bom_id = fields.Many2one(
        'ttb.mrp.bom', 'Parent BoM',
        index=True, ondelete='cascade', required=True)
    parent_product_tmpl_id = fields.Many2one('product.template', 'Parent Product Template', related='bom_id.product_tmpl_id')
