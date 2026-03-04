from odoo import *


class PurchaseBatchSelectPR(models.TransientModel):
    _name = 'ttb.purchase.batch.select.pr.wizard'
    _description = 'Chọn PR'

    pr_ids = fields.Many2many(string='Danh sách PR', comodel_name='ttb.purchase.request', domain=[('state', '=', 'approved'), ('line_ids.partner_id', '=', False)])

    def do(self):
        record = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids'))
        if record.line_ids:
            return
        pr_lines = self.pr_ids.line_ids.filtered(lambda x: x.product_id and not x.partner_id and not x.reject and (not x.user_id or x.user_id.id == record.user_id.id))

        line_ids = [(5, 0, 0)]
        query = f"""
        SELECT * from 
            (SELECT pol.product_id,pol.id,
            RANK () OVER (PARTITION BY pol.product_id ORDER BY pol.date_approve desc) as sequence
            FROM (
            select DISTINCT ON(pol.partner_id,pol.product_id) pol.product_id,pol.id,po.date_approve
            from 
                purchase_order_line pol left join
                purchase_order po on  pol.order_id = po.id left join
                res_partner rp on po.partner_id = rp.id
            where pol.product_id in {str(tuple([-1, 0] + pr_lines.mapped('product_id').ids))} 
            and po.state in ('purchase','done')
            and po.company_id = {record.company_id.id}
            order by pol.partner_id,pol.product_id,po.date_approve desc,pol.product_qty desc) pol
            order by pol.date_approve desc)
            where sequence <= 3
        """
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        rank_pol_by_product = {}
        for result in results:
            if result['product_id'] not in rank_pol_by_product:
                rank_pol_by_product.setdefault(result['product_id'], {1: self.env['purchase.order.line'], 2: self.env['purchase.order.line'], 3: self.env['purchase.order.line']})
            rank_pol_by_product[result['product_id']][result['sequence']] = result['id']
        for product in pr_lines.mapped('product_id'):
            pr_line_ids = pr_lines.filtered(lambda x: x.product_id.id == product.id)
            quantity = sum([line.uom_id._compute_quantity(line.quantity, product.uom_id) for line in pr_line_ids])
            vals = {
                'product_id': product.id,
                'quantity': quantity,
                'uom_id': product.uom_id.id,
                'purchase_line_id_1': rank_pol_by_product.get(product.id, {}).get(1),
                'purchase_line_id_2': rank_pol_by_product.get(product.id, {}).get(2),
                'purchase_line_id_3': rank_pol_by_product.get(product.id, {}).get(3),
                'pr_line_ids': [(4, line.id) for line in pr_line_ids]
            }
            line_ids += [(0, 0, vals)]
        record.write({'line_ids': line_ids})
        return
