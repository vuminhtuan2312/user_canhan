from odoo.exceptions import UserError
from odoo import api, fields, models
from collections import defaultdict

class ReportTemplatePrintReturnRequestSupplier(models.AbstractModel):
    _name = 'report.ttb_return_request.print_return_request_document'
    _description = 'Mẫu in phiếu trả NCC'

    def convert_number_to_words(self, amount):
        """Chuyển đổi số tiền thành chữ tiếng Việt"""
        if amount == 0:
            return "Không đồng"

        units = ["", "nghìn", "triệu", "tỷ"]
        ones = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

        def read_block(number):
            """Đọc một khối 3 chữ số"""
            result = ""
            hundred = number // 100
            ten = (number % 100) // 10
            one = number % 10

            if hundred > 0:
                result += ones[hundred] + " trăm "
                if ten == 0 and one > 0:
                    result += "lẻ "

            if ten > 1:
                result += ones[ten] + " mươi "
                if one == 1:
                    result += "mốt "
                elif one == 5:
                    result += "lăm "
                elif one > 0:
                    result += ones[one] + " "
            elif ten == 1:
                result += "mười "
                if one == 5:
                    result += "lăm "
                elif one > 0:
                    result += ones[one] + " "
            else:
                if one > 0:
                    result += ones[one] + " "

            return result.strip()

        # Tách số thành các khối 3 chữ số
        blocks = []
        temp = int(amount)
        while temp > 0:
            blocks.append(temp % 1000)
            temp //= 1000

        # Đọc từng khối
        result = ""
        for i in range(len(blocks) - 1, -1, -1):
            if blocks[i] > 0:
                result += read_block(blocks[i]) + " " + units[i] + " "

        result = result.strip().capitalize() + " đồng"
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.picking'].browse(docids)
        if docs.pickup_status != 'back_to_supplier':
            raise UserError("Chức năng này chỉ được in phiếu trả nhà cung cấp!")
        if len(docs)>1:
            raise UserError("Chỉ được in 1 phiếu một lần!")
        dict_data = {}
        dict_data['address'] = docs.ttb_return_request_id.stock_warehouse_id.name
        dict_data['scheduled_date'] = docs.scheduled_date.strftime('%d/%m/%Y') if docs.scheduled_date else ''
        dict_data['date_now'] = fields.datetime.now().strftime('%d/%m/%Y')
        dict_data['delivery_address'] = docs.partner_id.street or ''
        dict_data['partner_id'] = docs.partner_id.name or ''
        dict_data['street'] = docs.partner_id.street or ''
        dict_data['tax'] = docs.partner_id.vat or ''
        dict_data['user_name'] = docs.user_id.name or ''
        dict_data['reason'] = docs.ttb_return_request_id.reason or ''
        dict_data['total_quantity'] = sum(docs.move_ids.mapped('quantity'))
        dict_data['sp_augges'] = docs.sp_augges
        dict_data['quantity_total'] = docs.quantity_total
        dict_data['ttb_amount_total'] = docs.ttb_amount_total
        dict_data['amount_in_words'] = self.convert_number_to_words(docs.ttb_amount_total)

        total_tax = 0.0
        processed_data = []
        for doc in docs.move_ids:
            data_row = {
                'barcode': doc.ttb_product_code or '',
                'product': doc.product_id.name or '',
                'product_uom': doc.product_uom.name or '',
                'quantity': doc.quantity or '',
                'confirm_vendor_price': doc.confirm_vendor_price or 0.0,
                'return_price_subtotal': doc.return_price_subtotal or 0.0,
                'ttb_discount': doc.ttb_discount or 0.0,
            }
            total_tax += doc.price_tax
            processed_data.append(data_row)
        dict_data['amount_total'] = docs.ttb_amount_total - total_tax


        return {
            'doc_ids': docids,
            'doc_model': 'goods.distribution.ticket',
            'dict_data': dict_data,
            'docs': processed_data,  # Trả về original Odoo records
            'company': self.env.company,
            'o': docs[0] if docs else None,
        }

