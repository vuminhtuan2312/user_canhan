from odoo import models, fields

class RefuseCampaignWizard(models.TransientModel):
    _name = 'refuse.campaign.wizard'
    _description = 'Refuse Campaign Wizard'

    reason = fields.Text(string="Lý do từ chối", required=True)

    def action_confirm_refuse(self):
        campaign = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        campaign.reason = self.reason
        campaign.action_refuse_campaign(self.reason)
