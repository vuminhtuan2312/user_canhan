from odoo import api, fields, models, _
from datetime import datetime, time

class TtbKpiTypeGroup(models.Model):
    _name = 'ttb.kpi.type.group'
    _description = 'Nhóm KPI'

    name = fields.Char(string='Tên nhóm KPI', required=True)
    menu_report_id = fields.Many2one('ir.ui.menu', string='Menu báo cáo')
    kpi_type_ids = fields.One2many('ttb.kpi.type', 'group_id', string='Loại KPI')
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._sync_menu()
        return record

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for record in self:
                record._sync_menu()
        
        if 'active' in vals:
            self.menu_report_id.write({'active': vals['active']})

        return res

    def unlink(self):
        menus = self.mapped('menu_report_id')
        res = super().unlink()
        if menus:
            menus.sudo().unlink()
        return res

    def _sync_menu(self):
        menu_obj = self.env['ir.ui.menu'].sudo()
        action_obj = self.env['ir.actions.act_window'].sudo()

        parent_menu = self.env.ref('ttb_kpi.ttb_check_list_report_menu')

        for record in self:
            if record.menu_report_id:
                record.menu_report_id.write({'name': record.name})
                continue

            action = action_obj.create({
                'name': record.name,
                'res_model': 'ttb.task.report',
                'view_mode': 'list,form,pivot',
                'domain': [
                    ('kpi_type_id.group_id', '=', record.id),
                    ('group', '=', 'manager'),
                ],
            })

            menu = menu_obj.create({
                'name': record.name,
                'parent_id': parent_menu.id,
                'action': f'ir.actions.act_window,{action.id}',
            })

            record.menu_report_id = menu.id
