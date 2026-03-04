import json
from odoo import http
from odoo.http import content_disposition, request


class StockXLSXReportController(http.Controller):
    @http.route('/ttb_xlsx_report', type='http', auth='user', csrf=False)
    def get_report(self, model, data):
        data = json.loads(data)
        response = request.env[model].get_xlxs_report(data)
        return request.make_response(
            response,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition('bartender' + '.xlsx'))
            ]
        )

