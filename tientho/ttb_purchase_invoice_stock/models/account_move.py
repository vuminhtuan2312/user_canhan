from odoo.exceptions import UserError
from odoo import api, Command, fields, models, _
import logging
from odoo.tools.float_utils import float_is_zero
from odoo.tools import format_amount, format_date, format_list, formatLang, groupby

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    compare_invoice = fields.Selection([('quantity', 'Lệch số lượng'), ('money', "Lệch tiền"), ('no_invoice_vendor', "Nhà cung cấp không xuất hóa đơn"),
                                        ('matching', "Khớp"), ('none', "Hoá đơn không đi cùng hàng")],
                                       string="Khớp hóa đơn đỏ", readonly=True, copy=False, )

    def create_invoice(self, po, precision):
        # Dùng cho từng PO một
        invoice_vals_list = []
        sequence = 10
        for order in po:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        line_vals = pending_section._prepare_account_move_line()
                        line_vals.update({'sequence': sequence})
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
                        pending_section = None
                    line_vals = line._prepare_account_move_line()
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(
                _('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list,
                                               key=lambda x: (x.get('company_id'), x.get('partner_id'),
                                                              x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_move_type()
        if po.ttb_vendor_invoice_date:
            moves.write({'invoice_date': po.ttb_vendor_invoice_date})
        else:
            moves.write({'invoice_date': '1990-01-01'})

    def _create_invoice_from_po(self, po_name):
        po_by_name_list = self.env['purchase.order'].search([('name', 'in', po_name)]) if po_name else _logger.info(f"Không có PO name")

        if po_by_name_list:
            _logger.info(f"Tạo hóa đơn cho : {len(po_by_name_list)} PO.")
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            list_create = []
            list_error = []
            set_error = set()
            count_po = 0
            count_error = 0
            for po in po_by_name_list:
                try:
                    _logger.error(f"Tạo hóa đơn cho PO {po.name}")
                    self.create_invoice(po, precision)
                    count_po += 1
                    list_create.append(po.name)
                except UserError as e:
                    list_error.append({po.name})
                    set_error.add(str(e))
                    count_error += 1
            _logger.error(f"Lỗi tạo hóa đơn cho PO {list_error} với các lý do: {set_error}")
            _logger.info(f"Tạo xong hóa đơn cho các Po: {list_create}")
            _logger.info(f"Tạo xong hóa đơn theo tên cho : {count_po} PO. Có {count_error} PO lỗi.")
