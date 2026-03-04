import re

from odoo import *
from odoo import _
from odoo.addons.ttb_einvoice.models.einvoice_service import object_to_xml
from collections import defaultdict
from odoo.exceptions import UserError



class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'api_call.base']

    ttb_serial_id = fields.Many2one(string='Ký hiệu hóa đơn điện tử', comodel_name='ttb.einvoice.serial', tracking=True)
    ttb_service_id = fields.Many2one(string='Dịch vụ hóa đơn điện tử', related='ttb_serial_id.service_id')
    ttb_pattern = fields.Char(string='Mẫu hóa đơn', related='ttb_serial_id.pattern')
    ttb_type = fields.Char(string='Loại hóa đơn', related='ttb_serial_id.type')
    ttb_invoice_number = fields.Char('Số hoá đơn')
    ttb_invoice_id = fields.Many2one(string='Pháp nhân xuất hóa đơn', comodel_name='res.partner')
    ttb_einvoice_state = fields.Selection(string='Trạng thái HĐĐT', selection=[('new', 'Chưa tạo'), ('created', 'Đã tạo hóa đơn'), ('published', 'Đã phát hành')], default='new', tracking=True)
    ttb_company_partner_id = fields.Many2one(related='company_id.partner_id')
    total_discount_amount = fields.Monetary(string='Tổng chiết khấu', currency_field='currency_id',
                                            compute='_compute_total_discount_amount', store=True, readonly=True)

    @api.depends('invoice_line_ids.ttb_discount_amount')
    def _compute_total_discount_amount(self):
        for move in self:
            move.total_discount_amount = sum(line.ttb_discount_amount or 0.0 for line in move.invoice_line_ids)

    def _post(self, soft=True):
        res = super()._post(soft)
        for rec in self:
            if not rec.pos_order_ids.payment_ids.account_move_id: continue
            payments_widget_vals = rec.sudo().invoice_outstanding_credits_debits_widget
            if not payments_widget_vals: continue
            for payment in payments_widget_vals.get('content', []):
                if payment.get('move_id') not in rec.mapped('pos_order_ids.payment_ids.account_move_id').ids: continue
                rec.js_assign_outstanding_line(payment.get('id'))
            # if rec.pos_order_ids and rec.ttb_service_id.vendor == 'vnpt':
            #     if rec.ttb_einvoice_state == 'new':
            #         rec.ttb_create_einvoice()
            #     if rec.ttb_einvoice_state == 'created':
            #         rec.ttb_publish_einvoice()

        return res

    def ttb_create_einvoice(self, invoice_info):
        def prepare_inv(lines, number=None):
            vat_amounts = defaultdict(float)
            gross_amounts = defaultdict(float)
            for line in lines:
                is_kct = line.tax_ids[:1].id == 15
                tax_number = 111 if is_kct else int(line.tax_ids[:1].amount or 0)

                vat_amounts[tax_number] += line.price_total - line.price_subtotal
                gross_amounts[tax_number] += line.price_subtotal 

            tax_values = {}
            for tax_number in vat_amounts:
                if tax_number == 111:
                    tax_values['GrossValue'] = gross_amounts[tax_number]
                else:
                    tax_values['VatAmount%s' % tax_number] = vat_amounts[tax_number]
                    tax_values['GrossValue%s' % tax_number] = gross_amounts[tax_number]

            product_lines = []
            discount_amount_sum = 0
            for line in lines:
                prices = line.tax_ids.compute_all(line.price_unit, self.currency_id, 1, product=line.product_id, partner=False)
                price_excluded = prices['total_excluded']
                discount_amount = price_excluded * line.quantity * line.discount / 100
                discount_amount = self.currency_id.round(discount_amount)
                is_kct = line.tax_ids[:1].id == 15
                tax_amount = 0 if is_kct else (line.price_total - line.price_subtotal)
                if (line.ttb_discount_amount or 0.0) != discount_amount:
                    line.sudo().write({'ttb_discount_amount': discount_amount})
                if (line.ttb_tax_amount or 0.0) != tax_amount:
                    line.sudo().write({'ttb_tax_amount': tax_amount})
                
                product_lines.append({
                    'Code': line.product_id.barcode or line.product_id.default_code or 'no_barcode_default_code',
                    'ProdName': line.product_id.display_name,
                    'ProdUnit': line.product_uom_id.name,
                    'ProdQuantity': line.quantity,
                    'ProdPrice': price_excluded,
                    'Amount': line.price_total,
                    'Discount': line.discount,
                    'DiscountAmount': discount_amount,
                    'IsSum': 0 if line.price_unit > 0 else 1 if not line.price_unit else 2,
                    'Total': line.price_subtotal,
                    'VATRate': -1 if is_kct else sum(line.mapped('tax_ids.amount')),
                    'VATAmount': tax_amount,
                    'Extra1': line.promotion_program_name or '',
                })
                discount_amount_sum += discount_amount

            email_value = {'EmailDeliver': invoice_info['EmailDeliver']} if invoice_info.get('EmailDeliver') else {}
            return {
                'key': self.name if not number else f'{self.name}/{number}',
                'Invoice': {
                    'CusCode': invoice_info.get('CusCode', '') if invoice_info else self.partner_id.ref or '',
                    'CusName': invoice_info.get('CusName', '') if invoice_info else self.partner_id.name or '',
                    'CusAddress': ', '.join(partner_addr) if partner_addr else '',
                    'CusTaxCode': invoice_info.get('CusTaxCode', '') if invoice_info else self.partner_id.vat or '',
                    'MDVQHNSach': invoice_info.get('code_qhns', '') if invoice_info else '',
                    'PaymentMethod': 'TM, CK',
                    'Products': {
                        'Product': product_lines,
                    },
                    'Total': sum(lines.mapped('price_subtotal')),
                    'DiscountAmount': discount_amount_sum,
                    'VATAmount': sum(lines.mapped('price_total')) - sum(lines.mapped('price_subtotal')),
                    'Amount': sum(lines.mapped('price_total')),
                    'AmountInWords': self.currency_id.amount_to_text(sum(lines.mapped('price_total'))).replace('Dong', 'Đồng'),
                    # 'ArisingDate': self.invoice_date.strftime('%d/%m/%Y'),
                    'ArisingDate': fields.Date.context_today(self).strftime('%d/%m/%Y'),
                    'ComName': self.ttb_invoice_id.name,
                    'ComAddress': ', '.join(invoice_addr) if invoice_addr else '',
                    'ComTaxCode': self.ttb_invoice_id.vat,
                    ** tax_values,
                    ** email_value,
                }
            }

        host = self.ttb_service_id.host
        endpoint = f'{host}/publishservice.asmx'
        headers = {'Content-Type': 'text/xml;charset=utf-8'}
        addr = ['street', 'street2', 'city', 'state_code', 'zip', 'country_name']
        
        if invoice_info:
            partner_addr = invoice_info.get('CusAddress')
            partner_addr = [partner_addr] if partner_addr else []
        else:
            partner_addr = []
            for add in addr:
                if self.partner_id.read([add])[0].get(add):
                    partner_addr += [self.partner_id.read([add])[0].get(add)]

        invoice_addr = []
        for add in addr:
            if self.ttb_invoice_id.read([add])[0].get(add):
                invoice_addr += [self.ttb_invoice_id.read([add])[0].get(add)]

        Inv = [prepare_inv(self.invoice_line_ids)]

        data = {
            'Account': self.ttb_service_id.account,
            'ACpass': self.ttb_service_id.acpass,
            'username': self.ttb_service_id.username,
            'password': self.ttb_service_id.password,
            'pattern': self.ttb_serial_id.pattern,
            'serial': self.ttb_serial_id.name,
            'convert': 0,
        }
        body = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <ImportInvByPattern xmlns="http://tempuri.org/">
        """
        body += object_to_xml(data, '')
        body += f"""<xmlInvData><![CDATA[{object_to_xml({'Invoices': {'Inv': Inv}}, '')}]]></xmlInvData>"""
        body += """
                     </ImportInvByPattern>
                </soap:Body>
            </soap:Envelope>
        """
        response = self._call_api(endpoint, body, headers, 'POST', 'xml')
        if isinstance(response, dict):
            self.write({'call_error': response.get('error')})
        else:
            if response[0][0][0].text.startswith(f'OK:{self.ttb_serial_id.pattern};{self.ttb_serial_id.name}'):
                self.write({
                    'ttb_einvoice_state': 'created',
                    'call_error': False,
                    'l10n_vn_e_invoice_number': response[0][0][0].text.replace(f'OK:{self.ttb_serial_id.pattern};{self.ttb_serial_id.name}-', '').replace(',', '_')
                })
            else:
                self.write({'call_error': self.ttb_service_id.get_error_by_code(response[0][0][0].text) or response[0][0][0].text})
        # do smt with response?
        return True

    def get_invoice_number(self, full_xml_string):
        invoice_name = self.l10n_vn_e_invoice_number or self.name

        success_string = f'OK:#{invoice_name}_'
        invoice_number = False
        
        if success_string in full_xml_string:
            pattern = rf"{success_string}(\d+)"
            match = re.search(pattern, full_xml_string)
            if match:
                invoice_number = match.group(1)

        return invoice_number

    def auto_invoice_number(self):
        for rec in self:
            for api_call in rec.call_log_ids.filtered(lambda x: '/publishservice.asmx' in x.url):
                invoice_number = rec.get_invoice_number(api_call.response_text)

                if invoice_number:
                    rec.write({
                        'ttb_einvoice_state': 'published',
                        'call_error': False,
                        'ttb_invoice_number': invoice_number,
                    })
                    break

    def ttb_publish_einvoice(self):
        host = self.ttb_service_id.host
        endpoint = f'{host}/publishservice.asmx'
        headers = {'Content-Type': 'text/xml;charset=utf-8'}
        data = {
            'Account': self.ttb_service_id.account,
            'ACpass': self.ttb_service_id.acpass,
            'username': self.ttb_service_id.username,
            'password': self.ttb_service_id.password,
            'pattern': self.ttb_serial_id.pattern,
            'serial': self.ttb_serial_id.name,
            'lsFkey': self.l10n_vn_e_invoice_number,
        }
        body = """
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                        <soap:Body>
                            <PublishInvFkey xmlns="http://tempuri.org/">
                """
        body += object_to_xml(data, '')
        body += """
                             </PublishInvFkey>
                        </soap:Body>
                    </soap:Envelope>
                """
        response = self._call_api(endpoint, body, headers, 'POST', 'xml')
        if isinstance(response, dict):
            self.write({'call_error': response.get('error')})
        else:
            full_xml_string = response[0][0][0].text
            invoice_number = self.get_invoice_number(full_xml_string)
            if invoice_number:
                self.write({
                    'ttb_einvoice_state': 'published',
                    'call_error': False,
                    'ttb_invoice_number': invoice_number,
                })
            else:
                self.write({'call_error': self.ttb_service_id.get_error_by_code(full_xml_string) or full_xml_string})
        # do smt with response?
        return True

    def ttb_call_api_einvoice(self, invoice_info={}):
        if self.ttb_einvoice_state == 'new':
            self.ttb_create_einvoice(invoice_info)
        # return
        if self.state == 'posted' and self.ttb_einvoice_state == 'created':
            self.ttb_publish_einvoice()

    def action_ttb_export_einvoice(self):
        """
        Xuất hóa đơn điện tử cho từng hóa đơn, dùng cùng flow với 'phiên xuất':
        - Nếu trạng thái HĐĐT = 'new'  -> ttb_create_einvoice()
        - Nếu đã 'Đã vào sổ' + 'created' -> ttb_publish_einvoice()
        """
        for move in self:
            if move.state != 'posted':
                raise UserError(_("Hóa đơn phải ở trạng thái 'Đã vào sổ'."))
            if not move.ttb_serial_id:
                raise UserError(_("Vui lòng chọn ký hiệu hóa đơn điện tử."))
            # Gọi đúng quy trình hiện tại
            move.ttb_call_api_einvoice({})

        return True

    def action_ttb_create_einvoice(self):
        """
        Tạo HĐĐT (ImportInv) nhưng CHƯA phát hành.
        Dùng để kiểm tra trước trên cổng VNPT.
        """
        for move in self:
            if move.state != 'posted':
                raise UserError(_("Hóa đơn phải ở trạng thái 'Đã vào sổ' trước khi tạo HĐĐT."))
            if not move.ttb_serial_id:
                raise UserError(_("Vui lòng chọn Ký hiệu hóa đơn điện tử trước khi tạo HĐĐT."))

            if move.ttb_einvoice_state not in ('new',):  # nếu đã created/published thì không cho tạo lại
                raise UserError(_("HĐĐT cho hóa đơn này đã được tạo hoặc đã phát hành."))

            move.ttb_create_einvoice({})
        return True

    def action_ttb_publish_einvoice(self):
        """
        Phát hành HĐĐT (PublishInvFkey) sau khi đã tạo và kiểm tra trên VNPT.
        """
        for move in self:
            if move.ttb_einvoice_state != 'created':
                raise UserError(_("Chỉ phát hành HĐĐT khi trạng thái HĐĐT là 'Đã tạo' (created)."))

            move.ttb_publish_einvoice()

    def action_ttb_set_serial_from_branch(self):
        """
        Lấy ký hiệu hóa đơn (ttb_serial_id) từ Cơ sở (branch).
        """
        for move in self:
            orders = move.mapped('invoice_line_ids.sale_line_ids.order_id')
            orders = orders.filtered('id')

            if not orders:
                raise UserError(_("Không tìm thấy Đơn bán (Sale Order) gốc từ hoá đơn này."))
            if len(orders) > 1:
                raise UserError(_("Hóa đơn này đang liên quan tới nhiều Đơn bán, không biết lấy cơ sở từ đơn nào."))
            order = orders[0]
            branch = getattr(order, 'ttb_branch_id', False)
            if not branch:
                raise UserError(_("Đơn bán %s chưa gắn Cơ sở (branch), không thể tự lấy ký hiệu.") % order.name)
            if not getattr(branch, 'invoice_serial_id', False):
                raise UserError(_("Cơ sở %s chưa cấu hình Ký hiệu hoá đơn điện tử.") % branch.display_name)

            move.ttb_serial_id = branch.invoice_serial_id.id
        return True
