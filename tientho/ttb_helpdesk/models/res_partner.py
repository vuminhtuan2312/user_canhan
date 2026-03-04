from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import re


class Partner(models.Model):
    _inherit = "res.partner"

    ticket_ids = fields.One2many('helpdesk.ticket', 'partner_id', string='Ticket')
    ttb_hpc_ids = fields.One2many('ttb.happy.call', 'partner_id', string='Happycall')
    ttb_transaction_ids = fields.One2many('ttb.transaction', 'partner_id', string='Tuơng tác')

    total_accumulated_points = fields.Float(string='Tổng điểm tích lũy')
    redeemed_accumulated_points = fields.Float(string='Điểm tích lũy SD')
    remaining_accumulated_points = fields.Float(string='Điểm tích lũy còn')

    pos_order_amount_total = fields.Float(compute='_get_info_partner', string="Giá trị mua hàng")
    pos_order_amount_total_year = fields.Float(compute='_get_info_partner', string="Giá trị mua hàng trong năm")
    pos_order_last_date = fields.Datetime(compute='_get_info_partner', string="Lần mua hàng gần nhất")
    hpc_done_last_date = fields.Datetime(compute='_get_info_hpc_partner', string="Thời gian Happy Call thành công gần nhất")
    hpc_last_date = fields.Datetime(compute='_get_info_hpc_partner', string="Thời gian Happy Call gần nhất")

    order_ids = fields.One2many('pos.order', 'partner_id', string='Đơn Hàng', compute='_compute_order_ids')
    phone_masked = fields.Char(compute="_compute_phone_masked", store=False)

    @api.depends('phone')
    def _compute_phone_masked(self):
        is_cskh = self.env.user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh')
        for rec in self:
            if rec.phone:
                if not rec.id:
                    rec.phone_masked = rec.phone
                    continue

                if is_cskh:
                    clean_phone = re.sub(r'\D', '', rec.phone)
                    if len(clean_phone) > 3:
                        rec.phone_masked = '*' * (len(clean_phone) - 3) + clean_phone[-3:]
                    else:
                        rec.phone_masked = '*' * len(clean_phone)
                else:
                    rec.phone_masked = rec.phone
            else:
                rec.phone_masked = ""
    def _compute_order_ids(self):
        for record in self:
            if record.id:
                record.order_ids = self.env['pos.order'].sudo().search([('partner_id', '=', record.id)], limit=100)
            else:
                record.order_ids = self.env['pos.order'].sudo()

    @api.depends('pos_order_ids')
    def _get_info_partner(self):
        for rec in self:
            rec.pos_order_amount_total = sum(rec.pos_order_ids.mapped('amount_total'))
            rec.pos_order_amount_total_year = sum(rec.pos_order_ids.filtered(lambda o: o.date_order >= (fields.Datetime.now() + relativedelta(day=1, month=1, hour=0, minute=0, second=0, hours=-7))).mapped('amount_total'))
            rec.pos_order_last_date = rec.pos_order_ids[:1].date_order

    @api.depends('ttb_hpc_ids')
    def _get_info_hpc_partner(self):
        for rec in self:
            rec.hpc_done_last_date = rec.ttb_hpc_ids.filtered(lambda o: o.state == 'success').sorted('create_date')[:1].create_date
            rec.hpc_last_date = rec.ttb_hpc_ids.sorted('create_date')[:1].create_date
