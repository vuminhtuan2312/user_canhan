from odoo import models, fields

class ReportDownloader(models.TransientModel):
    _name = 'report.downloader'
    _description = 'Report Downloader Wizard'

    file_data = fields.Binary('File', readonly=True, required=True)
    file_name = fields.Char('File Name', readonly=True, required=True)

    def download_report(self):
        return

