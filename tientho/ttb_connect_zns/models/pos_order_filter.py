from odoo import models, fields, api
from datetime import datetime, time
import ast
from odoo.osv import expression


class PosOrderFilter(models.Model):
    _name = 'ttb.pos.order.filter'
    _description = 'Filter POS Order by Config'

    @api.model
    def action_open_pos_order_by_time_config(self):
        now = fields.Datetime.now()
        weekday = str(now.weekday())

        # --------------------------------
        # 1️⃣ CONFIG KHUNG GIỜ + CHI NHÁNH
        # --------------------------------
        configs = self.env['condition.to.send.zns'].search([
            ('date_in_week', '=', weekday),
        ])

        time_domains = []
        for cfg in configs:
            time_domains.append([
                '&',
                ('ttb_branch_id', '=', cfg.ttb_branch_id.id),
                ('date_order', '>=', self._dt(now.date(), cfg.time_from)),
                ('date_order', '<=', self._dt(now.date(), cfg.time_to)),
            ])

        time_domain = expression.OR(time_domains) if time_domains else []

        # --------------------------------
        # 2️⃣ CAMPAIGN res.partner
        # --------------------------------
        campaigns = self.env['period.campaign'].search([
            ('state', '=', 'running'),
        ])

        # Partner domain (OR nhiều campaign)
        partner_domains = [
            ast.literal_eval(c.domain)
            for c in campaigns
            if c.domain
        ]
        partner_domain = expression.OR(partner_domains) if partner_domains else []

        # Product condition
        product_ids = campaigns.mapped('product_ids.id')

        # --------------------------------
        # 3️⃣ BUILD DOMAIN POS.ORDER (AND)
        # --------------------------------
        domain = [
            ('is_send_sms_zalo_oa_zns', '=', False),
        ]

        if time_domain:
            domain = expression.AND([domain, time_domain])

        if partner_domain:
            partner_ids = self.env['res.partner'].search(partner_domain).ids
            domain.append(('partner_id', 'in', partner_ids))

        if product_ids:
            domain.append(('lines.product_id', 'in', product_ids))




        return {
            'type': 'ir.actions.act_window',
            'name': 'POS Orders theo khung giờ',
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def _dt(self, date, float_hour):
        hour = int(float_hour)
        minute = int((float_hour - hour) * 60)
        return fields.Datetime.to_string(
            datetime.combine(date, time(hour, minute))
        )
