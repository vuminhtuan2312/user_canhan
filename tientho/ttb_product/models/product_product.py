from odoo import *
from odoo.tools.misc import unique


class ProductProduct(models.Model):
    _inherit = "product.product"

    top_supplier_id = fields.Many2one(string='Tên nhà cung cấp', related='product_tmpl_id.top_supplier_id', store=False)
    top_supplier_price = fields.Float(string='Giá nhập', related='product_tmpl_id.top_supplier_price', store=False)
    top_supplier_date_start = fields.Date(string='Thời gian bắt đầu', related='product_tmpl_id.top_supplier_date_start', store=False)
    top_supplier_date_end = fields.Date(string='Thời gian kết thúc', related='product_tmpl_id.top_supplier_date_end', store=False)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not name:
            return super().name_search(name, args, operator, limit)
        domain = args or []
        products = self.search_fetch(osv.expression.AND([domain, ['|', '|', '|', ('barcode', operator, name), ('barcode_vendor', operator, name), ('barcode_k', operator, name), ('default_code', operator, name)]]), ['display_name'], limit=limit)

        if not products:
            operator_barcodek = 'ilike' if operator == '=' else operator
            products = self.search_fetch(osv.expression.AND([domain, [('barcode_k', operator_barcodek, name)]]), ['display_name'], limit=limit)

        if not products:
            return super().name_search(name, args, operator, limit)
        return [(product.id, product.display_name) for product in products.sudo()]

    # đè trường của base thêm copy=False
    default_code = fields.Char(copy=False)
    # 2 trường này nên khai báo ở product.product. Nhưng đã lỡ khai báo ở product.template
    # Do đó
    # B1: khai báo related tới product.template để lấy dữ liệu giống nhau
    # B2: (sau này) khai báo lại bắt chước trường default_code
    barcode_vendor = fields.Char('Ma_Hang1 (Mã nhà cung cấp)', index=True, related='product_tmpl_id.barcode_vendor', store=True, readonly=False)
    barcode_k = fields.Char('Ma_VachK', index=True, related='product_tmpl_id.barcode_k', store=True, readonly=False)

    def onchange_level(self, level):
        categ_id = self[f'categ_id_level_{level}']
        # Gán lại cha. Chỉ cần gán lại 1 cấp sau đó sẽ có hiệu ứng dây chuyền
        if level > 1 and categ_id:
            self[f'categ_id_level_{level - 1}'] = categ_id.parent_id

        # Gán cấp con bằng False nếu không thỏa mãn quan hệ cha con.
        # Gán tất cả để tính được categ_id
        for level_up in range(level + 1, 6):
            key = f'categ_id_level_{level_up}'
            key_parent = f'categ_id_level_{level_up - 1}'

            if not self[key_parent] or (self[key] and self[key].parent_id != self[key_parent]):
                self[key] = False

        for level_categ in range(5, 0, -1):
            key = f'categ_id_level_{level_categ}'
            if self[key] or level_categ == 1:
                self.categ_id = self[key]
                break

    @api.onchange('categ_id_level_1')
    def onchange_level_1(self):
        self.onchange_level(1)

    @api.onchange('categ_id_level_2')
    def onchange_level_2(self):
        self.onchange_level(2)

    @api.onchange('categ_id_level_3')
    def onchange_level_3(self):
        self.onchange_level(3)

    @api.onchange('categ_id_level_4')
    def onchange_level_4(self):
        self.onchange_level(4)

    @api.onchange('categ_id_level_5')
    def onchange_level_5(self):
        self.onchange_level(5)

    # Ghi đè hàm base
    @api.depends('name', 'default_code', 'product_tmpl_id')
    @api.depends_context('display_default_code', 'seller_id', 'company_id', 'partner_id')
    def _compute_display_name(self):
        # Ghi đè hàm thay đổi việc lấy giá trị display từ name
        def get_display_name(name, code):
            return name
        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access("read")

        product_template_ids = self.sudo().product_tmpl_id.ids

        if partner_ids:
            # prefetch the fields used by the `display_name`
            supplier_info = self.env['product.supplierinfo'].sudo().search_fetch(
                [('product_tmpl_id', 'in', product_template_ids), ('partner_id', 'in', partner_ids)],
                ['product_tmpl_id', 'product_id', 'company_id', 'product_name', 'product_code'],
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)

        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = self.env['product.supplierinfo'].sudo().browse(self.env.context.get('seller_id')) or []
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                temp = []
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    temp.append(get_display_name(seller_variant or name, s.product_code or product.default_code))

                # => Feature drop here, one record can only have one display_name now, instead separate with `,`
                # Remove this comment
                product.display_name = ", ".join(unique(temp))
            else:
                product.display_name = get_display_name(name, product.default_code)

    def action_refresh_augges_info(self):
        return self.product_tmpl_id.action_refresh_augges_info()

    def action_create_augges(self):
        return self.product_tmpl_id.action_create_augges()

    def action_update_augges(self):
        return self.product_tmpl_id.action_update_augges()